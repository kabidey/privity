"""
Configuration and constants for the application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB Configuration
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# File upload directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Email Configuration
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.office365.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USERNAME)

# Emergent LLM Key for OCR
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

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
    1: ["all"],  # PE Desk - full access
    2: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    3: ["view_all", "manage_clients", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],
    4: ["view_own", "create_bookings", "view_clients", "create_clients"],
    5: ["view_own"]
}

# Allowed email domains for registration
ALLOWED_EMAIL_DOMAINS = ["smifs.com"]

# OTP Configuration
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3

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
    "STOCK_UPDATE": "Stock Updated",
    "STOCK_DELETE": "Stock Deleted",
    "PURCHASE_CREATE": "Purchase Created",
    "BOOKING_CREATE": "Booking Created",
    "BOOKING_APPROVE": "Booking Approved",
    "BOOKING_REJECT": "Booking Rejected",
    "BOOKING_UPDATE": "Booking Updated",
    "INVENTORY_ADJUST": "Inventory Adjusted",
    "CORPORATE_ACTION": "Corporate Action Applied",
    "EMAIL_TEMPLATE_UPDATE": "Email Template Updated",
}

# Default Email Templates
DEFAULT_EMAIL_TEMPLATES = {
    "client_welcome": {
        "name": "Client Welcome",
        "subject": "Welcome to Share Booking System",
        "body": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #064E3B;">Welcome to Share Booking System</h2>
    <p>Dear {{client_name}},</p>
    <p>Your account has been created successfully.</p>
    <p>Your OTC UCC Code: <strong>{{otc_ucc}}</strong></p>
    <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
</div>""",
        "variables": ["client_name", "otc_ucc"]
    },
    "client_approved": {
        "name": "Client Approved",
        "subject": "Account Approved - Share Booking System",
        "body": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #10b981;">Account Approved</h2>
    <p>Dear {{client_name}},</p>
    <p>Your account has been approved and is now active.</p>
    <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
</div>""",
        "variables": ["client_name"]
    },
    "booking_created": {
        "name": "Booking Created",
        "subject": "Booking Order Created - {{stock_symbol}} | {{booking_id}}",
        "body": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #064E3B;">Booking Order Created</h2>
    <p>Dear {{client_name}},</p>
    <p>A new booking order has been created:</p>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Order ID</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_id}}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Price</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{price}}</td>
        </tr>
    </table>
    <p style="color: #6b7280;">This order is pending approval.</p>
    <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
</div>""",
        "variables": ["client_name", "booking_id", "stock_symbol", "stock_name", "quantity", "price"]
    },
    "booking_approved": {
        "name": "Booking Approved",
        "subject": "Booking Approved - {{stock_symbol}} | {{booking_id}}",
        "body": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #10b981;">Booking Order Approved ✓</h2>
    <p>Dear {{client_name}},</p>
    <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
        </tr>
        <tr style="background-color: #f3f4f6;">
            <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
            <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approved_by}}</td>
        </tr>
    </table>
    <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
</div>""",
        "variables": ["client_name", "booking_id", "stock_symbol", "quantity", "approved_by"]
    },
    "password_reset_otp": {
        "name": "Password Reset OTP",
        "subject": "Password Reset OTP - Share Booking System",
        "body": """<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2 style="color: #333;">Password Reset Request</h2>
    <p>Dear {{user_name}},</p>
    <p>You have requested to reset your password. Use the following OTP:</p>
    <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
        <h1 style="color: #007bff; letter-spacing: 5px; margin: 0;">{{otp}}</h1>
    </div>
    <p><strong>This OTP is valid for 10 minutes.</strong></p>
    <p>If you did not request this, please ignore this email.</p>
</div>""",
        "variables": ["user_name", "otp"]
    }
}
