"""
Routers package initialization
"""
from .auth import router as auth_router
from .users import router as users_router
from .notifications import router as notifications_router

__all__ = [
    'auth_router',
    'users_router',
    'notifications_router',
]
