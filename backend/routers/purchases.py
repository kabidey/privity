"""
Purchases Router
Handles purchase orders and vendor payments
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import uuid
import os

from database import db
from config import is_pe_level, UPLOAD_DIR
from models import Purchase, PurchaseCreate
from utils.auth import get_current_user
from services.audit_service import create_audit_log
from services.email_service import send_stock_transfer_request_email

router = APIRouter(prefix="/purchases", tags=["Purchases"])


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
        "price_per_share": purchase_data.price_per_share,
        "total_amount": purchase_data.quantity * purchase_data.price_per_share,
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
    amount: float,
    payment_date: str,
    payment_mode: str = "bank_transfer",
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Add a payment tranche to a purchase"""
    user_role = current_user.get("role", 6)
    
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE level can add payments")
    
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    
    # Get existing payments
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
    
    tranche_number = len(existing_payments) + 1
    payment_id = str(uuid.uuid4())
    
    payment_doc = {
        "id": payment_id,
        "purchase_id": purchase_id,
        "tranche_number": tranche_number,
        "amount": amount,
        "payment_date": payment_date,
        "payment_mode": payment_mode,
        "reference_number": reference_number,
        "notes": notes,
        "status": "completed",
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.purchase_payments.insert_one(payment_doc)
    
    # Update purchase payment status
    new_total_paid = total_paid + amount
    if new_total_paid >= purchase.get("total_amount", 0):
        await db.purchases.update_one(
            {"id": purchase_id},
            {"$set": {"payment_status": "completed"}}
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
