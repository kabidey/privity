"""
Confirmation Notes Router
Handles confirmation note generation and management
Generated after DP transfer and sent to clients
"""
import os
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from database import db
from utils.auth import get_current_user
from services.audit_service import create_audit_log
from services.contract_note_service import (
    generate_contract_note_pdf,
    create_and_save_contract_note,
    generate_contract_note_number
)
from services.email_service import send_email
from services.file_storage import upload_file_to_gridfs, get_file_url
from services.permission_service import (
    has_permission,
    check_permission as check_dynamic_permission,
    require_permission
)

router = APIRouter(prefix="/contract-notes", tags=["Confirmation Notes"])


# Helper function for backward compatibility
def is_pe_level(role: int) -> bool:
    """Check if role is PE level (PE Desk or PE Manager)."""
    return role in [1, 2]


class ContractNote(BaseModel):
    id: str
    contract_note_number: str
    booking_id: str
    booking_number: str
    client_id: str
    stock_id: Optional[str] = None
    quantity: int
    rate: float
    gross_amount: float
    net_amount: float
    pdf_url: Optional[str] = None
    status: str
    email_sent: bool
    created_by: str
    created_by_name: str
    created_at: str
    # Enriched fields
    client_name: Optional[str] = None
    stock_symbol: Optional[str] = None


@router.get("", response_model=dict)
async def get_contract_notes(
    client_id: Optional[str] = None,
    booking_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.view", "view contract notes"))
):
    """
    Get contract notes with filters (requires contract_notes.view permission)
    """
    user_role = current_user.get("role", 6)
    
    query = {}
    
    if client_id:
        query["client_id"] = client_id
    if booking_id:
        query["booking_id"] = booking_id
    if status:
        query["status"] = status
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date + "T23:59:59"
        else:
            query["created_at"] = {"$lte": end_date + "T23:59:59"}
    
    total = await db.contract_notes.count_documents(query)
    notes = await db.contract_notes.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with client and stock names
    for note in notes:
        client = await db.clients.find_one({"id": note.get("client_id")}, {"_id": 0, "name": 1})
        stock = await db.stocks.find_one({"id": note.get("stock_id")}, {"_id": 0, "symbol": 1})
        note["client_name"] = client.get("name") if client else "Unknown"
        note["stock_symbol"] = stock.get("symbol") if stock else "Unknown"
    
    return {
        "total": total,
        "notes": notes,
        "limit": limit,
        "skip": skip
    }


@router.get("/{note_id}", response_model=ContractNote)
async def get_contract_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.view", "view contract notes"))
):
    """Get single contract note by ID (requires contract_notes.view permission)"""
    user_role = current_user.get("role", 6)
    
    note = await db.contract_notes.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Contract note not found")
    
    # Enrich
    client = await db.clients.find_one({"id": note.get("client_id")}, {"_id": 0, "name": 1})
    stock = await db.stocks.find_one({"id": note.get("stock_id")}, {"_id": 0, "symbol": 1})
    note["client_name"] = client.get("name") if client else "Unknown"
    note["stock_symbol"] = stock.get("symbol") if stock else "Unknown"
    
    return ContractNote(**note)


@router.post("/generate/{booking_id}")
async def generate_contract_note(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.generate", "generate contract notes"))
):
    """
    Generate contract note for a booking (requires contract_notes.generate permission)
    Usually triggered after DP transfer is marked complete
    """
    user_role = current_user.get("role", 6)
    
    # Check booking exists
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Check if contract note already exists
    existing = await db.contract_notes.find_one({"booking_id": booking_id}, {"_id": 0})
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Contract note already exists: {existing.get('contract_note_number')}"
        )
    
    # Check if DP transfer is complete
    if not booking.get("stock_transferred"):
        raise HTTPException(
            status_code=400,
            detail="Cannot generate contract note - DP transfer not complete"
        )
    
    try:
        # Generate contract note
        cn_doc = await create_and_save_contract_note(
            booking_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"]
        )
        
        # Create audit log
        await create_audit_log(
            action="CONTRACT_NOTE_GENERATED",
            entity_type="contract_note",
            entity_id=cn_doc["id"],
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            entity_name=cn_doc["contract_note_number"],
            details={
                "booking_id": booking_id,
                "booking_number": booking.get("booking_number"),
                "client_id": booking.get("client_id")
            }
        )
        
        return {
            "message": "Contract note generated successfully",
            "contract_note_number": cn_doc["contract_note_number"],
            "contract_note_id": cn_doc["id"],
            "pdf_url": cn_doc["pdf_url"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate contract note: {str(e)}")


@router.post("/generate-missing")
async def generate_missing_contract_notes(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.generate", "generate missing contract notes"))
):
    """
    Generate contract notes for all bookings that:
    - Have DP transfer complete (stock_transferred=True or dp_status=transferred)
    - Do not have a contract note yet
    
    Useful for backfilling missing contract notes
    """
    # Find bookings with completed DP transfer but no contract note
    transferred_bookings = await db.bookings.find({
        "$or": [
            {"stock_transferred": True},
            {"dp_status": "transferred"}
        ]
    }, {"_id": 0, "id": 1, "booking_number": 1}).to_list(10000)
    
    results = {
        "total_transferred": len(transferred_bookings),
        "already_have_cn": 0,
        "generated": 0,
        "failed": 0,
        "errors": []
    }
    
    for booking in transferred_bookings:
        booking_id = booking.get("id")
        
        # Check if contract note exists
        existing = await db.contract_notes.find_one({"booking_id": booking_id}, {"_id": 0, "contract_note_number": 1})
        if existing:
            results["already_have_cn"] += 1
            continue
        
        # Generate contract note
        try:
            cn_doc = await create_and_save_contract_note(
                booking_id=booking_id,
                user_id=current_user["id"],
                user_name=current_user["name"]
            )
            results["generated"] += 1
            logger.info(f"Generated missing CN {cn_doc.get('contract_note_number')} for booking {booking_id}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "booking_id": booking_id,
                "booking_number": booking.get("booking_number"),
                "error": str(e)
            })
            logger.error(f"Failed to generate CN for booking {booking_id}: {str(e)}")
    
    # Create audit log
    await create_audit_log(
        action="MISSING_CONTRACT_NOTES_GENERATED",
        entity_type="contract_note",
        entity_id="batch_generation",
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 6),
        entity_name="Batch Generation",
        details=results
    )
    
    return {
        "message": f"Generated {results['generated']} missing contract notes",
        "results": results
    }


@router.get("/download/{note_id}")
async def download_contract_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.download", "download contract note"))
):
    """Download contract note PDF"""
    
    note = await db.contract_notes.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Contract note not found")
    
    pdf_path = f"/app{note.get('pdf_url', '')}"
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Contract_Note_{note.get('contract_note_number', '').replace('/', '_')}.pdf"
    )


@router.post("/preview/{booking_id}")
async def preview_contract_note(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.view", "preview contract note"))
):
    """
    Preview contract note PDF without saving
    Returns PDF as stream
    """
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    try:
        pdf_buffer = await generate_contract_note_pdf(booking)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=Preview_CN_{booking_id[:8]}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")


@router.post("/send-email/{note_id}")
async def send_contract_note_email(
    note_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.send", "send contract note"))
):
    """
    Send contract note to client via email
    """
    
    note = await db.contract_notes.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Contract note not found")
    
    # Get client
    client = await db.clients.find_one({"id": note.get("client_id")}, {"_id": 0})
    if not client or not client.get("email"):
        raise HTTPException(status_code=400, detail="Client email not found")
    
    # Get stock
    stock = await db.stocks.find_one({"id": note.get("stock_id")}, {"_id": 0})
    stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
    
    # Get company master
    company = await db.company_master.find_one({"_id": "company_settings"})
    company_name = company.get("company_name", "SMIFS Capital Markets") if company else "SMIFS Capital Markets"
    
    # Prepare email
    subject = f"Contract Note - {note.get('contract_note_number')} | {stock_symbol}"
    
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #064E3B;">Contract Note - Transaction Complete</h2>
        <p>Dear {client.get('name', 'Client')},</p>
        <p>Your share purchase transaction has been completed successfully. Please find the Contract Note details below:</p>
        
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Contract Note No.</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{note.get('contract_note_number')}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking No.</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{note.get('booking_number')}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock_symbol}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">{note.get('quantity')}</td>
            </tr>
            <tr style="background-color: #f3f4f6;">
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Rate</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;">₹ {note.get('rate', 0):,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Net Amount</strong></td>
                <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>₹ {note.get('net_amount', 0):,.2f}</strong></td>
            </tr>
        </table>
        
        <p>The Contract Note PDF is attached to this email for your records.</p>
        
        <p style="color: #6b7280; font-size: 14px;">
            In case of any discrepancy, please report within 3 working days from the receipt of this document.
        </p>
        
        <p>Thank you for your business.</p>
        
        <p>Best regards,<br><strong>{company_name}</strong></p>
    </div>
    """
    
    # Read PDF file for attachment
    pdf_path = f"/app{note.get('pdf_url', '')}"
    pdf_content = None
    
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
    
    # Prepare attachment
    attachments = None
    if pdf_content:
        cn_number = note.get('contract_note_number', 'CN').replace('/', '_')
        attachments = [{
            'filename': f"Contract_Note_{cn_number}.pdf",
            'content': pdf_content,
            'content_type': 'application/pdf'
        }]
    
    # Send email with PDF attachment
    try:
        await send_email(
            to_email=client.get("email"),
            subject=subject,
            body=body,
            template_key="contract_note",
            related_entity_type="contract_note",
            related_entity_id=note_id,
            attachments=attachments
        )
        
        # Update contract note - mark as sent
        await db.contract_notes.update_one(
            {"id": note_id},
            {
                "$set": {
                    "status": "sent",
                    "email_sent": True,
                    "email_sent_at": datetime.now(timezone.utc).isoformat(),
                    "email_sent_by": current_user["name"]
                }
            }
        )
        
        # Create audit log
        await create_audit_log(
            action="CONTRACT_NOTE_EMAILED",
            entity_type="contract_note",
            entity_id=note_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 6),
            entity_name=note.get("contract_note_number"),
            details={"client_email": client.get("email")}
        )
        
        return {"message": f"Contract note sent to {client.get('email')}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/by-booking/{booking_id}")
async def get_contract_note_by_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.view", "view contract note by booking"))
):
    """Get contract note for a specific booking"""
    
    note = await db.contract_notes.find_one({"booking_id": booking_id}, {"_id": 0})
    
    if not note:
        return {"exists": False, "note": None}
    
    # Enrich
    client = await db.clients.find_one({"id": note.get("client_id")}, {"_id": 0, "name": 1})
    stock = await db.stocks.find_one({"id": note.get("stock_id")}, {"_id": 0, "symbol": 1})
    note["client_name"] = client.get("name") if client else "Unknown"
    note["stock_symbol"] = stock.get("symbol") if stock else "Unknown"
    
    return {"exists": True, "note": note}


@router.post("/regenerate/{note_id}")
async def regenerate_contract_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("contract_notes.generate", "regenerate contract note"))
):
    """
    Regenerate an existing contract note PDF
    Useful when client/stock details have been updated
    Stronger regeneration with multiple fallback methods
    """
    note = await db.contract_notes.find_one({"id": note_id}, {"_id": 0})
    if not note:
        raise HTTPException(status_code=404, detail="Contract note not found")
    
    booking_id = note.get("booking_id")
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Associated booking not found")
    
    try:
        # Delete old PDF file if exists
        old_pdf_path = f"/app{note.get('pdf_url', '')}"
        if old_pdf_path and os.path.exists(old_pdf_path):
            try:
                os.remove(old_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to delete old PDF: {e}")
        
        # Regenerate PDF with fresh data
        pdf_buffer = await generate_contract_note_pdf(booking)
        pdf_content = pdf_buffer.getvalue()
        
        if not pdf_content or len(pdf_content) < 100:
            raise ValueError("Generated PDF is empty or too small")
        
        # Create directories
        cn_dir = "/app/uploads/contract_notes"
        os.makedirs(cn_dir, exist_ok=True)
        
        cn_number = note.get("contract_note_number", "CN")
        filename = f"CN_{cn_number.replace('/', '_')}_{booking_id[:8]}_regen.pdf"
        filepath = os.path.join(cn_dir, filename)
        
        # Save to disk
        with open(filepath, "wb") as f:
            f.write(pdf_content)
        
        # Also upload to GridFS for backup
        try:
            file_id = await upload_file_to_gridfs(
                pdf_content,
                filename,
                "application/pdf",
                {
                    "category": "contract_notes",
                    "entity_id": booking_id,
                    "contract_note_number": cn_number,
                    "regenerated": True,
                    "created_by": current_user["id"]
                }
            )
            gridfs_url = get_file_url(file_id)
        except Exception as e:
            logger.warning(f"GridFS upload failed during regeneration: {e}")
            file_id = None
            gridfs_url = None
        
        # Update contract note record
        update_data = {
            "pdf_url": f"/uploads/contract_notes/{filename}",
            "regenerated_at": datetime.now(timezone.utc).isoformat(),
            "regenerated_by": current_user["id"],
            "regenerated_by_name": current_user["name"],
            "regeneration_count": note.get("regeneration_count", 0) + 1
        }
        
        if file_id:
            update_data["file_id"] = file_id
            update_data["gridfs_url"] = gridfs_url
        
        await db.contract_notes.update_one(
            {"id": note_id},
            {"$set": update_data}
        )
        
        # Create audit log
        await create_audit_log(
            action="CONTRACT_NOTE_REGENERATED",
            entity_type="contract_note",
            entity_id=note_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=current_user.get("role", 6),
            entity_name=cn_number,
            details={
                "booking_id": booking_id,
                "pdf_size_bytes": len(pdf_content),
                "gridfs_backup": file_id is not None
            }
        )
        
        return {
            "success": True,
            "message": "Contract note regenerated successfully",
            "contract_note_number": cn_number,
            "pdf_url": f"/uploads/contract_notes/{filename}",
            "pdf_size": len(pdf_content)
        }
    
    except Exception as e:
        logger.error(f"Failed to regenerate contract note {note_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate contract note: {str(e)}")
