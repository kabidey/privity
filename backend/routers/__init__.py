"""
Routers package initialization
"""
from .auth import router as auth_router
from .users import router as users_router
from .notifications import router as notifications_router
from .email_templates import router as email_templates_router
from .smtp_config import router as smtp_config_router
from .stocks import router as stocks_router

__all__ = [
    'auth_router',
    'users_router',
    'notifications_router',
    'email_templates_router',
    'smtp_config_router',
    'stocks_router',
]
