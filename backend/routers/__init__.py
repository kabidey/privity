"""
Routers package initialization
"""
from .auth import router as auth_router
from .users import router as users_router
from .notifications import router as notifications_router
from .clients import router as clients_router
from .stocks import router as stocks_router, corporate_router
from .purchases import router as purchases_router
from .bookings import router as bookings_router
from .reports import router as reports_router
from .email_templates import router as email_templates_router
from .utils import router as utils_router

__all__ = [
    'auth_router',
    'users_router',
    'notifications_router',
    'clients_router',
    'stocks_router',
    'corporate_router',
    'purchases_router',
    'bookings_router',
    'reports_router',
    'email_templates_router',
    'utils_router',
]
