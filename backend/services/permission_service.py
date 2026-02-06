"""
Permission Service
Dynamic permission checking against the roles collection.

This service provides functions to check if a user has a specific permission
based on their assigned role and the permissions defined in the roles collection.
"""

from typing import List, Optional, Set
from database import db
import logging

logger = logging.getLogger(__name__)

# Default system roles with their permissions (fallback if not in DB)
DEFAULT_ROLES = {
    1: {  # PE Desk
        "name": "PE Desk",
        "permissions": ["*"]  # All permissions
    },
    2: {  # PE Manager
        "name": "PE Manager",
        "permissions": [
            "dashboard.*", "bookings.*", "clients.*", "clients.rerun_ocr", "stocks.*", 
            "inventory.*", "purchases.*", "vendors.*", "finance.view",
            "finance.view_reports", "users.view", "business_partners.*",
            "referral_partners.*", "reports.*", "dp.*", "revenue.*",
            "research.*", "contract_notes.*"
        ]
    },
    3: {  # Finance
        "name": "Finance",
        "permissions": [
            "dashboard.view", "bookings.view", "bookings.view_all",
            "bookings.record_payment", "finance.*", "reports.view",
            "reports.view_reports", "purchases.view", "purchases.record_payment",
            "revenue.rp_view", "revenue.employee_view"
        ]
    },
    4: {  # Viewer
        "name": "Viewer",
        "permissions": [
            "dashboard.view", "bookings.view", "bookings.view_all",
            "clients.view", "stocks.view", "inventory.view",
            "purchases.view", "vendors.view", "finance.view",
            "users.view", "business_partners.view", "referral_partners.view",
            "reports.view", "research.view", "revenue.rp_view", "revenue.employee_view"
        ]
    },
    5: {  # Partners Desk
        "name": "Partners Desk",
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "clients.view", "clients.create", "business_partners.*",
            "referral_partners.view", "revenue.rp_view"
        ]
    },
    6: {  # Business Partner
        "name": "Business Partner",
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "clients.view", "clients.create"
        ]
    },
    7: {  # Employee
        "name": "Employee",
        "permissions": [
            "dashboard.view", "dashboard.my_view", "bookings.view", "bookings.create",
            "clients.view", "clients.create", "clients.edit",
            "stocks.view", "inventory.view", "revenue.rp_view",
            "revenue.employee_view", "revenue.team_view", "research.view"
        ]
    }
}


async def get_role_permissions(role_id: int) -> List[str]:
    """
    Get permissions for a role from database or fallback to defaults.
    
    Args:
        role_id: The role ID to get permissions for
        
    Returns:
        List of permission strings
    """
    # Try to get from database first
    role = await db.roles.find_one({"id": role_id}, {"_id": 0, "permissions": 1})
    
    if role and "permissions" in role:
        return role["permissions"]
    
    # Fallback to default permissions
    if role_id in DEFAULT_ROLES:
        return DEFAULT_ROLES[role_id]["permissions"]
    
    # Unknown role - return empty permissions
    logger.warning(f"Unknown role ID: {role_id}")
    return []


def expand_permissions(raw_permissions: List[str]) -> Set[str]:
    """
    Expand wildcard permissions to all specific permissions.
    
    Args:
        raw_permissions: List of permission strings (may include wildcards)
        
    Returns:
        Set of expanded permission strings
    """
    # All available permissions in the system
    ALL_PERMISSIONS = {
        "dashboard": ["view", "pe_view", "my_view"],
        "bookings": ["view", "view_all", "create", "edit", "delete", "approve", 
                     "record_payment", "delete_payment", "export",
                     "override_revenue_share", "approve_revenue_override", "edit_revenue_override"],
        "clients": ["view", "create", "edit", "delete", "map", "upload_docs", "view_docs", "suspend", "skip_cancelled_cheque", "rerun_ocr"],
        "stocks": ["view", "create", "edit", "delete", "corporate_actions"],
        "inventory": ["view", "view_lp_change", "view_lp_history", "edit_landing_price", "recalculate", "delete"],
        "purchases": ["view", "create", "edit", "delete", "record_payment"],
        "vendors": ["view", "create", "edit", "delete"],
        "finance": ["view", "manage_refunds", "view_reports", "export"],
        "users": ["view", "create", "edit", "delete", "change_role", "reset_password", "proxy_login"],
        "roles": ["view", "create", "edit", "delete"],
        "business_partners": ["view", "create", "edit", "delete", "approve"],
        "referral_partners": ["view", "create", "edit", "approve", "view_payouts"],
        "reports": ["view", "pnl", "export", "pe_hit", 
                   "bi_bookings", "bi_clients", "bi_revenue", "bi_inventory", "bi_payments", "bi_pnl", 
                   "bi_export", "bi_save_templates"],
        "analytics": ["view", "revenue", "performance", "export"],
        "dp": ["view_receivables", "confirm_receipt", "transfer", "view_transfers"],
        "email": ["view_templates", "edit_templates", "view_logs", "server_config"],
        "company": ["view", "edit", "upload_docs", "manage_bank"],
        "security": ["view_dashboard", "view_audit", "manage_2fa", "kill_switch"],
        "database": ["view_backups", "create_backup", "restore", "download"],
        "bulk_upload": ["clients", "stocks", "purchases", "bookings"],
        "research": ["view", "upload", "delete", "ai"],
        "contract_notes": ["view", "generate", "send", "download"],
        "client_approval": ["view", "approve", "reject"],
        "revenue": ["rp_view", "employee_view", "team_view"],
        "system": ["kill_switch"],
        "license": ["view", "generate", "activate", "revoke"],
        "notifications": ["whatsapp_view", "whatsapp_connect", "whatsapp_templates", 
                         "whatsapp_send", "whatsapp_bulk", "whatsapp_history", "whatsapp_config"],
        "chat": ["view", "send"],
        "files": ["view", "upload", "delete"]
    }
    
    expanded = set()
    
    for perm in raw_permissions:
        if perm == "*":
            # All permissions
            for category, perms in ALL_PERMISSIONS.items():
                for p in perms:
                    expanded.add(f"{category}.{p}")
            return expanded
        elif perm.endswith(".*"):
            # Category wildcard (e.g., "bookings.*")
            category = perm[:-2]
            if category in ALL_PERMISSIONS:
                for p in ALL_PERMISSIONS[category]:
                    expanded.add(f"{category}.{p}")
        else:
            expanded.add(perm)
    
    return expanded


async def has_permission(user: dict, permission: str) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: User dict containing at least 'role' key
        permission: Permission string to check (e.g., "bookings.approve")
        
    Returns:
        True if user has the permission, False otherwise
    """
    role_id = user.get("role", 7)  # Default to Employee
    
    # PE Desk (role 1) always has all permissions
    if role_id == 1:
        return True
    
    # Get role-level permissions
    raw_permissions = await get_role_permissions(role_id)
    
    # Check for wildcard all
    if "*" in raw_permissions:
        return True
    
    # Check for category wildcard
    category = permission.split(".")[0]
    if f"{category}.*" in raw_permissions:
        return True
    
    # Check for exact permission
    return permission in raw_permissions


async def check_permission(user: dict, permission: str, action_name: str = "perform this action"):
    """
    Check if user has permission and raise HTTPException if not.
    
    Args:
        user: User dict containing at least 'role' key
        permission: Permission string to check
        action_name: Human-readable action name for error message
        
    Raises:
        HTTPException with 403 status if permission denied
    """
    from fastapi import HTTPException
    
    if not await has_permission(user, permission):
        role_name = await get_role_name(user.get("role", 7))
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied. {role_name} role does not have permission to {action_name}."
        )


async def get_role_name(role_id: int) -> str:
    """Get the name of a role by ID."""
    role = await db.roles.find_one({"id": role_id}, {"_id": 0, "name": 1})
    if role:
        return role.get("name", "Unknown")
    return DEFAULT_ROLES.get(role_id, {}).get("name", "Unknown")


async def get_user_all_permissions(user: dict) -> Set[str]:
    """
    Get all expanded permissions for a user.
    
    Args:
        user: User dict containing at least 'role' key
        
    Returns:
        Set of all permission strings the user has
    """
    role_id = user.get("role", 7)
    raw_permissions = await get_role_permissions(role_id)
    return expand_permissions(raw_permissions)


# Backward compatibility functions that check dynamic permissions
# These can be used to gradually migrate existing code

async def is_pe_level_dynamic(user: dict) -> bool:
    """Check if user has PE-level access based on permissions."""
    # Check for admin-level permissions
    perms = await get_user_all_permissions(user)
    pe_indicators = {"users.change_role", "bookings.approve", "settings.company_master"}
    return bool(perms & pe_indicators) or user.get("role") in [1, 2]


async def can_approve_bookings(user: dict) -> bool:
    """Check if user can approve bookings."""
    return await has_permission(user, "bookings.approve")


async def can_record_payments(user: dict) -> bool:
    """Check if user can record payments."""
    return await has_permission(user, "bookings.record_payment")


async def can_delete_payments(user: dict) -> bool:
    """Check if user can delete payments."""
    return await has_permission(user, "bookings.delete_payment")


async def can_manage_users(user: dict) -> bool:
    """Check if user can manage users."""
    return await has_permission(user, "users.edit")


async def can_edit_landing_price(user: dict) -> bool:
    """Check if user can edit landing prices."""
    return await has_permission(user, "inventory.edit_landing_price")


async def can_recalculate_inventory(user: dict) -> bool:
    """Check if user can recalculate inventory."""
    return await has_permission(user, "inventory.recalculate")


# FastAPI Dependency Factory
def require_permission(permission: str, action_name: str = None):
    """
    Create a FastAPI dependency that checks for a specific permission.
    
    Usage:
        @router.post("/endpoint")
        async def my_endpoint(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(require_permission("bookings.approve", "approve bookings"))
        ):
            # User has permission if we get here
            pass
    
    Args:
        permission: Permission string to check (e.g., "bookings.approve")
        action_name: Human-readable action name for error message
        
    Returns:
        FastAPI dependency function
    """
    from fastapi import Depends
    from utils.auth import get_current_user
    
    if action_name is None:
        action_name = permission.replace(".", " ").replace("_", " ")
    
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        await check_permission(current_user, permission, action_name)
        return None
    
    return permission_checker


# Convenience functions for common permission checks
async def require_pe_desk(user: dict, action_name: str = "perform this action"):
    """Require PE Desk level (full admin) for an action."""
    await check_permission(user, "settings.company_master", action_name)


async def require_pe_level(user: dict, action_name: str = "perform this action"):
    """Require PE Level (PE Desk or PE Manager) for an action."""
    # Check if user has any PE-level permission indicator
    if not await is_pe_level_dynamic(user):
        from fastapi import HTTPException
        role_name = await get_role_name(user.get("role", 7))
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied. {role_name} role does not have PE-level access to {action_name}."
        )

