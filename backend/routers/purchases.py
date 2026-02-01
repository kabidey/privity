"""
Purchases Router
Handles purchase orders and vendor payments
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
import os
import io

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from database import db
from config import is_pe_level, UPLOAD_DIR
from models import Purchase, PurchaseCreate
from utils.auth import get_current_user
from services.audit_service import create_audit_log
from services.email_service import send_stock_transfer_request_email, send_email, get_email_template

router = APIRouter(prefix="/purchases", tags=["Purchases"])

# TCS Constants
TCS_RATE = 0.001  # 0.1%
TCS_THRESHOLD = 5000000  # 50 lakhs


def get_indian_financial_year(date_str: str = None) -> tuple:
    """Get Indian Financial Year (April to March) start and end dates"""
    from datetime import datetime
    
    if date_str:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if 'T' in date_str else datetime.strptime(date_str, '%Y-%m-%d')
    else:
        date = datetime.now()
    
    year = date.year
    month = date.month
    
    # Indian FY starts in April
    if month >= 4:  # April to December - FY is current year to next year
        fy_start = f"{year}-04-01"
        fy_end = f"{year + 1}-03-31"
    else:  # January to March - FY is previous year to current year
        fy_start = f"{year - 1}-04-01"
        fy_end = f"{year}-03-31"
    
    return fy_start, fy_end


async def get_vendor_fy_payments(vendor_id: str, payment_date: str = None) -> float:
    """Get total payments made to a vendor in the current Indian Financial Year"""
    fy_start, fy_end = get_indian_financial_year(payment_date)
    
    # Get all purchases for this vendor
    purchases = await db.purchases.find(
        {"vendor_id": vendor_id},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    
    purchase_ids = [p["id"] for p in purchases]
    
    if not purchase_ids:
        return 0.0
    
    # Get all payments for these purchases within the financial year
    pipeline = [
        {
            "$match": {
                "purchase_id": {"$in": purchase_ids},
                "payment_date": {"$gte": fy_start, "$lte": fy_end}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"}
            }
        }
    ]
    
    result = await db.purchase_payments.aggregate(pipeline).to_list(1)
    
    return result[0]["total"] if result else 0.0


def calculate_tcs(payment_amount: float, cumulative_payments: float) -> dict:
    """Calculate TCS based on payment amount and cumulative payments"""
    # TCS applies only if cumulative payments exceed threshold
    amount_above_threshold = (cumulative_payments + payment_amount) - TCS_THRESHOLD
    
    if amount_above_threshold <= 0:
        # Total payments still under threshold
        return {
            "tcs_applicable": False,
            "tcs_amount": 0.0,
            "tcs_rate": TCS_RATE,
            "threshold": TCS_THRESHOLD,
            "cumulative_before": cumulative_payments,
            "cumulative_after": cumulative_payments + payment_amount,
            "amount_above_threshold": 0.0
        }
    
    # Calculate how much of this payment is above threshold
    if cumulative_payments >= TCS_THRESHOLD:
        # Already above threshold, TCS on entire payment
        tcs_applicable_amount = payment_amount
    else:
        # Partially above threshold
        tcs_applicable_amount = amount_above_threshold
    
    tcs_amount = round(tcs_applicable_amount * TCS_RATE, 2)
    
    return {
        "tcs_applicable": True,
        "tcs_amount": tcs_amount,
        "tcs_rate": TCS_RATE,
        "threshold": TCS_THRESHOLD,
        "cumulative_before": cumulative_payments,
        "cumulative_after": cumulative_payments + payment_amount,
        "amount_above_threshold": amount_above_threshold,
        "tcs_applicable_amount": tcs_applicable_amount
    }


# Pydantic model for payment request
class PaymentRequest(BaseModel):
    amount: float
    payment_date: str
    payment_mode: Optional[str] = "bank_transfer"
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    proof_url: Optional[str] = None
    tcs_amount: Optional[float] = None  # Manual TCS override
    tcs_applicable: Optional[bool] = None  # Manual TCS flag


@router.post("", response_model=Purchase)
async def create_purchase(
    purchase_data: PurchaseCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new purchase order"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can create purchases")
    
    # Validate vendor
    vendor = await db.clients.find_one(
        {"id": purchase_data.vendor_id, "is_vendor": True},
        {"_id": 0}
    )
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Validate stock
    stock = await db.stocks.find_one({"id": purchase_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    purchase_id = str(uuid.uuid4())
    purchase_number = f"PO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{purchase_id[:8].upper()}"
    
    purchase_doc = {
        "id": purchase_id,
        "purchase_number": purchase_number,
        "vendor_id": purchase_data.vendor_id,
        "vendor_name": vendor.get("name"),
        "stock_id": purchase_data.stock_id,
        "stock_symbol": stock.get("symbol"),
        "quantity": purchase_data.quantity,
        "price_per_share": purchase_data.price_per_unit,
        "total_amount": purchase_data.quantity * purchase_data.price_per_unit,
        "status": "pending",
        "payment_status": "pending",
        "notes": purchase_data.notes,
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.purchases.insert_one(purchase_doc)
    
    await create_audit_log(
        action="PURCHASE_CREATE",
        entity_type="purchase",
        entity_id=purchase_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=purchase_number
    )
    
    # Send email notification to vendor
    vendor_email = vendor.get("email")
    if vendor_email:
        template = await get_email_template("purchase_order_created")
        
        if template:
            # Format amounts with Indian locale
            formatted_price = f"₹{purchase_data.price_per_unit:,.2f}"
            formatted_total = f"₹{purchase_doc['total_amount']:,.2f}"
            formatted_quantity = f"{purchase_data.quantity:,}"
            
            subject = template["subject"]
            subject = subject.replace("{{stock_symbol}}", stock.get("symbol", ""))
            
            body = template["body"]
            body = body.replace("{{vendor_name}}", vendor.get("name", ""))
            body = body.replace("{{stock_symbol}}", stock.get("symbol", ""))
            body = body.replace("{{quantity}}", formatted_quantity)
            body = body.replace("{{price_per_unit}}", formatted_price)
            body = body.replace("{{total_amount}}", formatted_total)
            
            await send_email(
                to_email=vendor_email,
                subject=subject,
                body=body,
                template_key="purchase_order_created",
                variables={
                    "vendor_name": vendor.get("name"),
                    "stock_symbol": stock.get("symbol"),
                    "quantity": formatted_quantity,
                    "price_per_unit": formatted_price,
                    "total_amount": formatted_total
                },
                related_entity_type="purchase",
                related_entity_id=purchase_id
            )
    
    return purchase_doc


@router.get("", response_model=List[Purchase])
async def get_purchases(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all purchases with vendor and stock details"""
    query = {}
    if status:
        query["status"] = status
    if vendor_id:
        query["vendor_id"] = vendor_id
    if stock_id:
        query["stock_id"] = stock_id
    
    purchases = await db.purchases.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    if not purchases:
        return []
    
    # Enrich with vendor and stock details
    vendor_ids = list(set(p["vendor_id"] for p in purchases))
    stock_ids = list(set(p["stock_id"] for p in purchases))
    
    vendors = await db.clients.find({"id": {"$in": vendor_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    vendor_map = {v["id"]: v for v in vendors}
    stock_map = {s["id"]: s for s in stocks}
    
    enriched_purchases = []
    for p in purchases:
        vendor = vendor_map.get(p["vendor_id"])
        stock = stock_map.get(p["stock_id"])
        
        # Add vendor_name and stock_symbol if not present
        p["vendor_name"] = p.get("vendor_name") or (vendor["name"] if vendor else "Unknown")
        p["stock_symbol"] = p.get("stock_symbol") or (stock["symbol"] if stock else "Unknown")
        
        enriched_purchases.append(Purchase(**p))
    
    return enriched_purchases


@router.get("/{purchase_id}/payments")
async def get_purchase_payments(
    purchase_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get payment tranches for a purchase"""
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    payments = await db.purchase_payments.find(
        {"purchase_id": purchase_id},
        {"_id": 0}
    ).sort("tranche_number", 1).to_list(100)
    
    return payments


@router.post("/{purchase_id}/payments")
async def add_purchase_payment(
    purchase_id: str,
    payment_data: PaymentRequest,
    current_user: dict = Depends(get_current_user)
):
    """Add a payment tranche to a purchase with TCS calculation"""
    user_role = current_user.get("role", 6)
    
    # Extract payment data from Pydantic model
    amount = payment_data.amount
    payment_date = payment_data.payment_date
    payment_mode = payment_data.payment_mode or "bank_transfer"
    reference_number = payment_data.reference_number
    notes = payment_data.notes
    proof_url = payment_data.proof_url
    manual_tcs_amount = payment_data.tcs_amount
    manual_tcs_applicable = payment_data.tcs_applicable
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can add payments")
    
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    vendor_id = purchase.get("vendor_id")
    
    # Get existing payments for this purchase
    existing_payments = await db.purchase_payments.find(
        {"purchase_id": purchase_id},
        {"_id": 0}
    ).to_list(100)
    
    total_paid = sum(p.get("amount", 0) for p in existing_payments)
    remaining = purchase.get("total_amount", 0) - total_paid
    
    if amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount ({amount}) exceeds remaining balance ({remaining})"
        )
    
    # Calculate TCS
    cumulative_vendor_payments = await get_vendor_fy_payments(vendor_id, payment_date)
    tcs_info = calculate_tcs(amount, cumulative_vendor_payments)
    
    # Use manual TCS if provided, otherwise use calculated
    if manual_tcs_applicable is not None:
        tcs_applicable = manual_tcs_applicable
        tcs_amount = manual_tcs_amount if manual_tcs_amount is not None else tcs_info["tcs_amount"]
    else:
        tcs_applicable = tcs_info["tcs_applicable"]
        tcs_amount = tcs_info["tcs_amount"]
    
    tranche_number = len(existing_payments) + 1
    payment_id = str(uuid.uuid4())
    
    # Get Indian FY info
    fy_start, fy_end = get_indian_financial_year(payment_date)
    
    payment_doc = {
        "id": payment_id,
        "purchase_id": purchase_id,
        "vendor_id": vendor_id,
        "tranche_number": tranche_number,
        "amount": amount,
        "payment_date": payment_date,
        "payment_mode": payment_mode,
        "reference_number": reference_number,
        "notes": notes,
        "proof_url": proof_url,
        # TCS fields
        "tcs_applicable": tcs_applicable,
        "tcs_amount": tcs_amount if tcs_applicable else 0.0,
        "tcs_rate": TCS_RATE,
        "tcs_threshold": TCS_THRESHOLD,
        "vendor_fy_cumulative_before": cumulative_vendor_payments,
        "vendor_fy_cumulative_after": cumulative_vendor_payments + amount,
        "financial_year": f"{fy_start[:4]}-{fy_end[:4]}",
        # Net payment (amount - TCS)
        "net_payment": round(amount - (tcs_amount if tcs_applicable else 0), 2),
        "status": "completed",
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.purchase_payments.insert_one(payment_doc)
    
    # Remove MongoDB _id from response
    payment_doc.pop("_id", None)
    
    # Update purchase payment status
    new_total_paid = total_paid + amount
    if new_total_paid >= purchase.get("total_amount", 0):
        await db.purchases.update_one(
            {"id": purchase_id},
            {"$set": {
                "payment_status": "completed",
                "dp_status": "receivable",
                "dp_receivable_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Payment completed - send stock transfer request email to vendor
        vendor = await db.clients.find_one(
            {"id": purchase.get("vendor_id"), "is_vendor": True},
            {"_id": 0}
        )
        stock = await db.stocks.find_one({"id": purchase.get("stock_id")}, {"_id": 0})
        company_master = await db.company_master.find_one({"_id": "company_settings"}, {"_id": 0})
        
        if vendor and company_master:
            await send_stock_transfer_request_email(
                purchase_id=purchase_id,
                vendor=vendor,
                purchase=purchase,
                stock=stock,
                total_paid=new_total_paid,
                payment_date=payment_doc["created_at"],
                company_master=company_master,
                cc_email=current_user.get("email")
            )
    else:
        await db.purchases.update_one(
            {"id": purchase_id},
            {"$set": {"payment_status": "partial"}}
        )
    
    return payment_doc


@router.delete("/{purchase_id}")
async def delete_purchase(
    purchase_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a purchase order (PE Desk only)"""
    user_role = current_user.get("role", 6)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete purchases")
    
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    # Check if payments exist
    payments_count = await db.purchase_payments.count_documents({"purchase_id": purchase_id})
    if payments_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete purchase with existing payments. Delete payments first."
        )
    
    await db.purchases.delete_one({"id": purchase_id})
    
    await create_audit_log(
        action="PURCHASE_DELETE",
        entity_type="purchase",
        entity_id=purchase_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=purchase.get("purchase_number", purchase_id)
    )
    
    return {"message": "Purchase deleted successfully"}


# ============== DP Receivable Endpoints ==============

@router.get("/dp-receivables")
async def get_dp_receivables(current_user: dict = Depends(get_current_user)):
    """Get all purchases with DP receivable status (PE Level only)"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can view DP receivables")
    
    # Get purchases with dp_status = "receivable"
    purchases = await db.purchases.find(
        {"dp_status": "receivable"},
        {"_id": 0}
    ).sort("dp_receivable_at", -1).to_list(1000)
    
    # Enrich with vendor and stock details
    for purchase in purchases:
        vendor = await db.clients.find_one(
            {"id": purchase.get("vendor_id")},
            {"_id": 0, "name": 1, "email": 1}
        )
        if vendor:
            purchase["vendor_name"] = vendor.get("name")
            purchase["vendor_email"] = vendor.get("email")
        
        stock = await db.stocks.find_one(
            {"id": purchase.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1}
        )
        if stock:
            purchase["stock_name"] = stock.get("name")
            purchase["stock_symbol"] = stock.get("symbol")
    
    return purchases


@router.get("/dp-received")
async def get_dp_received(current_user: dict = Depends(get_current_user)):
    """Get all purchases with DP received status (PE Level only)"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can view DP received records")
    
    # Get purchases with dp_status = "received"
    purchases = await db.purchases.find(
        {"dp_status": "received"},
        {"_id": 0}
    ).sort("dp_received_at", -1).to_list(1000)
    
    # Enrich with vendor and stock details
    for purchase in purchases:
        vendor = await db.clients.find_one(
            {"id": purchase.get("vendor_id")},
            {"_id": 0, "name": 1, "email": 1}
        )
        if vendor:
            purchase["vendor_name"] = vendor.get("name")
            purchase["vendor_email"] = vendor.get("email")
        
        stock = await db.stocks.find_one(
            {"id": purchase.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1}
        )
        if stock:
            purchase["stock_name"] = stock.get("name")
            purchase["stock_symbol"] = stock.get("symbol")
    
    return purchases


@router.put("/{purchase_id}/mark-dp-received")
async def mark_dp_received(
    purchase_id: str,
    dp_type: str,  # "NSDL" or "CDSL"
    current_user: dict = Depends(get_current_user)
):
    """Mark a purchase as DP received (PE Level only)
    
    Args:
        purchase_id: Purchase ID
        dp_type: Either "NSDL" or "CDSL"
    """
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can mark DP as received")
    
    if dp_type not in ["NSDL", "CDSL"]:
        raise HTTPException(status_code=400, detail="dp_type must be 'NSDL' or 'CDSL'")
    
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    if purchase.get("dp_status") != "receivable":
        raise HTTPException(status_code=400, detail="Purchase is not in receivable status")
    
    # Update purchase with received status
    await db.purchases.update_one(
        {"id": purchase_id},
        {"$set": {
            "dp_status": "received",
            "dp_type": dp_type,
            "dp_received_at": datetime.now(timezone.utc).isoformat(),
            "dp_received_by": current_user["id"],
            "dp_received_by_name": current_user["name"]
        }}
    )
    
    # Update inventory - add received quantity to available stock
    stock = await db.stocks.find_one({"id": purchase.get("stock_id")}, {"_id": 0})
    if stock:
        # Update inventory with received quantity
        inventory = await db.inventory.find_one({"stock_id": purchase.get("stock_id")}, {"_id": 0})
        if inventory:
            await db.inventory.update_one(
                {"stock_id": purchase.get("stock_id")},
                {"$inc": {"available_quantity": purchase.get("quantity", 0)}}
            )
        else:
            # Create new inventory record
            await db.inventory.insert_one({
                "id": str(uuid.uuid4()),
                "stock_id": purchase.get("stock_id"),
                "available_quantity": purchase.get("quantity", 0),
                "blocked_quantity": 0,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    await create_audit_log(
        action="DP_RECEIVED",
        entity_type="purchase",
        entity_id=purchase_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        details={
            "dp_type": dp_type,
            "quantity": purchase.get("quantity"),
            "stock_id": purchase.get("stock_id")
        },
        entity_name=purchase.get("purchase_number", purchase_id)
    )
    
    return {
        "message": f"Stock received via {dp_type} and inventory updated",
        "dp_type": dp_type,
        "quantity": purchase.get("quantity"),
        "received_at": datetime.now(timezone.utc).isoformat()
    }



@router.get("/dp-receivables/export")
async def export_dp_receivables_excel(
    status: str = "all",  # "receivable", "received", or "all"
    current_user: dict = Depends(get_current_user)
):
    """Export DP receivables data to Excel"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can export DP data")
    
    # Build query based on status
    query = {}
    if status == "receivable":
        query["dp_status"] = "receivable"
    elif status == "received":
        query["dp_status"] = "received"
    else:
        query["dp_status"] = {"$in": ["receivable", "received"]}
    
    # Get purchases
    purchases = await db.purchases.find(query, {"_id": 0}).to_list(10000)
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "DP Receivables"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = [
        "Purchase #", "Vendor Name", "Vendor DP ID", "Vendor PAN",
        "Stock Symbol", "Stock Name", "ISIN", "Quantity",
        "Total Amount", "Status", "DP Type", "Received Date"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Data rows
    row = 2
    for purchase in purchases:
        # Get vendor details
        vendor = await db.clients.find_one(
            {"id": purchase.get("vendor_id")},
            {"_id": 0, "name": 1, "dp_id": 1, "pan": 1}
        )
        
        # Get stock details
        stock = await db.stocks.find_one(
            {"id": purchase.get("stock_id")},
            {"_id": 0, "name": 1, "symbol": 1, "isin": 1}
        )
        
        data = [
            purchase.get("purchase_number", ""),
            vendor.get("name", "") if vendor else "",
            vendor.get("dp_id", "") if vendor else "",
            vendor.get("pan", "") if vendor else "",
            stock.get("symbol", "") if stock else "",
            stock.get("name", "") if stock else "",
            stock.get("isin", "") if stock else "",
            purchase.get("quantity", 0),
            purchase.get("total_amount", 0),
            purchase.get("dp_status", "").upper(),
            purchase.get("dp_type", ""),
            purchase.get("dp_received_at", "")[:10] if purchase.get("dp_received_at") else ""
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
            if col in [8, 9]:  # Quantity and Amount columns
                cell.alignment = Alignment(horizontal="right")
        
        row += 1
    
    # Adjust column widths
    column_widths = [15, 25, 20, 15, 15, 30, 20, 12, 15, 12, 10, 15]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width
    
    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"dp_receivables_{status}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

