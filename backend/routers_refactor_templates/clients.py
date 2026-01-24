"""
Client and Vendor management routes
"""
import uuid
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
import aiofiles
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Query

from database import db
from config import UPLOAD_DIR, ROLES
from models import (
    ClientCreate, Client, BankAccount, User
)
from utils.auth import get_current_user, check_permission
from services.email_service import send_email
from services.notification_service import create_notification, notify_roles
from services.audit_service import create_audit_log
from services.ocr_service import process_document_ocr

router = APIRouter(prefix="/clients", tags=["Clients"])


def generate_otc_ucc(client_id: str) -> str:
    """Generate unique OTC UCC code"""
    return f"OTC{datetime.now().strftime('%Y%m%d')}{client_id[:8].upper()}"


@router.post("", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    """Create a new client or vendor"""
    user_role = current_user.get("role", 5)
    
    # Employees can only create clients (not vendors)
    if user_role == 4 and client_data.is_vendor:
        raise HTTPException(status_code=403, detail="Employees cannot create vendors")
    
    # Validate trading_ucc is required when dp_type is "smifs"
    if client_data.dp_type == "smifs" and not client_data.trading_ucc:
        raise HTTPException(status_code=400, detail="Trading UCC is required when DP is with SMIFS")
    
    # Check permission based on whether it's a client or vendor
    if client_data.is_vendor:
        check_permission(current_user, "manage_vendors")
    else:
        if user_role == 4:
            check_permission(current_user, "create_clients")
        else:
            check_permission(current_user, "manage_clients")
    
    client_id = str(uuid.uuid4())
    otc_ucc = generate_otc_ucc(client_id)
    
    # Determine approval status - employees need approval
    is_active = True
    approval_status = "approved"
    if user_role == 4 and not client_data.is_vendor:
        is_active = False
        approval_status = "pending"
    
    client_doc = {
        "id": client_id,
        "otc_ucc": otc_ucc,
        **client_data.model_dump(),
        "bank_accounts": [acc.model_dump() if hasattr(acc, 'model_dump') else acc for acc in client_data.bank_accounts] if client_data.bank_accounts else [],
        "is_active": is_active,
        "approval_status": approval_status,
        "documents": [],
        "mapped_employee_id": current_user["id"] if user_role == 4 else None,
        "mapped_employee_name": current_user["name"] if user_role == 4 else None,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(client_doc)
    
    # Send email notification
    if client_data.email and is_active:
        await send_email(
            client_data.email,
            "Welcome to Private Equity System",
            f"<p>Dear {client_data.name},</p><p>Your account has been created successfully.</p>"
        )
    
    # Real-time notification for pending approval
    if approval_status == "pending":
        await notify_roles(
            [1, 2, 3],
            "client_pending",
            "New Client Pending Approval",
            f"Client '{client_data.name}' created by {current_user['name']} is pending approval",
            {"client_id": client_id, "client_name": client_data.name}
        )
    
    return Client(**{k: v for k, v in client_doc.items() if k != "user_id"})


@router.get("", response_model=List[Client])
async def get_clients(
    search: Optional[str] = None,
    is_vendor: Optional[bool] = None,
    pending_approval: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get list of clients/vendors with optional filters"""
    query = {}
    user_role = current_user.get("role", 5)
    user_id = current_user.get("id")
    
    # Employee restrictions
    if user_role == 4:
        if is_vendor == True:
            raise HTTPException(status_code=403, detail="Employees cannot access vendors")
        query["is_vendor"] = False
        query["$or"] = [
            {"mapped_employee_id": user_id},
            {"created_by": user_id}
        ]
    else:
        if is_vendor is not None:
            query["is_vendor"] = is_vendor
    
    # Pending approval filter (for admins)
    if pending_approval and user_role <= 3:
        query["approval_status"] = "pending"
    
    # Search filter
    if search:
        search_query = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"pan_number": {"$regex": search, "$options": "i"}},
            {"otc_ucc": {"$regex": search, "$options": "i"}}
        ]
        if "$or" in query:
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, {"$or": search_query}]
        else:
            query["$or"] = search_query
    
    clients = await db.clients.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    return clients


@router.get("/pending-approval", response_model=List[Client])
async def get_pending_clients(current_user: dict = Depends(get_current_user)):
    """Get clients pending approval (admin only)"""
    check_permission(current_user, "approve_clients")
    
    clients = await db.clients.find(
        {"approval_status": "pending", "is_vendor": False},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    return clients


@router.get("/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get a single client by ID"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0, "user_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    """Update a client (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can modify clients")
    
    result = await db.clients.update_one(
        {"id": client_id},
        {"$set": client_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated_client = await db.clients.find_one({"id": client_id}, {"_id": 0, "user_id": 0})
    return updated_client


@router.delete("/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete clients")
    
    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}


@router.put("/{client_id}/approve")
async def approve_client(client_id: str, approve: bool = True, current_user: dict = Depends(get_current_user)):
    """Approve or reject a client created by employee"""
    check_permission(current_user, "approve_clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {
        "is_active": approve,
        "approval_status": "approved" if approve else "rejected"
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Send notification email if approved
    if approve and client.get("email"):
        await send_email(
            client["email"],
            "Account Approved - Private Equity System",
            f"<p>Dear {client['name']},</p><p>Your account has been approved and is now active.</p>"
        )
    
    # Real-time notification to creator
    if client.get("created_by"):
        notif_type = "client_approved" if approve else "client_rejected"
        notif_title = f"Client {'Approved' if approve else 'Rejected'}"
        notif_message = f"Client '{client['name']}' has been {'approved' if approve else 'rejected'} by {current_user['name']}"
        await create_notification(
            client["created_by"],
            notif_type,
            notif_title,
            notif_message,
            {"client_id": client_id, "client_name": client["name"]}
        )
    
    return {"message": f"Client {'approved' if approve else 'rejected'} successfully"}


@router.post("/{client_id}/bank-account")
async def add_bank_account(client_id: str, bank_account: BankAccount, current_user: dict = Depends(get_current_user)):
    """Add another bank account to client"""
    check_permission(current_user, "manage_clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"bank_accounts": bank_account.model_dump()}}
    )
    
    return {"message": "Bank account added successfully"}


@router.post("/{client_id}/documents")
async def upload_client_document(
    client_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document for a client (PAN, CML, Cheque)"""
    user_role = current_user.get("role", 5)
    if user_role == 4:
        check_permission(current_user, "create_clients")
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only upload documents to your own clients")
    else:
        check_permission(current_user, "manage_clients")
    
    if user_role != 4:
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    # Create client directory
    client_dir = UPLOAD_DIR / client_id
    client_dir.mkdir(exist_ok=True)
    
    # Save file
    file_ext = Path(file.filename).suffix
    filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = client_dir / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Process OCR
    ocr_data = await process_document_ocr(str(file_path), doc_type)
    
    # Update client document record
    doc_record = {
        "doc_type": doc_type,
        "filename": filename,
        "file_path": str(file_path),
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "ocr_data": ocr_data
    }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"documents": doc_record}}
    )
    
    return {"message": "Document uploaded successfully", "document": doc_record}


@router.get("/{client_id}/documents/{filename}")
async def download_client_document(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a client document"""
    from fastapi.responses import FileResponse
    
    file_path = UPLOAD_DIR / client_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(file_path, filename=filename)


@router.get("/{client_id}/documents/{filename}/ocr")
async def get_document_ocr(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get OCR data for a specific document"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    document = None
    for doc in client.get("documents", []):
        if doc["filename"] == filename:
            document = doc
            break
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "filename": filename,
        "doc_type": document.get("doc_type"),
        "ocr_data": document.get("ocr_data"),
        "upload_date": document.get("upload_date")
    }


@router.put("/{client_id}/employee-mapping")
async def update_client_employee_mapping(
    client_id: str,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Map or unmap a client to an employee (admin only)"""
    if current_user.get("role", 5) > 2:
        raise HTTPException(status_code=403, detail="Only admins can map/unmap clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {}
    
    if employee_id:
        employee = await db.users.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        update_data = {
            "mapped_employee_id": employee_id,
            "mapped_employee_name": employee.get("name")
        }
    else:
        update_data = {
            "mapped_employee_id": None,
            "mapped_employee_name": None
        }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": update_data}
    )
    
    action = "mapped" if employee_id else "unmapped"
    return {"message": f"Client successfully {action}", "client_id": client_id, **update_data}


@router.post("/bulk-upload")
async def bulk_upload_clients(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Bulk upload clients from CSV"""
    check_permission(current_user, "manage_clients")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["name", "pan_number", "dp_id"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        clients_created = 0
        for _, row in df.iterrows():
            client_id = str(uuid.uuid4())
            otc_ucc = generate_otc_ucc(client_id)
            
            client_doc = {
                "id": client_id,
                "otc_ucc": otc_ucc,
                "name": str(row["name"]),
                "email": str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                "phone": str(row.get("phone", "")) if pd.notna(row.get("phone")) else None,
                "pan_number": str(row["pan_number"]),
                "dp_id": str(row["dp_id"]),
                "bank_name": str(row.get("bank_name", "")) if pd.notna(row.get("bank_name")) else None,
                "account_number": str(row.get("account_number", "")) if pd.notna(row.get("account_number")) else None,
                "ifsc_code": str(row.get("ifsc_code", "")) if pd.notna(row.get("ifsc_code")) else None,
                "is_vendor": bool(row.get("is_vendor", False)) if pd.notna(row.get("is_vendor")) else False,
                "documents": [],
                "mapped_employee_id": None,
                "mapped_employee_name": None,
                "user_id": current_user["id"],
                "created_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.clients.insert_one(client_doc)
            clients_created += 1
        
        return {"message": f"Successfully uploaded {clients_created} clients"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


@router.post("/{client_id}/clone")
async def clone_client_vendor(
    client_id: str, 
    target_type: str = Query(..., description="Target type: 'client' or 'vendor'"),
    current_user: dict = Depends(get_current_user)
):
    """Clone a client as vendor or vendor as client (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can clone clients/vendors")
    
    if target_type not in ["client", "vendor"]:
        raise HTTPException(status_code=400, detail="target_type must be 'client' or 'vendor'")
    
    source = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not source:
        raise HTTPException(status_code=404, detail="Source client/vendor not found")
    
    is_currently_vendor = source.get("is_vendor", False)
    if (target_type == "vendor" and is_currently_vendor) or (target_type == "client" and not is_currently_vendor):
        raise HTTPException(status_code=400, detail=f"This is already a {target_type}")
    
    existing = await db.clients.find_one({
        "pan_number": source["pan_number"],
        "is_vendor": target_type == "vendor"
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"A {target_type} with PAN {source['pan_number']} already exists"
        )
    
    new_id = str(uuid.uuid4())
    new_otc_ucc = generate_otc_ucc(new_id)
    
    cloned_doc = {
        "id": new_id,
        "otc_ucc": new_otc_ucc,
        "name": source["name"],
        "email": source.get("email"),
        "phone": source.get("phone"),
        "mobile": source.get("mobile"),
        "pan_number": source["pan_number"],
        "dp_id": source["dp_id"],
        "dp_type": source.get("dp_type", "outside"),
        "trading_ucc": source.get("trading_ucc"),
        "address": source.get("address"),
        "pin_code": source.get("pin_code"),
        "bank_accounts": source.get("bank_accounts", []),
        "is_vendor": target_type == "vendor",
        "is_active": True,
        "approval_status": "approved",
        "documents": [],
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_role": 1,
        "mapped_employee_id": None,
        "mapped_employee_name": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(cloned_doc)
    
    source_type = "vendor" if is_currently_vendor else "client"
    await create_audit_log(
        action="CLIENT_CREATE",
        entity_type=target_type,
        entity_id=new_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=1,
        entity_name=source["name"],
        details={
            "cloned_from": client_id,
            "source_type": source_type,
            "target_type": target_type,
            "pan_number": source["pan_number"]
        }
    )
    
    return {
        "message": f"Successfully cloned {source_type} '{source['name']}' as {target_type}",
        "id": new_id,
        "otc_ucc": new_otc_ucc
    }


@router.get("/{client_id}/portfolio")
async def get_client_portfolio(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get detailed portfolio for a specific client"""
    from models import ClientPortfolio, BookingWithDetails
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    bookings = await db.bookings.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
    
    stock_ids = list(set(b["stock_id"] for b in bookings))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    user_ids = list(set(b.get("created_by") for b in bookings if b.get("created_by")))
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "password": 0}).to_list(1000)
    user_map = {u["id"]: u for u in users}
    
    enriched_bookings = []
    total_profit_loss = 0
    open_bookings = 0
    closed_bookings = 0
    
    for b in bookings:
        stock = stock_map.get(b["stock_id"], {})
        creator = user_map.get(b.get("created_by"), {})
        
        profit_loss = None
        if b.get("status") == "closed" and b.get("selling_price"):
            profit_loss = (b["selling_price"] - b["buying_price"]) * b["quantity"]
            total_profit_loss += profit_loss
            closed_bookings += 1
        else:
            open_bookings += 1
        
        enriched_bookings.append(BookingWithDetails(
            id=b["id"],
            booking_number=b.get("booking_number"),
            client_id=b["client_id"],
            client_name=client["name"],
            client_pan=client.get("pan_number"),
            client_dp_id=client.get("dp_id"),
            stock_id=b["stock_id"],
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown"),
            quantity=b["quantity"],
            buying_price=b["buying_price"],
            selling_price=b.get("selling_price"),
            total_amount=b.get("selling_price", b["buying_price"]) * b["quantity"] if b.get("selling_price") else None,
            booking_date=b["booking_date"],
            status=b["status"],
            approval_status=b.get("approval_status", "pending"),
            approved_by=b.get("approved_by"),
            approved_at=b.get("approved_at"),
            notes=b.get("notes"),
            profit_loss=profit_loss,
            created_at=b["created_at"],
            created_by=b.get("created_by", ""),
            created_by_name=creator.get("name", "Unknown"),
            client_confirmation_status=b.get("client_confirmation_status", "pending"),
            client_confirmed_at=b.get("client_confirmed_at"),
            client_denial_reason=b.get("client_denial_reason"),
            is_loss_booking=b.get("is_loss_booking", False),
            loss_approval_status=b.get("loss_approval_status", "not_required"),
            loss_approved_by=b.get("loss_approved_by"),
            loss_approved_at=b.get("loss_approved_at"),
            payments=b.get("payments", []),
            total_paid=b.get("total_paid", 0),
            payment_status=b.get("payment_status", "pending"),
            payment_completed_at=b.get("payment_completed_at"),
            dp_transfer_ready=b.get("dp_transfer_ready", False)
        ))
    
    return ClientPortfolio(
        client_id=client_id,
        client_name=client["name"],
        total_bookings=len(bookings),
        open_bookings=open_bookings,
        closed_bookings=closed_bookings,
        total_profit_loss=total_profit_loss,
        bookings=enriched_bookings
    )
