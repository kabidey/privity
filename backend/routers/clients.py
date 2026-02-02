"""
Clients Router

Handles all client and vendor management operations.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os
import aiofiles
from pathlib import Path

from database import db
from config import is_pe_level, is_pe_desk_only, ROLES, UPLOAD_DIR
from models import ClientCreate, Client, BankAccount, ClientSuspensionRequest
from utils.auth import get_current_user, check_permission
from services.notification_service import notify_roles, create_notification
from services.audit_service import create_audit_log
from services.email_service import send_templated_email, send_email, get_email_template
from services.ocr_service import process_document_ocr
from services.file_storage import upload_file_to_gridfs, get_file_url

router = APIRouter(tags=["Clients"])


async def generate_otc_ucc() -> str:
    """Generate unique OTC UCC code"""
    counter = await db.counters.find_one_and_update(
        {"_id": "otc_ucc"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    seq = counter.get("seq", 1)
    return f"OTC{str(seq).zfill(6)}"


@router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    """Create a new client or vendor."""
    user_role = current_user.get("role", 5)
    
    # Employees and Finance cannot create vendors
    if user_role in [4, 7] and client_data.is_vendor:
        raise HTTPException(status_code=403, detail="You do not have permission to create vendors")
    
    # Check for duplicate PAN
    existing = await db.clients.find_one(
        {"pan_number": client_data.pan_number.upper()},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"{'Vendor' if client_data.is_vendor else 'Client'} with PAN {client_data.pan_number} already exists"
        )
    
    # STRICT RULE: Client cannot be an RP - Check by PAN
    existing_rp_pan = await db.referral_partners.find_one(
        {"pan_number": client_data.pan_number.upper()},
        {"_id": 0, "name": 1, "pan_number": 1, "rp_code": 1}
    )
    if existing_rp_pan:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create {'Vendor' if client_data.is_vendor else 'Client'}: This PAN ({client_data.pan_number.upper()}) belongs to an existing Referral Partner ({existing_rp_pan.get('name', 'Unknown')} - {existing_rp_pan.get('rp_code', '')}). An RP cannot be a Client."
        )
    
    # STRICT RULE: Client cannot be an RP - Check by Email (if email provided)
    if client_data.email:
        existing_rp_email = await db.referral_partners.find_one(
            {"email": client_data.email.lower()},
            {"_id": 0, "name": 1, "email": 1, "rp_code": 1}
        )
        if existing_rp_email:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create {'Vendor' if client_data.is_vendor else 'Client'}: This email ({client_data.email}) belongs to an existing Referral Partner ({existing_rp_email.get('name', 'Unknown')} - {existing_rp_email.get('rp_code', '')}). An RP cannot be a Client."
            )
    
    # STRICT RULE: System users (those with accounts) cannot be created as clients - Check by PAN
    existing_user_pan = await db.users.find_one(
        {"pan_number": client_data.pan_number.upper()},
        {"_id": 0, "name": 1, "email": 1, "pan_number": 1}
    )
    if existing_user_pan:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create {'Vendor' if client_data.is_vendor else 'Client'}: This PAN ({client_data.pan_number.upper()}) belongs to an existing system user ({existing_user_pan.get('name', 'Unknown')} - {existing_user_pan.get('email', '')}). System users cannot be mapped as Clients."
        )
    
    # STRICT RULE: System users cannot be created as clients - Check by Email
    if client_data.email:
        existing_user_email = await db.users.find_one(
            {"email": client_data.email.lower()},
            {"_id": 0, "name": 1, "email": 1}
        )
        if existing_user_email:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create {'Vendor' if client_data.is_vendor else 'Client'}: This email ({client_data.email}) belongs to an existing system user ({existing_user_email.get('name', 'Unknown')}). System users cannot be mapped as Clients."
            )
    
    client_id = str(uuid.uuid4())
    
    # PE Desk/Manager created clients are auto-approved
    approval_status = "approved" if is_pe_level(user_role) else "pending"
    
    # Generate OTC UCC
    otc_ucc = await generate_otc_ucc()
    
    # Auto-map client to creator (all roles)
    client_doc = {
        "id": client_id,
        "otc_ucc": otc_ucc,
        "name": client_data.name,
        "email": client_data.email,
        "email_secondary": client_data.email_secondary,
        "email_tertiary": client_data.email_tertiary,
        "phone": client_data.phone,
        "mobile": client_data.mobile,
        "pan_number": client_data.pan_number.upper(),
        "dp_id": client_data.dp_id,
        "dp_type": client_data.dp_type,
        "trading_ucc": client_data.trading_ucc,
        "address": client_data.address,
        "pin_code": client_data.pin_code,
        "is_vendor": client_data.is_vendor,
        "is_proprietor": client_data.is_proprietor,
        "has_name_mismatch": client_data.has_name_mismatch,
        "bank_accounts": [acc.model_dump() for acc in client_data.bank_accounts] if client_data.bank_accounts else [],
        "documents": [],
        "approval_status": approval_status,
        "approved_by": current_user["id"] if is_pe_level(user_role) else None,
        "approved_at": datetime.now(timezone.utc).isoformat() if is_pe_level(user_role) else None,
        "is_active": True,
        "is_suspended": False,
        "suspension_reason": None,
        "suspended_at": None,
        "suspended_by": None,
        # Auto-map client to creator for ALL roles
        "mapped_employee_id": current_user["id"],
        "mapped_employee_name": current_user["name"],
        "mapped_employee_email": current_user.get("email"),
        "is_cloned": False,
        "cloned_from_id": None,
        "cloned_from_type": None,
        "created_by": current_user["id"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(client_doc)
    
    # Create audit log
    await create_audit_log(
        action="CLIENT_CREATE" if not client_data.is_vendor else "VENDOR_CREATE",
        entity_type="client" if not client_data.is_vendor else "vendor",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=client_data.name,
        details={
            "pan_number": client_data.pan_number, 
            "is_vendor": client_data.is_vendor,
            "is_proprietor": client_data.is_proprietor,
            "has_name_mismatch": client_data.has_name_mismatch
        }
    )
    
    # Notify PE Desk if client needs approval
    if approval_status == "pending":
        await notify_roles(
            [1, 2],
            "client_pending",
            f"New {'Vendor' if client_data.is_vendor else 'Client'} Pending Approval",
            f"'{client_data.name}' ({client_data.pan_number}) requires approval",
            {"client_id": client_id, "client_name": client_data.name}
        )
    
    # Send welcome email if auto-approved (PE Level created)
    if approval_status == "approved" and client_data.email:
        entity_type = "vendor" if client_data.is_vendor else "client"
        subject = f"Welcome - Your {entity_type.title()} Account is Active"
        body = f"""Dear {client_data.name},

Welcome to SMIFS Private Equity!

Your {entity_type} account has been successfully created and is now active.

Your Account Details:
- Name: {client_data.name}
- OTC UCC: {otc_ucc}
- PAN: {client_data.pan_number}
- DP ID: {client_data.dp_id}

{"You can now receive purchase orders and stock transfer requests from us." if client_data.is_vendor else "You can now place orders and manage your portfolio with us."}

If you have any questions, please contact our PE Desk.

Best Regards,
SMIFS Private Equity Team"""
        
        await send_email(
            to_email=client_data.email,
            subject=subject,
            body=body,
            template_key="welcome",
            variables={"client_name": client_data.name, "otc_ucc": otc_ucc},
            related_entity_type=entity_type,
            related_entity_id=client_id
        )
    
    return Client(**{k: v for k, v in client_doc.items() if k != "_id"})


@router.get("/clients", response_model=List[Client])
async def get_clients(
    search: Optional[str] = None,
    is_vendor: Optional[bool] = None,
    pending_approval: Optional[bool] = None,
    include_unmapped: Optional[bool] = False,
    current_user: dict = Depends(get_current_user)
):
    """Get all clients with optional filters based on hierarchy."""
    from services.hierarchy_service import get_team_user_ids
    
    query = {}
    user_role = current_user.get("role", 5)
    user_id = current_user.get("id")
    hierarchy_level = current_user.get("hierarchy_level", 1)
    
    # PE Level sees everything
    if is_pe_level(user_role):
        if is_vendor is not None:
            query["is_vendor"] = is_vendor
    # Finance role sees all clients (no vendors)
    elif user_role == 6:
        query["is_vendor"] = False
    # Viewer sees all but read-only
    elif user_role == 7:
        if is_vendor is not None:
            query["is_vendor"] = is_vendor
    # Employee/Manager/Zonal/Regional/Business Head - use hierarchy
    else:
        if is_vendor == True:
            raise HTTPException(status_code=403, detail="You do not have access to vendors")
        query["is_vendor"] = False
        
        # Get team user IDs based on hierarchy
        team_ids = await get_team_user_ids(user_id, include_self=True)
        
        # Filter clients by team
        query["$or"] = [
            {"mapped_employee_id": {"$in": team_ids}},
            {"created_by": {"$in": team_ids}}
        ]
    
    # Pending approval filter (for PE Level only)
    if pending_approval and is_pe_level(user_role):
        query["approval_status"] = "pending"
    
    # Unmapped clients - only PE Level can see
    if include_unmapped and is_pe_level(user_role):
        # Remove the team filter and add unmapped filter
        if "$or" in query:
            existing_or = query.pop("$or")
            query["$or"] = existing_or + [
                {"mapped_employee_id": None},
                {"mapped_employee_id": {"$exists": False}},
                {"mapped_employee_id": ""}
            ]
    
    # Search filter
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        search_conditions = [
            {"name": search_regex},
            {"pan_number": search_regex},
            {"email": search_regex},
            {"phone": search_regex}
        ]
        if "$or" in query:
            # Combine with existing $or using $and
            query = {"$and": [{"$or": query["$or"]}, {"$or": search_conditions}]}
        else:
            query["$or"] = search_conditions
    
    clients = await db.clients.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    return [Client(**c) for c in clients]


@router.get("/clients/pending-approval", response_model=List[Client])
async def get_pending_clients(current_user: dict = Depends(get_current_user)):
    """Get clients pending approval (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can view pending approvals")
    
    clients = await db.clients.find({"approval_status": "pending"}, {"_id": 0}).to_list(1000)
    return [Client(**c) for c in clients]


@router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific client by ID."""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**client)


@router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    """Update an existing client."""
    existing = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {
        "name": client_data.name,
        "email": client_data.email,
        "email_secondary": client_data.email_secondary,
        "email_tertiary": client_data.email_tertiary,
        "phone": client_data.phone,
        "mobile": client_data.mobile,
        "pan_number": client_data.pan_number.upper(),
        "dp_id": client_data.dp_id,
        "dp_type": client_data.dp_type,
        "trading_ucc": client_data.trading_ucc,
        "address": client_data.address,
        "pin_code": client_data.pin_code,
        "is_vendor": client_data.is_vendor,
        "bank_accounts": [acc.model_dump() for acc in client_data.bank_accounts] if client_data.bank_accounts else existing.get("bank_accounts", []),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return Client(**updated)


@router.put("/clients/{client_id}/approve")
async def approve_client(client_id: str, approve: bool = True, current_user: dict = Depends(get_current_user)):
    """Approve or reject a client (PE Level only)."""
    user_role = current_user.get("role", 6)
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can approve clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # PE Manager cannot approve proprietor clients with name mismatch unless bank proof is uploaded
    # PE Desk (role 1) can bypass this check
    if approve and user_role == 2:  # PE Manager
        is_proprietor = client.get("is_proprietor", False)
        has_name_mismatch = client.get("has_name_mismatch", False)
        bank_proof_url = client.get("bank_proof_url")
        
        if is_proprietor and has_name_mismatch and not bank_proof_url:
            raise HTTPException(
                status_code=400, 
                detail="Cannot approve: This is a proprietorship client with name mismatch. Bank Proof must be uploaded before approval."
            )
    
    update_data = {
        "approval_status": "approved" if approve else "rejected",
        "approved_by": current_user["id"],
        "approved_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(
        action="CLIENT_APPROVE" if approve else "CLIENT_REJECT",
        entity_type="client",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name=client["name"],
        details={"approved": approve}
    )
    
    # Notify creator
    if client.get("created_by"):
        await create_notification(
            client["created_by"],
            "client_approved" if approve else "client_rejected",
            f"Client {'Approved' if approve else 'Rejected'}",
            f"Client '{client['name']}' has been {'approved' if approve else 'rejected'}",
            {"client_id": client_id}
        )
    
    # Send email to client
    client_email = client.get("email")
    if client_email:
        template_key = "client_approved" if approve else "client_rejected"
        template = await get_email_template(template_key)
        
        if template:
            subject = template["subject"].replace("{{client_name}}", client["name"])
            body = template["body"].replace("{{client_name}}", client["name"])
            body = body.replace("{{otc_ucc}}", client.get("otc_ucc", "N/A"))
            
            await send_email(
                to_email=client_email,
                subject=subject,
                body=body,
                template_key=template_key,
                variables={"client_name": client["name"], "otc_ucc": client.get("otc_ucc")},
                related_entity_type="client",
                related_entity_id=client_id
            )
    
    return {"message": f"Client {'approved' if approve else 'rejected'} successfully"}


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a client (PE Desk only)."""
    if not is_pe_desk_only(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk can delete clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check for existing bookings
    booking_count = await db.bookings.count_documents({"client_id": client_id})
    if booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete client with existing bookings ({booking_count} bookings)"
        )
    
    await db.clients.delete_one({"id": client_id})
    
    # Create audit log
    await create_audit_log(
        action="CLIENT_DELETE",
        entity_type="client",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name=client["name"]
    )
    
    return {"message": f"Client '{client['name']}' deleted successfully"}


@router.put("/clients/{client_id}/suspend")
async def suspend_client(
    client_id: str,
    suspension: ClientSuspensionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Suspend a client (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can suspend clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.get("is_suspended"):
        raise HTTPException(status_code=400, detail="Client is already suspended")
    
    update_data = {
        "is_suspended": True,
        "suspension_reason": suspension.reason,
        "suspended_at": datetime.now(timezone.utc).isoformat(),
        "suspended_by": current_user["id"]
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(
        action="CLIENT_SUSPEND",
        entity_type="client",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name=client["name"],
        details={"reason": suspension.reason}
    )
    
    return {"message": f"Client '{client['name']}' suspended successfully"}


@router.put("/clients/{client_id}/unsuspend")
async def unsuspend_client(
    client_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Unsuspend a client (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can unsuspend clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if not client.get("is_suspended"):
        raise HTTPException(status_code=400, detail="Client is not suspended")
    
    update_data = {
        "is_suspended": False,
        "suspension_reason": None,
        "suspended_at": None,
        "suspended_by": None,
        "unsuspended_at": datetime.now(timezone.utc).isoformat(),
        "unsuspended_by": current_user["id"]
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(
        action="CLIENT_UNSUSPEND",
        entity_type="client",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name=client["name"]
    )
    
    return {"message": f"Client '{client['name']}' unsuspended successfully"}


@router.post("/clients/{client_id}/bank-account")
async def add_bank_account(client_id: str, bank_account: BankAccount, current_user: dict = Depends(get_current_user)):
    """Add a bank account to a client."""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    bank_accounts = client.get("bank_accounts", [])
    bank_accounts.append(bank_account.model_dump())
    
    await db.clients.update_one({"id": client_id}, {"$set": {"bank_accounts": bank_accounts}})
    
    return {"message": "Bank account added successfully"}


@router.put("/clients/{client_id}/employee-mapping")
async def update_client_employee_mapping(
    client_id: str,
    employee_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Map a client to an employee (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can update employee mapping")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Verify employee exists
    employee = await db.users.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {"mapped_employee_id": employee_id}}
    )
    
    return {"message": f"Client mapped to {employee['name']} successfully"}


# Document Management Endpoints
@router.post("/clients/{client_id}/documents")
async def upload_client_document(
    client_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a document for a client with OCR processing. Stored in GridFS for persistence."""
    user_role = current_user.get("role", 5)
    
    # Allow both manage_clients (managers+) and create_clients (employees) to upload docs
    if user_role == 5:  # Employee
        check_permission(current_user, "create_clients")
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only upload documents to your own clients")
    else:
        check_permission(current_user, "manage_clients")
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    # Read file content
    content = await file.read()
    
    # Generate filename
    file_ext = Path(file.filename).suffix
    filename = f"{doc_type}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{file_ext}"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        content,
        filename,
        file.content_type or "application/octet-stream",
        {
            "category": "client_documents",
            "entity_id": client_id,
            "doc_type": doc_type,
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
    )
    
    # Also save locally for OCR processing (temporary)
    client_dir = UPLOAD_DIR / client_id
    client_dir.mkdir(exist_ok=True)
    file_path = client_dir / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Process OCR
    ocr_data = await process_document_ocr(str(file_path), doc_type)
    
    # Update client document record with GridFS file_id
    doc_record = {
        "doc_type": doc_type,
        "filename": filename,
        "file_id": file_id,  # GridFS file ID for persistent access
        "file_url": get_file_url(file_id),  # URL to access file
        "file_path": str(file_path),  # Local path (may not persist)
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "ocr_data": ocr_data
    }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"documents": doc_record}}
    )
    
    return {"message": "Document uploaded successfully", "document": doc_record}


@router.post("/clients/{client_id}/bank-proof")
async def upload_bank_proof(
    client_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload bank proof document for proprietor clients with name mismatch (PE Level only). Stored in GridFS."""
    user_role = current_user.get("role", 6)
    
    # Only PE Desk and PE Manager can upload bank proof
    if not is_pe_level(user_role):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can upload bank proof")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Validate this is a proprietor client with name mismatch
    if not client.get("is_proprietor") or not client.get("has_name_mismatch"):
        raise HTTPException(status_code=400, detail="Bank proof upload is only required for proprietor clients with name mismatch")
    
    # Read file content
    content = await file.read()
    
    # Generate filename
    file_ext = Path(file.filename).suffix
    filename = f"bank_proof_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{file_ext}"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        content,
        filename,
        file.content_type or "application/octet-stream",
        {
            "category": "client_bank_proof",
            "entity_id": client_id,
            "doc_type": "bank_proof",
            "uploaded_by": current_user.get("id"),
            "uploaded_by_name": current_user.get("name")
        }
    )
    
    # Also save locally (for backward compatibility)
    client_dir = UPLOAD_DIR / client_id
    client_dir.mkdir(exist_ok=True)
    file_path = client_dir / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Update client with bank proof URL (use GridFS URL)
    bank_proof_url = get_file_url(file_id)
    update_data = {
        "bank_proof_url": bank_proof_url,
        "bank_proof_file_id": file_id,
        "bank_proof_uploaded_by": current_user["id"],
        "bank_proof_uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Also add to documents array for consistency
    doc_record = {
        "doc_type": "bank_proof",
        "filename": filename,
        "file_id": file_id,
        "file_url": bank_proof_url,
        "file_path": str(file_path),
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "ocr_data": None
    }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"documents": doc_record}}
    )
    
    # Create audit log
    await create_audit_log(
        action="BANK_PROOF_UPLOAD",
        entity_type="client",
        entity_id=client_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=client["name"],
        details={"filename": filename, "file_id": file_id, "is_proprietor": True, "has_name_mismatch": True}
    )
    
    return {
        "message": "Bank proof uploaded successfully", 
        "bank_proof_url": bank_proof_url,
        "file_id": file_id,
        "uploaded_by": current_user["name"],
        "uploaded_at": update_data["bank_proof_uploaded_at"]
    }


@router.get("/clients/{client_id}/documents/{filename}")
async def download_client_document(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a client document."""
    from fastapi.responses import FileResponse
    
    file_path = UPLOAD_DIR / client_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(file_path, filename=filename)


@router.get("/clients/{client_id}/documents/{filename}/ocr")
async def get_document_ocr(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get OCR data for a specific document."""
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


@router.post("/ocr/preview")
async def ocr_preview(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Process OCR on a document without saving - for auto-fill preview."""
    import uuid as uuid_module
    
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    file_ext = Path(file.filename).suffix
    temp_filename = f"temp_{uuid_module.uuid4()}{file_ext}"
    temp_path = temp_dir / temp_filename
    
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        ocr_data = await process_document_ocr(str(temp_path), doc_type)
        return ocr_data
    finally:
        if temp_path.exists():
            temp_path.unlink()


@router.post("/clients/{client_id}/clone")
async def clone_client_vendor(
    client_id: str, 
    target_type: str = Query(..., description="Target type: 'client' or 'vendor'"),
    current_user: dict = Depends(get_current_user)
):
    """Clone a client as vendor or vendor as client (PE Level only)."""
    if not is_pe_level(current_user.get("role", 6)):
        raise HTTPException(status_code=403, detail="Only PE Desk or PE Manager can clone clients/vendors")
    
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
    otc_ucc = await generate_otc_ucc()
    
    cloned_doc = {
        "id": new_id,
        "otc_ucc": otc_ucc,
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
        "documents": source.get("documents", []),  # Copy documents from source
        "is_proprietor": source.get("is_proprietor", False),
        "has_name_mismatch": source.get("has_name_mismatch", False),
        "bank_proof_url": source.get("bank_proof_url"),
        "bank_proof_uploaded_by": source.get("bank_proof_uploaded_by"),
        "bank_proof_uploaded_at": source.get("bank_proof_uploaded_at"),
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_role": current_user.get("role", 1),
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
        user_role=current_user.get("role", 1),
        entity_name=source["name"],
        details={
            "cloned_from": client_id,
            "source_type": source_type,
            "target_type": target_type,
            "pan_number": source["pan_number"]
        }
    )
    
    # Send email notification for conversion
    entity_email = source.get("email")
    if entity_email:
        if target_type == "vendor":
            # Client converted to Vendor
            subject = f"Welcome as Vendor - {source['name']}"
            body = f"""Dear {source['name']},

We are pleased to inform you that your account has been registered as a Vendor in our system.

Your Vendor Details:
- Name: {source['name']}
- OTC UCC: {otc_ucc}
- PAN: {source['pan_number']}
- DP ID: {source['dp_id']}

You can now receive purchase orders and stock transfer requests from us.

If you have any questions, please contact our PE Desk.

Best Regards,
SMIFS Private Equity Team"""
        else:
            # Vendor converted to Client
            subject = f"Welcome as Client - {source['name']}"
            body = f"""Dear {source['name']},

We are pleased to inform you that your account has been registered as a Client in our system.

Your Client Details:
- Name: {source['name']}
- OTC UCC: {otc_ucc}
- PAN: {source['pan_number']}
- DP ID: {source['dp_id']}

You can now place orders and manage your portfolio with us.

If you have any questions, please contact our PE Desk.

Best Regards,
SMIFS Private Equity Team"""
        
        await send_email(
            to_email=entity_email,
            subject=subject,
            body=body,
            template_key=f"{source_type}_to_{target_type}_conversion",
            variables={"name": source["name"], "otc_ucc": otc_ucc, "pan_number": source["pan_number"]},
            related_entity_type=target_type,
            related_entity_id=new_id
        )
    
    return {
        "message": f"Successfully cloned {source_type} '{source['name']}' as {target_type}",
        "id": new_id,
        "otc_ucc": otc_ucc
    }


@router.get("/clients/{client_id}/portfolio")
async def get_client_portfolio(client_id: str, current_user: dict = Depends(get_current_user)):
    """Get a client's portfolio showing all their holdings."""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get all completed bookings for this client
    bookings = await db.bookings.find({
        "client_id": client_id,
        "stock_transferred": True,
        "is_voided": {"$ne": True}
    }, {"_id": 0}).to_list(10000)
    
    # Group by stock and calculate holdings
    holdings = {}
    for booking in bookings:
        stock_id = booking.get("stock_id")
        if stock_id not in holdings:
            holdings[stock_id] = {
                "stock_id": stock_id,
                "stock_symbol": booking.get("stock_symbol", ""),
                "stock_name": booking.get("stock_name", ""),
                "quantity": 0,
                "total_value": 0,
                "avg_price": 0,
                "bookings": []
            }
        
        qty = booking.get("quantity", 0)
        price = booking.get("selling_price", 0)
        holdings[stock_id]["quantity"] += qty
        holdings[stock_id]["total_value"] += qty * price
        holdings[stock_id]["bookings"].append({
            "booking_number": booking.get("booking_number"),
            "quantity": qty,
            "price": price,
            "date": booking.get("created_at")
        })
    
    # Calculate average price
    for stock_id, holding in holdings.items():
        if holding["quantity"] > 0:
            holding["avg_price"] = holding["total_value"] / holding["quantity"]
    
    portfolio_list = list(holdings.values())
    total_portfolio_value = sum(h["total_value"] for h in portfolio_list)
    
    return {
        "client_id": client_id,
        "client_name": client.get("name"),
        "otc_ucc": client.get("otc_ucc"),
        "holdings": portfolio_list,
        "total_value": total_portfolio_value,
        "total_stocks": len(portfolio_list)
    }

