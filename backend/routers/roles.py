"""
Role & Permission Management Router
Dynamic role management with granular permissions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from database import db
from routers.auth import get_current_user
from services.permission_service import (
    has_permission,
    require_permission,
    is_pe_desk
)

router = APIRouter(prefix="/roles", tags=["Roles"])


# Define all available permissions in the system
AVAILABLE_PERMISSIONS = {
    "dashboard": {
        "name": "Dashboard",
        "permissions": [
            {"key": "dashboard.view", "name": "View Dashboard", "description": "Access main dashboard"},
            {"key": "dashboard.pe_view", "name": "View PE Dashboard", "description": "Access PE-level dashboard"},
            {"key": "dashboard.my_view", "name": "View My Dashboard", "description": "Access My Dashboard (Employee/Partner view)"},
        ]
    },
    "bookings": {
        "name": "Bookings",
        "permissions": [
            {"key": "bookings.view", "name": "View Bookings", "description": "View booking list"},
            {"key": "bookings.view_all", "name": "View All Bookings", "description": "View all bookings (not just own)"},
            {"key": "bookings.create", "name": "Create Bookings", "description": "Create new bookings"},
            {"key": "bookings.edit", "name": "Edit Bookings", "description": "Edit existing bookings"},
            {"key": "bookings.delete", "name": "Delete Bookings", "description": "Delete bookings"},
            {"key": "bookings.approve", "name": "Approve Bookings", "description": "Approve/reject bookings"},
            {"key": "bookings.record_payment", "name": "Record Payments", "description": "Record payment tranches"},
            {"key": "bookings.delete_payment", "name": "Delete Payments", "description": "Delete payment records"},
            {"key": "bookings.export", "name": "Export Bookings", "description": "Export bookings to Excel"},
            {"key": "bookings.override_revenue_share", "name": "Override Revenue Share", "description": "Set BP revenue share override on bookings"},
            {"key": "bookings.approve_revenue_override", "name": "Approve Revenue Override", "description": "Approve BP revenue share overrides"},
            {"key": "bookings.edit_revenue_override", "name": "Edit Revenue Override", "description": "Edit existing revenue share overrides"},
        ]
    },
    "client_approval": {
        "name": "Client Approval",
        "permissions": [
            {"key": "client_approval.view", "name": "View Pending Approvals", "description": "View clients pending approval"},
            {"key": "client_approval.approve", "name": "Approve Clients", "description": "Approve client applications"},
            {"key": "client_approval.reject", "name": "Reject Clients", "description": "Reject client applications"},
        ]
    },
    "clients": {
        "name": "Clients",
        "permissions": [
            {"key": "clients.view", "name": "View Clients", "description": "View client list"},
            {"key": "clients.create", "name": "Create Clients", "description": "Add new clients"},
            {"key": "clients.edit", "name": "Edit Clients", "description": "Edit client details"},
            {"key": "clients.delete", "name": "Delete Clients", "description": "Delete clients"},
            {"key": "clients.map", "name": "Map Clients", "description": "Map clients to employees"},
            {"key": "clients.upload_docs", "name": "Upload Documents", "description": "Upload client documents"},
            {"key": "clients.view_docs", "name": "View Documents", "description": "View client documents"},
            {"key": "clients.suspend", "name": "Suspend Clients", "description": "Suspend/unsuspend clients"},
            {"key": "clients.skip_cancelled_cheque", "name": "Skip Cancelled Cheque", "description": "Create/approve clients without cancelled cheque document"},
        ]
    },
    "stocks": {
        "name": "Stocks",
        "permissions": [
            {"key": "stocks.view", "name": "View Stocks", "description": "View stock list"},
            {"key": "stocks.create", "name": "Create Stocks", "description": "Add new stocks"},
            {"key": "stocks.edit", "name": "Edit Stocks", "description": "Edit stock details"},
            {"key": "stocks.delete", "name": "Delete Stocks", "description": "Delete stocks"},
            {"key": "stocks.corporate_actions", "name": "Corporate Actions", "description": "Manage splits, bonuses, etc."},
        ]
    },
    "inventory": {
        "name": "Inventory",
        "permissions": [
            {"key": "inventory.view", "name": "View Inventory", "description": "View inventory levels"},
            {"key": "inventory.view_lp_change", "name": "View LP Change Indicator", "description": "View green/red LP price change indicators"},
            {"key": "inventory.view_lp_history", "name": "View LP History", "description": "View landing price change history"},
            {"key": "inventory.edit_landing_price", "name": "Edit Landing Price", "description": "Modify landing prices"},
            {"key": "inventory.recalculate", "name": "Recalculate Inventory", "description": "Trigger inventory recalculation for all stocks"},
            {"key": "inventory.delete", "name": "Delete Inventory", "description": "Delete inventory records"},
        ]
    },
    "purchases": {
        "name": "Purchases",
        "permissions": [
            {"key": "purchases.view", "name": "View Purchases", "description": "View purchase list"},
            {"key": "purchases.create", "name": "Create Purchases", "description": "Record new purchases"},
            {"key": "purchases.edit", "name": "Edit Purchases", "description": "Edit purchase details"},
            {"key": "purchases.delete", "name": "Delete Purchases", "description": "Delete purchases"},
            {"key": "purchases.record_payment", "name": "Record Vendor Payments", "description": "Record payments to vendors"},
        ]
    },
    "vendors": {
        "name": "Vendors",
        "permissions": [
            {"key": "vendors.view", "name": "View Vendors", "description": "View vendor list"},
            {"key": "vendors.create", "name": "Create Vendors", "description": "Add new vendors"},
            {"key": "vendors.edit", "name": "Edit Vendors", "description": "Edit vendor details"},
            {"key": "vendors.delete", "name": "Delete Vendors", "description": "Delete vendors"},
        ]
    },
    "contract_notes": {
        "name": "Contract Notes",
        "permissions": [
            {"key": "contract_notes.view", "name": "View Contract Notes", "description": "View contract notes list"},
            {"key": "contract_notes.generate", "name": "Generate Contract Notes", "description": "Generate new contract notes"},
            {"key": "contract_notes.send", "name": "Send Contract Notes", "description": "Email contract notes to clients"},
            {"key": "contract_notes.download", "name": "Download Contract Notes", "description": "Download contract note PDFs"},
        ]
    },
    "finance": {
        "name": "Finance",
        "permissions": [
            {"key": "finance.view", "name": "View Finance", "description": "Access finance section"},
            {"key": "finance.manage_refunds", "name": "Manage Refunds", "description": "Process refund requests"},
            {"key": "finance.view_reports", "name": "View Reports", "description": "Access financial reports"},
            {"key": "finance.export", "name": "Export Finance Data", "description": "Export finance data to Excel"},
        ]
    },
    "analytics": {
        "name": "Analytics",
        "permissions": [
            {"key": "analytics.view", "name": "View Analytics", "description": "Access analytics dashboard"},
            {"key": "analytics.revenue", "name": "View Revenue Analytics", "description": "View revenue breakdown"},
            {"key": "analytics.performance", "name": "View Performance", "description": "View performance metrics"},
            {"key": "analytics.export", "name": "Export Analytics", "description": "Export analytics data"},
        ]
    },
    "users": {
        "name": "User Management",
        "permissions": [
            {"key": "users.view", "name": "View Users", "description": "View user list"},
            {"key": "users.create", "name": "Create Users", "description": "Add new users"},
            {"key": "users.edit", "name": "Edit Users", "description": "Edit user details"},
            {"key": "users.delete", "name": "Delete Users", "description": "Delete users"},
            {"key": "users.change_role", "name": "Change Roles", "description": "Change user roles"},
            {"key": "users.reset_password", "name": "Reset Passwords", "description": "Reset user passwords"},
            {"key": "users.proxy_login", "name": "Proxy Login", "description": "Login as another user"},
        ]
    },
    "roles": {
        "name": "Role Management",
        "permissions": [
            {"key": "roles.view", "name": "View Roles", "description": "View role list"},
            {"key": "roles.create", "name": "Create Roles", "description": "Create new roles"},
            {"key": "roles.edit", "name": "Edit Roles", "description": "Edit role permissions"},
            {"key": "roles.delete", "name": "Delete Roles", "description": "Delete custom roles"},
        ]
    },
    "business_partners": {
        "name": "Business Partners",
        "permissions": [
            {"key": "business_partners.view", "name": "View Partners", "description": "View business partners"},
            {"key": "business_partners.create", "name": "Create Partners", "description": "Add new partners"},
            {"key": "business_partners.edit", "name": "Edit Partners", "description": "Edit partner details"},
            {"key": "business_partners.delete", "name": "Delete Partners", "description": "Delete partners"},
            {"key": "business_partners.approve", "name": "Approve Partners", "description": "Approve partner applications"},
        ]
    },
    "referral_partners": {
        "name": "Referral Partners",
        "permissions": [
            {"key": "referral_partners.view", "name": "View RPs", "description": "View referral partners"},
            {"key": "referral_partners.create", "name": "Create RPs", "description": "Add referral partners"},
            {"key": "referral_partners.edit", "name": "Edit RPs", "description": "Edit referral partner details"},
            {"key": "referral_partners.approve", "name": "Approve RPs", "description": "Approve/reject referral partners"},
            {"key": "referral_partners.view_payouts", "name": "View Payouts", "description": "View RP payout details"},
        ]
    },
    "reports": {
        "name": "Reports",
        "permissions": [
            {"key": "reports.view", "name": "View Reports", "description": "Access reports section"},
            {"key": "reports.pnl", "name": "View P&L Reports", "description": "View profit and loss reports"},
            {"key": "reports.export", "name": "Export Reports", "description": "Export report data"},
            {"key": "reports.bi_bookings", "name": "BI: Bookings Report", "description": "Generate booking reports in BI builder"},
            {"key": "reports.bi_clients", "name": "BI: Clients Report", "description": "Generate client reports in BI builder"},
            {"key": "reports.bi_revenue", "name": "BI: Revenue Report", "description": "Generate revenue reports in BI builder"},
            {"key": "reports.bi_inventory", "name": "BI: Inventory Report", "description": "Generate inventory reports in BI builder"},
            {"key": "reports.bi_payments", "name": "BI: Payments Report", "description": "Generate payment reports in BI builder"},
            {"key": "reports.bi_pnl", "name": "BI: P&L Analysis", "description": "Generate P&L analysis reports in BI builder"},
            {"key": "reports.bi_export", "name": "BI: Export to Excel", "description": "Export BI reports to Excel"},
            {"key": "reports.bi_save_templates", "name": "BI: Save Templates", "description": "Save and manage BI report templates"},
        ]
    },
    "notifications": {
        "name": "Notifications",
        "permissions": [
            {"key": "notifications.whatsapp_view", "name": "WhatsApp: View Settings", "description": "View WhatsApp configuration and templates"},
            {"key": "notifications.whatsapp_connect", "name": "WhatsApp: Connect/Disconnect", "description": "Manage WhatsApp connection via QR code"},
            {"key": "notifications.whatsapp_templates", "name": "WhatsApp: Manage Templates", "description": "Create, edit, and delete message templates"},
            {"key": "notifications.whatsapp_send", "name": "WhatsApp: Send Messages", "description": "Send individual WhatsApp messages"},
            {"key": "notifications.whatsapp_bulk", "name": "WhatsApp: Bulk Send", "description": "Send bulk WhatsApp messages"},
            {"key": "notifications.whatsapp_history", "name": "WhatsApp: View History", "description": "View message sending history"},
        ]
    },
    "dp_operations": {
        "name": "DP Operations",
        "permissions": [
            {"key": "dp.view_receivables", "name": "View DP Receivables", "description": "View DP receivables"},
            {"key": "dp.confirm_receipt", "name": "Confirm Receipt", "description": "Confirm stock receipt from vendor"},
            {"key": "dp.transfer", "name": "Transfer Stocks", "description": "Transfer stocks to clients"},
            {"key": "dp.view_transfers", "name": "View Transfers", "description": "View transfer history"},
        ]
    },
    "email_management": {
        "name": "Email Management",
        "permissions": [
            {"key": "email.view_templates", "name": "View Templates", "description": "View email templates"},
            {"key": "email.edit_templates", "name": "Edit Templates", "description": "Edit email templates"},
            {"key": "email.view_logs", "name": "View Email Logs", "description": "View sent email logs"},
            {"key": "email.server_config", "name": "Server Configuration", "description": "Configure email server settings"},
        ]
    },
    "company_master": {
        "name": "Company Master",
        "permissions": [
            {"key": "company.view", "name": "View Company Info", "description": "View company master data"},
            {"key": "company.edit", "name": "Edit Company Info", "description": "Edit company details"},
            {"key": "company.upload_docs", "name": "Upload Documents", "description": "Upload company documents"},
            {"key": "company.manage_bank", "name": "Manage Bank Details", "description": "Manage company bank accounts"},
        ]
    },
    "security": {
        "name": "Security",
        "permissions": [
            {"key": "security.view_dashboard", "name": "View Security Dashboard", "description": "View security events and alerts"},
            {"key": "security.view_audit", "name": "View Audit Trail", "description": "View audit logs"},
            {"key": "security.view_threats", "name": "View Threats", "description": "View security threat logs and blocked IPs"},
            {"key": "security.manage_threats", "name": "Manage Threats", "description": "Clear/manage threat records"},
            {"key": "security.manage_2fa", "name": "Manage 2FA", "description": "Manage two-factor authentication"},
            {"key": "security.kill_switch", "name": "Kill Switch", "description": "Emergency system freeze"},
        ]
    },
    "files": {
        "name": "File Management",
        "permissions": [
            {"key": "files.view", "name": "View Files", "description": "View and download uploaded files"},
            {"key": "files.view_stats", "name": "View File Stats", "description": "View storage statistics"},
            {"key": "files.upload", "name": "Upload Files", "description": "Upload new files to the system"},
            {"key": "files.delete", "name": "Delete Files", "description": "Delete uploaded files"},
            {"key": "files.scan", "name": "Scan Files", "description": "Scan for missing files and re-upload"},
        ]
    },
    "database": {
        "name": "Database Management",
        "permissions": [
            {"key": "database.view_backups", "name": "View Backups", "description": "View backup list"},
            {"key": "database.create_backup", "name": "Create Backup", "description": "Create new backup"},
            {"key": "database.restore", "name": "Restore Backup", "description": "Restore from backup"},
            {"key": "database.download", "name": "Download Backup", "description": "Download backup files"},
        ]
    },
    "bulk_upload": {
        "name": "Bulk Upload",
        "permissions": [
            {"key": "bulk_upload.clients", "name": "Upload Clients", "description": "Bulk upload clients"},
            {"key": "bulk_upload.stocks", "name": "Upload Stocks", "description": "Bulk upload stocks"},
            {"key": "bulk_upload.purchases", "name": "Upload Purchases", "description": "Bulk upload purchases"},
            {"key": "bulk_upload.bookings", "name": "Upload Bookings", "description": "Bulk upload bookings"},
        ]
    },
    "research": {
        "name": "Research",
        "permissions": [
            {"key": "research.view", "name": "View Research", "description": "View research reports"},
            {"key": "research.upload", "name": "Upload Research", "description": "Upload research reports"},
            {"key": "research.ai_analysis", "name": "AI Analysis", "description": "Use AI stock analysis"},
        ]
    },
    "license": {
        "name": "License Management",
        "permissions": [
            {"key": "license.view", "name": "View Licenses", "description": "View license status and list"},
            {"key": "license.generate", "name": "Generate License Keys", "description": "Generate new license keys"},
            {"key": "license.activate", "name": "Activate Licenses", "description": "Activate license keys"},
            {"key": "license.revoke", "name": "Revoke Licenses", "description": "Revoke active licenses"},
        ]
    },
}

# Default system roles with their permissions
DEFAULT_ROLES = [
    {
        "id": 1,
        "name": "PE Desk",
        "description": "Full system access with administrative privileges",
        "is_system": True,
        "permissions": ["*"],  # All permissions
        "color": "bg-purple-100 text-purple-800"
    },
    {
        "id": 2,
        "name": "PE Manager",
        "description": "Management level access with approval rights",
        "is_system": True,
        "permissions": [
            "dashboard.*", "bookings.*", "clients.*", "stocks.*", 
            "inventory.*", "purchases.*", "vendors.*", "finance.view",
            "finance.view_reports", "users.view", "business_partners.*",
            "referral_partners.*", "reports.*", "dp.*"
        ],
        "color": "bg-indigo-100 text-indigo-800"
    },
    {
        "id": 3,
        "name": "Finance",
        "description": "Finance and payment management",
        "is_system": True,
        "permissions": [
            "dashboard.view", "bookings.view", "bookings.view_all",
            "bookings.record_payment", "finance.*", "reports.view",
            "reports.view_reports", "purchases.view", "purchases.record_payment"
        ],
        "color": "bg-emerald-100 text-emerald-800"
    },
    {
        "id": 4,
        "name": "Viewer",
        "description": "Read-only access to all sections",
        "is_system": True,
        "permissions": [
            "dashboard.view", "bookings.view", "bookings.view_all",
            "clients.view", "stocks.view", "inventory.view",
            "purchases.view", "vendors.view", "finance.view",
            "users.view", "business_partners.view", "referral_partners.view",
            "reports.view"
        ],
        "color": "bg-gray-100 text-gray-800"
    },
    {
        "id": 5,
        "name": "Partners Desk",
        "description": "Business partner management",
        "is_system": True,
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "bookings.override_revenue_share",
            "clients.view", "clients.create", "business_partners.*",
            "referral_partners.view"
        ],
        "color": "bg-pink-100 text-pink-800"
    },
    {
        "id": 6,
        "name": "Business Partner",
        "description": "External partner with limited access",
        "is_system": True,
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "bookings.override_revenue_share",
            "clients.view", "clients.create"
        ],
        "color": "bg-orange-100 text-orange-800"
    },
    {
        "id": 7,
        "name": "Employee",
        "description": "Standard employee access",
        "is_system": True,
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "clients.view", "clients.create", "clients.edit",
            "stocks.view", "inventory.view"
        ],
        "color": "bg-blue-100 text-blue-800"
    }
]


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    permissions: List[str] = []
    color: Optional[str] = "bg-gray-100 text-gray-800"


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    color: Optional[str] = None


@router.get("/permissions")
async def get_all_permissions(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.view", "view permissions"))
):
    """Get all available permissions grouped by category"""
    return AVAILABLE_PERMISSIONS


@router.get("")
async def get_roles(
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.view", "view roles"))
):
    """Get all roles (system + custom)"""
    # Get custom roles from database
    custom_roles = await db.roles.find({}, {"_id": 0}).to_list(1000)
    
    # Combine with default system roles
    all_roles = []
    
    # Add system roles
    for role in DEFAULT_ROLES:
        # Check if there's a customized version in DB
        db_role = next((r for r in custom_roles if r.get("id") == role["id"]), None)
        if db_role:
            # Use DB version but mark as system
            db_role["is_system"] = True
            all_roles.append(db_role)
        else:
            all_roles.append(role)
    
    # Add custom roles (id > 7)
    for role in custom_roles:
        if role.get("id", 0) > 7:
            role["is_system"] = False
            all_roles.append(role)
    
    return sorted(all_roles, key=lambda x: x.get("id", 999))


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific role by ID - users can always view their own role"""
    user_role_id = current_user.get("role", 7)
    
    # Allow users to view their own role without permission
    # For other roles, require roles.view permission
    if role_id != user_role_id:
        has_perm = await has_permission(current_user, "roles.view")
        if not has_perm:
            raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check database first
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    
    if role:
        return role
    
    # Fall back to default roles
    default_role = next((r for r in DEFAULT_ROLES if r["id"] == role_id), None)
    if default_role:
        return default_role
    
    raise HTTPException(status_code=404, detail="Role not found")


@router.post("")
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.create", "create roles"))
):
    """Create a new custom role (PE Desk only)"""
    # Check if name already exists
    existing = await db.roles.find_one({"name": role_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Role with this name already exists")
    
    # Also check default roles
    if any(r["name"].lower() == role_data.name.lower() for r in DEFAULT_ROLES):
        raise HTTPException(status_code=400, detail="Cannot use system role name")
    
    # Get next ID (start from 8 for custom roles)
    last_role = await db.roles.find_one(sort=[("id", -1)])
    next_id = max((last_role.get("id", 7) if last_role else 7) + 1, 8)
    
    new_role = {
        "id": next_id,
        "name": role_data.name,
        "description": role_data.description,
        "permissions": role_data.permissions,
        "color": role_data.color,
        "is_system": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.roles.insert_one(new_role)
    
    # Remove _id before returning
    new_role.pop("_id", None)
    
    return new_role


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.edit", "edit roles"))
):
    """Update a role's permissions (PE Desk only)"""
    # Check if role exists
    existing = await db.roles.find_one({"id": role_id})
    is_system_role = role_id <= 7
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if role_data.name is not None:
        if is_system_role:
            raise HTTPException(status_code=400, detail="Cannot rename system roles")
        update_data["name"] = role_data.name
    
    if role_data.description is not None:
        update_data["description"] = role_data.description
    
    if role_data.permissions is not None:
        update_data["permissions"] = role_data.permissions
    
    if role_data.color is not None:
        update_data["color"] = role_data.color
    
    if existing:
        # Update existing record
        await db.roles.update_one({"id": role_id}, {"$set": update_data})
        updated = await db.roles.find_one({"id": role_id}, {"_id": 0})
    else:
        # Create new record for system role customization
        if is_system_role:
            default_role = next((r for r in DEFAULT_ROLES if r["id"] == role_id), None)
            if not default_role:
                raise HTTPException(status_code=404, detail="Role not found")
            
            new_record = {**default_role, **update_data}
            await db.roles.insert_one(new_record)
            updated = await db.roles.find_one({"id": role_id}, {"_id": 0})
        else:
            raise HTTPException(status_code=404, detail="Role not found")
    
    return updated


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.delete", "delete roles"))
):
    """Delete a custom role (PE Desk only, cannot delete system roles)"""
    if role_id <= 7:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    
    # Check if any users have this role
    users_with_role = await db.users.count_documents({"role": role_id})
    if users_with_role > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role: {users_with_role} user(s) are assigned to this role"
        )
    
    result = await db.roles.delete_one({"id": role_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {"message": "Role deleted successfully"}


@router.post("/check-permission")
async def check_permission(
    permission: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if current user has a specific permission"""
    user_role_id = current_user.get("role", 7)
    
    # Get role permissions
    role = await db.roles.find_one({"id": user_role_id}, {"_id": 0})
    if not role:
        role = next((r for r in DEFAULT_ROLES if r["id"] == user_role_id), None)
    
    if not role:
        return {"has_permission": False}
    
    permissions = role.get("permissions", [])
    
    # Check for wildcard permissions
    if "*" in permissions:
        return {"has_permission": True}
    
    # Check for category wildcard (e.g., "bookings.*")
    category = permission.split(".")[0]
    if f"{category}.*" in permissions:
        return {"has_permission": True}
    
    # Check exact permission
    return {"has_permission": permission in permissions}


@router.get("/user/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("roles.view", "view user permissions"))
):
    """Get all permissions for a specific user"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "role": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_id = user.get("role", 7)
    
    # Get role
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        role = next((r for r in DEFAULT_ROLES if r["id"] == role_id), None)
    
    if not role:
        return {"permissions": [], "role_name": "Unknown"}
    
    # Expand permissions
    raw_permissions = role.get("permissions", [])
    expanded_permissions = set()
    
    if "*" in raw_permissions:
        # All permissions
        for category in AVAILABLE_PERMISSIONS.values():
            for perm in category["permissions"]:
                expanded_permissions.add(perm["key"])
    else:
        for perm in raw_permissions:
            if perm.endswith(".*"):
                # Category wildcard
                category_key = perm[:-2]
                if category_key in AVAILABLE_PERMISSIONS:
                    for p in AVAILABLE_PERMISSIONS[category_key]["permissions"]:
                        expanded_permissions.add(p["key"])
            else:
                expanded_permissions.add(perm)
    
    return {
        "permissions": list(expanded_permissions),
        "role_id": role_id,
        "role_name": role.get("name", "Unknown")
    }
