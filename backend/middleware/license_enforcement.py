"""
License Enforcement Middleware
Backend enforcement for granular feature licensing
"""
from fastapi import HTTPException, Depends
from functools import wraps
from typing import Optional, Callable
import logging

from utils.auth import get_current_user
from services.license_service_v2 import (
    check_feature_license,
    check_module_license,
    check_usage_limit,
    is_license_admin,
    LICENSE_ADMIN_ROLE
)
from database import db

logger = logging.getLogger(__name__)


def is_smifs_employee(email: str) -> bool:
    """Check if user is a SMIFS employee (exempt from license checks)"""
    return email and email.lower().endswith('@smifs.com')


async def require_feature_license(
    feature: str,
    company_type: Optional[str] = None
) -> Callable:
    """
    Dependency factory to check if a feature is licensed.
    
    Usage:
        @router.get("/bookings")
        async def get_bookings(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(require_feature_license("bookings", "private_equity"))
        ):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        # License admin has full access
        if await is_license_admin(current_user):
            return True
        
        # SMIFS employees are exempt
        if is_smifs_employee(current_user.get("email", "")):
            return True
        
        # Check feature license
        result = await check_feature_license(feature, company_type)
        
        if not result["is_licensed"]:
            logger.warning(f"License denied for feature '{feature}' - User: {current_user.get('email')}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_not_licensed",
                    "feature": feature,
                    "message": result["message"],
                    "contact_admin": result.get("contact_admin", True)
                }
            )
        
        return True
    
    return dependency


async def require_module_license(module: str) -> Callable:
    """
    Dependency factory to check if a module is licensed.
    
    Usage:
        @router.get("/fi-instruments")
        async def get_instruments(
            current_user: dict = Depends(get_current_user),
            _: None = Depends(require_module_license("fixed_income"))
        ):
            ...
    """
    async def dependency(current_user: dict = Depends(get_current_user)):
        # License admin has full access
        if await is_license_admin(current_user):
            return True
        
        # SMIFS employees are exempt
        if is_smifs_employee(current_user.get("email", "")):
            return True
        
        # Check module license
        result = await check_module_license(module)
        
        if not result["is_licensed"]:
            module_name = "Private Equity" if module == "private_equity" else "Fixed Income"
            logger.warning(f"License denied for module '{module}' - User: {current_user.get('email')}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "module_not_licensed",
                    "module": module,
                    "message": result["message"],
                    "contact_admin": result.get("contact_admin", True)
                }
            )
        
        return True
    
    return dependency


class LicenseEnforcer:
    """
    Class-based license enforcer for more complex scenarios.
    
    Usage:
        enforcer = LicenseEnforcer()
        
        @router.post("/bookings")
        async def create_booking(
            data: BookingCreate,
            current_user: dict = Depends(get_current_user)
        ):
            await enforcer.require_feature("bookings", "private_equity", current_user)
            await enforcer.check_usage("max_bookings_per_month", "private_equity", current_user)
            ...
    """
    
    async def is_exempt(self, user: dict) -> bool:
        """Check if user is exempt from license checks"""
        if await is_license_admin(user):
            return True
        if is_smifs_employee(user.get("email", "")):
            return True
        return False
    
    async def require_feature(
        self, 
        feature: str, 
        company_type: Optional[str] = None,
        user: dict = None
    ) -> bool:
        """
        Check if feature is licensed, raise HTTPException if not.
        """
        if user and await self.is_exempt(user):
            return True
        
        result = await check_feature_license(feature, company_type)
        
        if not result["is_licensed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "feature_not_licensed",
                    "feature": feature,
                    "message": result["message"],
                    "contact_admin": True
                }
            )
        
        return True
    
    async def require_module(self, module: str, user: dict = None) -> bool:
        """
        Check if module is licensed, raise HTTPException if not.
        """
        if user and await self.is_exempt(user):
            return True
        
        result = await check_module_license(module)
        
        if not result["is_licensed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "module_not_licensed",
                    "module": module,
                    "message": result["message"],
                    "contact_admin": True
                }
            )
        
        return True
    
    async def check_usage(
        self,
        limit_type: str,
        company_type: str,
        user: dict = None,
        current_count: int = None
    ) -> dict:
        """
        Check usage limit and return status.
        If current_count is None, it will be calculated automatically.
        """
        if user and await self.is_exempt(user):
            return {"allowed": True, "limit": -1, "remaining": -1, "message": "Unlimited"}
        
        # Auto-calculate current count if not provided
        if current_count is None:
            current_count = await self._get_current_count(limit_type, company_type)
        
        result = await check_usage_limit(limit_type, company_type, current_count)
        
        if not result["allowed"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "usage_limit_exceeded",
                    "limit_type": limit_type,
                    "limit": result["limit"],
                    "current": result["current"],
                    "message": result["message"],
                    "contact_admin": True
                }
            )
        
        return result
    
    async def _get_current_count(self, limit_type: str, company_type: str) -> int:
        """Calculate current count for a usage limit"""
        from datetime import datetime, timezone
        
        if limit_type == "max_users":
            return await db.users.count_documents({"is_active": True, "is_hidden": {"$ne": True}})
        
        elif limit_type == "max_clients":
            query = {"status": {"$ne": "deleted"}}
            if company_type == "private_equity":
                query["modules"] = "private_equity"
            elif company_type == "fixed_income":
                query["modules"] = "fixed_income"
            return await db.clients.count_documents(query)
        
        elif limit_type == "max_bookings_per_month":
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return await db.bookings.count_documents({"created_at": {"$gte": month_start.isoformat()}})
        
        elif limit_type == "max_fi_orders_per_month":
            month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return await db.fi_orders.count_documents({"created_at": {"$gte": month_start.isoformat()}})
        
        return 0
    
    def check_feature_sync(self, feature: str, company_type: Optional[str] = None) -> dict:
        """
        Synchronous version for use in non-async contexts.
        Returns check result without raising exception.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(check_feature_license(feature, company_type))
        except:
            return {"is_licensed": True, "message": "Check failed, allowing access"}


# Global enforcer instance
license_enforcer = LicenseEnforcer()


# Convenience functions for common checks
async def enforce_pe_license(current_user: dict = Depends(get_current_user)):
    """Dependency to enforce Private Equity module license"""
    return await (await require_module_license("private_equity"))(current_user)


async def enforce_fi_license(current_user: dict = Depends(get_current_user)):
    """Dependency to enforce Fixed Income module license"""
    return await (await require_module_license("fixed_income"))(current_user)


async def enforce_bookings_license(current_user: dict = Depends(get_current_user)):
    """Dependency to enforce bookings feature license"""
    return await (await require_feature_license("bookings", "private_equity"))(current_user)


async def enforce_fi_orders_license(current_user: dict = Depends(get_current_user)):
    """Dependency to enforce FI orders feature license"""
    return await (await require_feature_license("fi_orders", "fixed_income"))(current_user)
