"""
Application configuration and constants
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# File upload directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Email Configuration (MS Exchange)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.office365.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USERNAME)

# Emergent LLM Key for OCR
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# OTP Configuration
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3

# Frontend URL for email links
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://booking-portal-38.preview.emergentagent.com')

# User Roles
ROLES = {
    1: "PE Desk",
    2: "PE Manager",
    3: "Zonal Manager",
    4: "Manager",
    5: "Employee",
    6: "Viewer",
    7: "Finance",
    8: "Business Partner",
    9: "Partners Desk",
    10: "Regional Manager",
    11: "Business Head"
}

# Role Permissions
ROLE_PERMISSIONS = {
    1: ["all"],  # PE Desk - full access including all deletions, database management
    2: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", 
        "view_reports", "approve_clients", "approve_bookings", "manage_vendors", "manage_email_templates",
        "view_analytics", "manage_inventory", "view_dp_transfer", "manage_corporate_actions",
        "view_audit_logs", "manage_payments", "view_database_stats", "view_finance"],  # PE Manager - PE Desk without delete/restore
    3: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    4: ["view_all", "manage_clients", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    5: ["view_own", "create_bookings", "view_clients", "create_clients"],
    6: ["view_all"],  # Viewer - View all modules but no create/edit/delete/download
    7: ["view_own", "create_bookings", "view_clients", "create_clients", "view_finance", "manage_finance"],  # Finance - Employee + full Finance access
    8: ["view_own", "create_bookings", "view_clients", "create_clients", "view_bp_dashboard", "view_bp_reports"],  # Business Partner - can create bookings and clients, view own dashboard
    9: ["view_own", "create_bookings", "view_clients", "create_clients", "manage_business_partners", "view_bp_revenue", "add_business_partners"],  # Partners Desk - Employee + BP management (no delete)
    10: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],  # Regional Manager - Above Zonal Manager
    11: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients", "approve_bookings"]  # Business Head - Above Regional Manager
}


def is_pe_level(role: int) -> bool:
    """Check if user has PE-level access (PE Desk or PE Manager)"""
    return role in [1, 2]


def is_pe_desk_only(role: int) -> bool:
    """Check if user is PE Desk (full access including deletions)"""
    return role == 1


def has_finance_access(role: int) -> bool:
    """Check if user has access to Finance page (PE Level or Finance role)"""
    return role in [1, 2, 7]


def can_manage_finance(role: int) -> bool:
    """Check if user can manage finance operations (update refunds etc.)"""
    return role in [1, 2, 7]


def can_manage_business_partners(role: int) -> bool:
    """Check if user can manage Business Partners (PE Level or Partners Desk)"""
    return role in [1, 2, 9]


def is_partners_desk(role: int) -> bool:
    """Check if user is Partners Desk"""
    return role == 9


# Allowed email domains for registration
ALLOWED_EMAIL_DOMAINS = ["smifs.com"]

# Audit Log Types
AUDIT_ACTIONS = {
    "USER_REGISTER": "User Registration",
    "USER_LOGIN": "User Login",
    "USER_PASSWORD_RESET": "Password Reset",
    "CLIENT_CREATE": "Client Created",
    "CLIENT_UPDATE": "Client Updated",
    "CLIENT_DELETE": "Client Deleted",
    "CLIENT_APPROVE": "Client Approved",
    "CLIENT_REJECT": "Client Rejected",
    "CLIENT_MAP": "Client Mapped to Employee",
    "VENDOR_CREATE": "Vendor Created",
    "STOCK_CREATE": "Stock Created",
    "PURCHASE_CREATE": "Purchase Created",
    "BOOKING_CREATE": "Booking Created",
    "BOOKING_APPROVE": "Booking Approved",
    "BOOKING_REJECT": "Booking Rejected",
    "BOOKING_UPDATE": "Booking Updated",
    "PAYMENT_RECORDED": "Payment Recorded",
    "INVENTORY_ADJUST": "Inventory Adjusted",
    "EMAIL_TEMPLATE_UPDATE": "Email Template Updated",
}

# Default Email Templates - All system emails are customizable via PE Desk

# Email templates moved to email_templates.py
from email_templates import DEFAULT_EMAIL_TEMPLATES
