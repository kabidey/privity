"""
Email Templates Router
Handles email template CRUD operations and SMTP configuration
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from database import db
from routers.auth import get_current_user
from config import DEFAULT_EMAIL_TEMPLATES as EMAIL_TEMPLATES
from services.email_service import render_template
from services.permission_service import require_permission

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])


# ============== Pydantic Models ==============
class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class EmailTemplatePreview(BaseModel):
    variables: dict = {}


# ============== Email Template Endpoints ==============
@router.get("")
async def get_email_templates(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.templates", "view email templates"))
):
    """Get all email templates (PE Desk only)"""
    # Get templates from database (custom overrides)
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    db_templates = {t["key"]: t for t in templates}
    
    # Merge with default templates
    result = []
    for key, default_template in EMAIL_TEMPLATES.items():
        custom = db_templates.get(key, {})
        result.append({
            "key": key,
            "name": default_template.get("name", key),
            "subject": custom.get("subject") or default_template.get("subject", ""),
            "body": custom.get("body") or default_template.get("body", ""),
            "variables": default_template.get("variables", []),
            "is_customized": key in db_templates
        })
    
    return result


@router.get("/{template_key}")
async def get_email_template(
    template_key: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("email.templates", "view email template"))
):
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    default_template = EMAIL_TEMPLATES.get(template_key)
    
    if not default_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "key": template_key,
        "name": default_template.get("name", template_key),
        "subject": template.get("subject") if template else default_template.get("subject", ""),
        "body": template.get("body") if template else default_template.get("body", ""),
        "variables": default_template.get("variables", []),
        "is_customized": template is not None
    }


@router.put("/{template_key}")
async def update_email_template(
    template_key: str,
    update_data: EmailTemplateUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an email template (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update email templates")
    
    if template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    
    existing = await db.email_templates.find_one({"key": template_key})
    
    update_dict = {
        "key": template_key,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if update_data.subject is not None:
        update_dict["subject"] = update_data.subject
    if update_data.body is not None:
        update_dict["body"] = update_data.body
    
    if existing:
        await db.email_templates.update_one(
            {"key": template_key},
            {"$set": update_dict}
        )
    else:
        new_template = {
            **update_dict,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["id"]
        }
        await db.email_templates.insert_one(new_template)
    
    return {"message": "Template updated successfully"}


@router.post("/{template_key}/reset")
async def reset_email_template(template_key: str, current_user: dict = Depends(get_current_user)):
    """Reset an email template to default (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can reset email templates")
    
    if template_key not in EMAIL_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.email_templates.delete_one({"key": template_key})
    return {"message": "Template reset to default"}


@router.post("/{template_key}/preview")
async def preview_email_template(
    template_key: str,
    preview_data: EmailTemplatePreview,
    current_user: dict = Depends(get_current_user)
):
    """Preview an email template with sample variables (PE Desk only)"""
    if current_user.get("role", 5) != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can preview email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    default_template = EMAIL_TEMPLATES.get(template_key)
    
    if not default_template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    subject = template.get("subject") if template else default_template.get("subject", "")
    body = template.get("body") if template else default_template.get("body", "")
    
    # Render with provided or sample variables
    variables = preview_data.variables or {var: f"[{var}]" for var in default_template.get("variables", [])}
    
    rendered_subject = render_template(subject, variables)
    rendered_body = render_template(body, variables)
    
    return {
        "subject": rendered_subject,
        "body": rendered_body
    }
