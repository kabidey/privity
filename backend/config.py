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
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://share-trade-portal.preview.emergentagent.com')

# User Roles
ROLES = {
    1: "PE Desk",
    2: "Zonal Manager",
    3: "Manager",
    4: "Employee",
    5: "Viewer"
}

# Role Permissions
ROLE_PERMISSIONS = {
    1: ["all"],  # PE Desk - full access, can approve bookings, manage vendors
    2: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    3: ["view_all", "manage_clients", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    4: ["view_own", "create_bookings", "view_clients", "create_clients"],
    5: ["view_own"]
}

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

# Default Email Templates
DEFAULT_EMAIL_TEMPLATES = {
    "welcome": {
        "key": "welcome",
        "name": "Welcome Email",
        "subject": "Welcome to Share Booking System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Welcome to Share Booking System</h2>
            <p>Dear {{user_name}},</p>
            <p>Your account has been created successfully with the role of <strong>{{role_name}}</strong>.</p>
            <p>You can now login to the system using your email and password.</p>
            <p>Best regards,<br>Share Booking System Team</p>
        </div>
        """,
        "variables": ["user_name", "role_name", "email"],
        "is_active": True
    },
    "client_approved": {
        "key": "client_approved",
        "name": "Client Approved",
        "subject": "Client {{client_name}} Approved",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #28a745;">Client Approved</h2>
            <p>The client <strong>{{client_name}}</strong> has been approved.</p>
            <p>You can now create bookings for this client.</p>
            <p>OTC UCC: {{otc_ucc}}</p>
        </div>
        """,
        "variables": ["client_name", "otc_ucc", "approved_by"],
        "is_active": True
    },
    "booking_created": {
        "key": "booking_created",
        "name": "Booking Created",
        "subject": "New Booking Created - {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Booking Confirmation</h2>
            <p>Dear {{client_name}},</p>
            <p>A new booking has been created for you:</p>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Stock</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{stock_symbol}} - {{stock_name}}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Quantity</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{{quantity}}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Price</strong></td><td style="padding: 8px; border: 1px solid #ddd;">₹{{buying_price}}</td></tr>
            </table>
        </div>
        """,
        "variables": ["client_name", "stock_symbol", "stock_name", "quantity", "buying_price", "booking_date"],
        "is_active": True
    },
    "booking_approved": {
        "key": "booking_approved",
        "name": "Booking Approved",
        "subject": "Booking Approved - {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #28a745;">Booking Approved</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking for <strong>{{stock_symbol}}</strong> has been approved.</p>
            <p>Quantity: {{quantity}}</p>
            <p>Approved by: {{approved_by}}</p>
        </div>
        """,
        "variables": ["client_name", "stock_symbol", "quantity", "approved_by"],
        "is_active": True
    },
    "password_otp": {
        "key": "password_otp",
        "name": "Password Reset OTP",
        "subject": "Password Reset OTP - Share Booking System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #333;">Password Reset Request</h2>
            <p>Dear {{user_name}},</p>
            <p>Your OTP for password reset is:</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center;">
                <h1 style="color: #007bff; letter-spacing: 5px;">{{otp}}</h1>
            </div>
            <p>This OTP is valid for {{expiry_minutes}} minutes.</p>
        </div>
        """,
        "variables": ["user_name", "otp", "expiry_minutes"],
        "is_active": True
    }
}
