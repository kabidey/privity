"""
Routers package initialization
All API routers for modular endpoint management
"""
from .auth import router as auth_router
from .users import router as users_router
from .notifications import router as notifications_router
from .email_templates import router as email_templates_router
from .email_logs import router as email_logs_router
from .smtp_config import router as smtp_config_router
from .stocks import router as stocks_router
from .database_backup import router as database_backup_router
from .bookings import router as bookings_router
from .clients import router as clients_router
from .finance import router as finance_router
from .referral_partners import router as referral_partners_router
from .analytics import router as analytics_router
from .audit_logs import router as audit_logs_router
from .dashboard import router as dashboard_router
from .inventory import router as inventory_router
from .purchases import router as purchases_router
from .reports import router as reports_router
from .company_master import router as company_master_router
from .contract_notes import router as contract_notes_router
from .sohini import router as sohini_router

__all__ = [
    'auth_router',
    'users_router',
    'notifications_router',
    'email_templates_router',
    'email_logs_router',
    'smtp_config_router',
    'stocks_router',
    'database_backup_router',
    'bookings_router',
    'clients_router',
    'finance_router',
    'referral_partners_router',
    'analytics_router',
    'audit_logs_router',
    'dashboard_router',
    'inventory_router',
    'purchases_router',
    'reports_router',
    'company_master_router',
    'contract_notes_router',
    'sohini_router',
]
