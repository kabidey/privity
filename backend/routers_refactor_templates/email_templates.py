"""
Email template management routes
"""
from fastapi import APIRouter, HTTPException, Depends

from database import db
from config import DEFAULT_EMAIL_TEMPLATES
from models import EmailTemplateUpdate, EmailTemplatePreview
from utils.auth import get_current_user

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])


@router.get("")
async def get_email_templates(current_user: dict = Depends(get_current_user)):
    """Get all email templates (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    
    if not templates:
        for key, template in DEFAULT_EMAIL_TEMPLATES.items():
            await db.email_templates.insert_one(template)
        templates = list(DEFAULT_EMAIL_TEMPLATES.values())
    
    return templates


@router.get("/{template_key}")
async def get_email_template(template_key: str, current_user: dict = Depends(get_current_user)):
    """Get a specific email template"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        if template_key in DEFAULT_EMAIL_TEMPLATES:
            template = DEFAULT_EMAIL_TEMPLATES[template_key]
            await db.email_templates.insert_one(template)
        else:
            raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.put("/{template_key}")
async def update_email_template(
    template_key: str,
    update_data: EmailTemplateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an email template (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        if template_key in DEFAULT_EMAIL_TEMPLATES:
            template = DEFAULT_EMAIL_TEMPLATES[template_key]
            await db.email_templates.insert_one(template)
        else:
            raise HTTPException(status_code=404, detail="Template not found")
    
    update_fields = {}
    if update_data.subject is not None:
        update_fields["subject"] = update_data.subject
    if update_data.body is not None:
        update_fields["body"] = update_data.body
    if update_data.is_active is not None:
        update_fields["is_active"] = update_data.is_active
    
    if update_fields:
        await db.email_templates.update_one(
            {"key": template_key},
            {"$set": update_fields}
        )
    
    updated = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    return updated


@router.post("/{template_key}/reset")
async def reset_email_template(template_key: str, current_user: dict = Depends(get_current_user)):
    """Reset template to default (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    if template_key not in DEFAULT_EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Default template not found")
    
    default = DEFAULT_EMAIL_TEMPLATES[template_key]
    await db.email_templates.update_one(
        {"key": template_key},
        {"$set": default},
        upsert=True
    )
    
    return {"message": "Template reset to default", "template": default}


@router.post("/{template_key}/preview")
async def preview_email_template(
    template_key: str,
    preview_data: EmailTemplatePreview,
    current_user: dict = Depends(get_current_user)
):
    """Preview email template with sample data"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        if template_key in DEFAULT_EMAIL_TEMPLATES:
            template = DEFAULT_EMAIL_TEMPLATES[template_key]
        else:
            raise HTTPException(status_code=404, detail="Template not found")
    
    subject = template["subject"]
    body = template["body"]
    
    for key, value in preview_data.variables.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
        body = body.replace(f"{{{{{key}}}}}", str(value))
    
    return {
        "subject": subject,
        "body": body
    }
