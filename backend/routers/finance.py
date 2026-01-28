"""
Finance Router

Handles all finance-related operations including payments tracking, refund requests,
and financial reports/exports.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import io

from database import db
from config import is_pe_level, has_finance_access, can_manage_finance
from utils.auth import get_current_user
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

router = APIRouter(tags=["Finance"])


class RefundStatusUpdate(BaseModel):
    status: str  # processing, completed, failed
    notes: Optional[str] = None
    reference_number: Optional[str] = None


@router.get("/finance/payments")
async def get_all_payments(
    payment_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all payments (client and vendor) for finance dashboard."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access finance data")
    
    all_payments = []
    
    # Get client payments from bookings
    if payment_type in [None, "client"]:
        bookings = await db.bookings.find(
            {"payments": {"$exists": True, "$ne": []}},
            {"_id": 0}
        ).to_list(10000)
        
        for booking in bookings:
            client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0, "name": 1})
            stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0, "symbol": 1})
            
            for payment in booking.get("payments", []):
                payment_date = payment.get("payment_date", "")
                
                # Date filter
                if start_date and payment_date < start_date:
                    continue
                if end_date and payment_date > end_date:
                    continue
                
                all_payments.append({
                    "id": payment.get("id", str(uuid.uuid4())),
                    "type": "client",
                    "direction": "received",
                    "entity_id": booking["client_id"],
                    "entity_name": client["name"] if client else "Unknown",
                    "reference_id": booking["id"],
                    "reference_number": booking.get("booking_number", ""),
                    "stock_symbol": stock["symbol"] if stock else "Unknown",
                    "amount": payment.get("amount", 0),
                    "payment_date": payment_date,
                    "notes": payment.get("notes", ""),
                    "proof_url": payment.get("proof_url"),
                    "recorded_by": payment.get("recorded_by_name", "")
                })
    
    # Get vendor payments from purchases
    if payment_type in [None, "vendor"]:
        purchases = await db.purchases.find(
            {"payments": {"$exists": True, "$ne": []}},
            {"_id": 0}
        ).to_list(10000)
        
        for purchase in purchases:
            vendor = await db.clients.find_one({"id": purchase["vendor_id"]}, {"_id": 0, "name": 1})
            stock = await db.stocks.find_one({"id": purchase["stock_id"]}, {"_id": 0, "symbol": 1})
            
            for payment in purchase.get("payments", []):
                payment_date = payment.get("payment_date", "")
                
                # Date filter
                if start_date and payment_date < start_date:
                    continue
                if end_date and payment_date > end_date:
                    continue
                
                all_payments.append({
                    "id": payment.get("id", str(uuid.uuid4())),
                    "type": "vendor",
                    "direction": "sent",
                    "entity_id": purchase["vendor_id"],
                    "entity_name": vendor["name"] if vendor else "Unknown",
                    "reference_id": purchase["id"],
                    "reference_number": purchase.get("purchase_number", purchase["id"][:8].upper()),
                    "stock_symbol": stock["symbol"] if stock else "Unknown",
                    "amount": payment.get("amount", 0),
                    "payment_date": payment_date,
                    "notes": payment.get("notes", ""),
                    "proof_url": payment.get("proof_url"),
                    "recorded_by": payment.get("recorded_by_name", "")
                })
    
    # Sort by date descending
    all_payments.sort(key=lambda x: x.get("payment_date", ""), reverse=True)
    
    return all_payments


@router.get("/finance/summary")
async def get_finance_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get finance summary statistics."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access finance data")
    
    # Get all payments
    payments = await get_all_payments(None, start_date, end_date, current_user)
    
    # Calculate summaries
    total_received = sum(p["amount"] for p in payments if p["direction"] == "received")
    total_sent = sum(p["amount"] for p in payments if p["direction"] == "sent")
    
    client_payments_count = len([p for p in payments if p["type"] == "client"])
    vendor_payments_count = len([p for p in payments if p["type"] == "vendor"])
    
    # Get refund request stats
    pending_refunds = await db.refund_requests.find(
        {"status": {"$in": ["pending", "processing"]}},
        {"_id": 0}
    ).to_list(1000)
    
    completed_refunds = await db.refund_requests.find(
        {"status": "completed"},
        {"_id": 0}
    ).to_list(1000)
    
    # Get RP payment stats
    pending_rp_payments = await db.rp_payments.find(
        {"status": {"$in": ["pending", "processing"]}},
        {"_id": 0}
    ).to_list(1000)
    
    paid_rp_payments = await db.rp_payments.find(
        {"status": "paid"},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "total_received": total_received,
        "total_sent": total_sent,
        "net_flow": total_received - total_sent,
        "client_payments_count": client_payments_count,
        "vendor_payments_count": vendor_payments_count,
        "pending_refunds_count": len(pending_refunds),
        "pending_refunds_amount": sum(r.get("refund_amount", 0) for r in pending_refunds),
        "completed_refunds_count": len(completed_refunds),
        "completed_refunds_amount": sum(r.get("refund_amount", 0) for r in completed_refunds),
        "pending_rp_payments_count": len(pending_rp_payments),
        "pending_rp_payments_amount": sum(p.get("payment_amount", 0) for p in pending_rp_payments),
        "paid_rp_payments_count": len(paid_rp_payments),
        "paid_rp_payments_amount": sum(p.get("payment_amount", 0) for p in paid_rp_payments)
    }


@router.get("/finance/refund-requests")
async def get_refund_requests(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all refund requests."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access refund requests")
    
    query = {}
    if status:
        query["status"] = status
    
    refunds = await db.refund_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return refunds


@router.get("/finance/refund-requests/{request_id}")
async def get_refund_request(request_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific refund request."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access refund requests")
    
    refund = await db.refund_requests.find_one({"id": request_id}, {"_id": 0})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    
    return refund


@router.put("/finance/refund-requests/{request_id}")
async def update_refund_request(
    request_id: str,
    update_data: RefundStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update refund request status."""
    if not can_manage_finance(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can update refund requests")
    
    refund = await db.refund_requests.find_one({"id": request_id}, {"_id": 0})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    
    update_fields = {
        "status": update_data.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if update_data.notes:
        update_fields["notes"] = update_data.notes
    if update_data.reference_number:
        update_fields["reference_number"] = update_data.reference_number
    
    await db.refund_requests.update_one({"id": request_id}, {"$set": update_fields})
    
    return {"message": f"Refund request updated to {update_data.status}"}


@router.put("/finance/refund-requests/{request_id}/bank-details")
async def update_refund_bank_details(
    request_id: str,
    bank_name: str,
    account_number: str,
    ifsc_code: str,
    account_holder_name: str,
    branch: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update bank details for a refund request."""
    if not can_manage_finance(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can update refund requests")
    
    refund = await db.refund_requests.find_one({"id": request_id}, {"_id": 0})
    if not refund:
        raise HTTPException(status_code=404, detail="Refund request not found")
    
    bank_details = {
        "bank_name": bank_name,
        "account_number": account_number,
        "ifsc_code": ifsc_code,
        "account_holder_name": account_holder_name,
        "branch": branch
    }
    
    await db.refund_requests.update_one({"id": request_id}, {"$set": {"bank_details": bank_details}})
    
    return {"message": "Bank details updated successfully"}


# ============== RP Payments Endpoints ==============
class RPPaymentUpdate(BaseModel):
    status: str  # processing, paid
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[str] = None


@router.get("/finance/rp-payments")
async def get_rp_payments(
    status: Optional[str] = None,
    rp_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all RP payments for finance dashboard."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access RP payments")
    
    query = {}
    if status:
        query["status"] = status
    if rp_id:
        query["referral_partner_id"] = rp_id
    
    payments = await db.rp_payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return payments


@router.get("/finance/rp-payments/summary")
async def get_rp_payments_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get RP payments summary statistics."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access RP payments")
    
    all_payments = await db.rp_payments.find({}, {"_id": 0}).to_list(10000)
    
    pending = [p for p in all_payments if p.get("status") == "pending"]
    processing = [p for p in all_payments if p.get("status") == "processing"]
    paid = [p for p in all_payments if p.get("status") == "paid"]
    
    return {
        "pending_count": len(pending),
        "pending_amount": sum(p.get("payment_amount", 0) for p in pending),
        "processing_count": len(processing),
        "processing_amount": sum(p.get("payment_amount", 0) for p in processing),
        "paid_count": len(paid),
        "paid_amount": sum(p.get("payment_amount", 0) for p in paid),
        "total_count": len(all_payments),
        "total_amount": sum(p.get("payment_amount", 0) for p in all_payments)
    }


@router.put("/finance/rp-payments/{payment_id}")
async def update_rp_payment(
    payment_id: str,
    update_data: RPPaymentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update RP payment status (mark as paid)."""
    if not can_manage_finance(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can update RP payments")
    
    payment = await db.rp_payments.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="RP payment not found")
    
    update_fields = {
        "status": update_data.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if update_data.payment_reference:
        update_fields["payment_reference"] = update_data.payment_reference
    if update_data.notes:
        update_fields["notes"] = update_data.notes
    if update_data.payment_date:
        update_fields["payment_date"] = update_data.payment_date
    elif update_data.status == "paid":
        update_fields["payment_date"] = datetime.now(timezone.utc).isoformat()
    
    await db.rp_payments.update_one({"id": payment_id}, {"$set": update_fields})
    
    # Also update the booking's RP payment status
    if payment.get("booking_id"):
        await db.bookings.update_one(
            {"id": payment["booking_id"]},
            {"$set": {"rp_payment_status": update_data.status}}
        )
    
    return {"message": f"RP payment updated to {update_data.status}"}


@router.get("/finance/employee-commissions")
async def get_employee_commissions(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,  # pending, calculated, paid
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get employee commissions from confirmed bookings"""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access commission data")
    
    query = {
        "stock_transferred": True,
        "employee_commission_amount": {"$exists": True, "$gt": 0}
    }
    
    if employee_id:
        query["created_by"] = employee_id
    
    if status:
        query["employee_commission_status"] = status
    
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(5000)
    
    # Get employee and stock details
    employee_ids = list(set(b.get("created_by") for b in bookings if b.get("created_by")))
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    client_ids = list(set(b.get("client_id") for b in bookings if b.get("client_id")))
    
    employees = await db.users.find({"id": {"$in": employee_ids}}, {"_id": 0, "hashed_password": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    
    emp_map = {e["id"]: e for e in employees}
    stock_map = {s["id"]: s for s in stocks}
    client_map = {c["id"]: c for c in clients}
    
    result = []
    for booking in bookings:
        emp = emp_map.get(booking.get("created_by"), {})
        stock = stock_map.get(booking.get("stock_id"), {})
        client = client_map.get(booking.get("client_id"), {})
        
        result.append({
            "booking_id": booking.get("id"),
            "booking_number": booking.get("booking_number"),
            "employee_id": booking.get("created_by"),
            "employee_name": emp.get("name", "Unknown"),
            "client_name": client.get("name", "Unknown"),
            "stock_symbol": stock.get("symbol", "Unknown"),
            "quantity": booking.get("quantity", 0),
            "profit": round((booking.get("selling_price", 0) - booking.get("buying_price", 0)) * booking.get("quantity", 0), 2),
            "rp_share_percent": booking.get("rp_revenue_share_percent", 0) or 0,
            "employee_share_percent": booking.get("employee_revenue_share_percent", 100),
            "employee_commission_amount": booking.get("employee_commission_amount", 0),
            "rp_payment_amount": booking.get("rp_payment_amount", 0) or 0,
            "status": booking.get("employee_commission_status", "pending"),
            "transfer_date": booking.get("stock_transferred_at"),
            "created_at": booking.get("created_at")
        })
    
    return result


@router.get("/finance/employee-commissions/summary")
async def get_employee_commissions_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get summary of employee commissions by employee"""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can access commission data")
    
    bookings = await db.bookings.find(
        {
            "stock_transferred": True,
            "employee_commission_amount": {"$exists": True, "$gt": 0}
        },
        {"_id": 0}
    ).to_list(10000)
    
    # Aggregate by employee
    emp_stats = {}
    for booking in bookings:
        emp_id = booking.get("created_by")
        if not emp_id:
            continue
        
        if emp_id not in emp_stats:
            emp_stats[emp_id] = {
                "total_bookings": 0,
                "total_profit": 0,
                "total_commission": 0,
                "total_rp_share": 0,
                "pending_commission": 0,
                "calculated_commission": 0,
                "paid_commission": 0
            }
        
        profit = (booking.get("selling_price", 0) - booking.get("buying_price", 0)) * booking.get("quantity", 0)
        commission = booking.get("employee_commission_amount", 0)
        rp_amount = booking.get("rp_payment_amount", 0) or 0
        status = booking.get("employee_commission_status", "pending")
        
        emp_stats[emp_id]["total_bookings"] += 1
        emp_stats[emp_id]["total_profit"] += profit
        emp_stats[emp_id]["total_commission"] += commission
        emp_stats[emp_id]["total_rp_share"] += rp_amount
        
        if status == "pending":
            emp_stats[emp_id]["pending_commission"] += commission
        elif status == "calculated":
            emp_stats[emp_id]["calculated_commission"] += commission
        elif status == "paid":
            emp_stats[emp_id]["paid_commission"] += commission
    
    # Get employee names
    emp_ids = list(emp_stats.keys())
    employees = await db.users.find({"id": {"$in": emp_ids}}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(1000)
    emp_map = {e["id"]: e for e in employees}
    
    result = []
    for emp_id, stats in emp_stats.items():
        emp = emp_map.get(emp_id, {})
        result.append({
            "employee_id": emp_id,
            "employee_name": emp.get("name", "Unknown"),
            "role": emp.get("role", 5),
            **{k: round(v, 2) if isinstance(v, float) else v for k, v in stats.items()}
        })
    
    result.sort(key=lambda x: x["total_commission"], reverse=True)
    return result


@router.put("/finance/employee-commissions/{booking_id}/mark-paid")
async def mark_commission_paid(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark an employee commission as paid"""
    if not can_manage_finance(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can mark commissions as paid")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if not booking.get("employee_commission_amount"):
        raise HTTPException(status_code=400, detail="No commission calculated for this booking")
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": {
            "employee_commission_status": "paid",
            "employee_commission_paid_at": datetime.now(timezone.utc).isoformat(),
            "employee_commission_paid_by": current_user["id"]
        }}
    )
    
    return {"message": "Commission marked as paid"}


@router.get("/finance/export/excel")
async def export_finance_excel(
    payment_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export finance data to Excel."""
    if not has_finance_access(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk, PE Manager, or Finance can export finance data")
    
    payments = await get_all_payments(payment_type, start_date, end_date, current_user)
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Payments Report"
    
    # Headers
    headers = ["Date", "Type", "Direction", "Entity", "Reference", "Stock", "Amount", "Notes", "Recorded By"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Data rows
    for row, payment in enumerate(payments, 2):
        ws.cell(row=row, column=1, value=payment.get("payment_date", ""))
        ws.cell(row=row, column=2, value=payment.get("type", "").title())
        ws.cell(row=row, column=3, value=payment.get("direction", "").title())
        ws.cell(row=row, column=4, value=payment.get("entity_name", ""))
        ws.cell(row=row, column=5, value=payment.get("reference_number", ""))
        ws.cell(row=row, column=6, value=payment.get("stock_symbol", ""))
        ws.cell(row=row, column=7, value=payment.get("amount", 0))
        ws.cell(row=row, column=8, value=payment.get("notes", ""))
        ws.cell(row=row, column=9, value=payment.get("recorded_by", ""))
    
    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = min(max_length + 2, 50)
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"finance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
