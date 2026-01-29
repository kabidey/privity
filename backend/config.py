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
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://privity-share.preview.emergentagent.com')

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
    9: "Partners Desk"
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
    6: ["view_own"],
    7: ["view_own", "create_bookings", "view_clients", "create_clients", "view_finance", "manage_finance"],  # Finance - Employee + full Finance access
    8: ["view_own", "create_bookings", "view_clients", "create_clients", "view_bp_dashboard", "view_bp_reports"],  # Business Partner - can create bookings and clients, view own dashboard
    9: ["view_own", "create_bookings", "view_clients", "create_clients", "manage_business_partners", "view_bp_revenue", "add_business_partners"]  # Partners Desk - Employee + BP management (no delete)
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
DEFAULT_EMAIL_TEMPLATES = {
    "welcome": {
        "key": "welcome",
        "name": "Welcome Email (Client)",
        "subject": "Welcome to Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Welcome to SMIFS Private Equity System</h2>
            <p>Dear {{client_name}},</p>
            <p>Your account has been created successfully!</p>
            <p>You can now participate in share booking transactions through our platform.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name"],
        "is_active": True
    },
    "client_approved": {
        "key": "client_approved",
        "name": "Client Approved",
        "subject": "Account Approved - Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Account Approved ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your account has been <strong style="color: #10b981;">APPROVED</strong> and is now active.</p>
            <p>Your OTC UCC: <strong>{{otc_ucc}}</strong></p>
            <p>You can now participate in share booking transactions.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "otc_ucc"],
        "is_active": True
    },
    "booking_created": {
        "key": "booking_created",
        "name": "Booking Created (Pending Approval)",
        "subject": "Booking Created - Pending Approval | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #f59e0b;">Booking Order Created</h2>
            <p>Dear {{client_name}},</p>
            <p>A new booking order has been created and is pending internal approval.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Order ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
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
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Internal Approval</span></td>
                </tr>
            </table>
            
            <p style="color: #6b7280; font-size: 14px;">You will receive a confirmation request email once the booking is approved internally.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "quantity"],
        "is_active": True
    },
    "booking_confirmation_request": {
        "key": "booking_confirmation_request",
        "name": "Booking Confirmation Request",
        "subject": "Action Required: Confirm Booking - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Booking Approved - Please Confirm ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong> by PE Desk. Please confirm your acceptance to proceed.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client OTC UCC</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{otc_ucc}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{buying_price}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Value</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_value}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approved_by}} (PE Desk)</td>
                </tr>
            </table>
            
            <div style="margin: 30px 0; text-align: center;">
                <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                <a href="{{accept_url}}" style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">✓ ACCEPT BOOKING</a>
                <a href="{{deny_url}}" style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">✗ DENY BOOKING</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">Please review and confirm this booking. If you accept, payment can be initiated. If you deny, the booking will be cancelled.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "otc_ucc", "stock_symbol", "stock_name", "quantity", "buying_price", "total_value", "approved_by", "accept_url", "deny_url"],
        "is_active": True
    },
    "booking_pending_loss_review": {
        "key": "booking_pending_loss_review",
        "name": "Booking Pending Loss Review",
        "subject": "Booking Approved - Pending Loss Review | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #f59e0b;">Booking Approved - Pending Loss Review</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking order has been approved. However, since this is a loss transaction, it requires additional review. You will receive a confirmation request once fully approved.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Loss Review</span></td>
                </tr>
            </table>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol"],
        "is_active": True
    },
    "loss_booking_confirmation_request": {
        "key": "loss_booking_confirmation_request",
        "name": "Loss Booking Confirmation Request",
        "subject": "Action Required: Confirm Loss Booking - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Booking Fully Approved - Please Confirm ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>Your loss booking order has been <strong style="color: #10b981;">FULLY APPROVED</strong>. Please confirm your acceptance to proceed.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Landing Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{buying_price}}</td>
                </tr>
                <tr style="background-color: #fef3c7;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Selling Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{selling_price}} <span style="color: #dc2626;">(Loss Transaction)</span></td>
                </tr>
            </table>
            
            <div style="margin: 30px 0; text-align: center;">
                <p style="margin-bottom: 20px; font-weight: bold;">Please confirm your booking:</p>
                <a href="{{accept_url}}" style="display: inline-block; background-color: #22c55e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin-right: 10px; font-weight: bold;">✓ ACCEPT BOOKING</a>
                <a href="{{deny_url}}" style="display: inline-block; background-color: #ef4444; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: bold;">✗ DENY BOOKING</a>
            </div>
            
            <p style="color: #6b7280; font-size: 14px;">This is a loss transaction booking. Please review carefully before confirming.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "quantity", "buying_price", "selling_price", "accept_url", "deny_url"],
        "is_active": True
    },
    "booking_status_updated": {
        "key": "booking_status_updated",
        "name": "Booking Status Updated",
        "subject": "Booking Status Updated - {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Booking Status Updated</h2>
            <p>Dear {{client_name}},</p>
            <p>Your booking <strong>{{booking_number}}</strong> status has been updated to: <strong style="color: #064E3B;">{{status}}</strong></p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "status"],
        "is_active": True
    },
    "payment_complete": {
        "key": "payment_complete",
        "name": "Client Payment Complete",
        "subject": "Payment Complete - Booking {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Payment Complete ✓</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to confirm that full payment has been received for your booking:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>Your booking is now ready for DP transfer.</strong></p>
            </div>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "quantity", "total_amount"],
        "is_active": True
    },
    "stock_transfer_complete": {
        "key": "stock_transfer_complete",
        "name": "Stock Transfer Completed",
        "subject": "Stock Transfer Completed - {{stock_symbol}} | {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ Stock Transfer Completed</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to inform you that your stock has been successfully transferred to your Demat account.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Transfer Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Booking Reference</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock Symbol</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>ISIN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{isin_number}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity Transferred</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Your DP ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #064E3B;">{{dp_id}}</strong></td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Transfer Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{transfer_date}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>Note:</strong> Please verify the credit in your Demat account. The shares should reflect within 1-2 working days.</p>
            </div>
            
            <p>If you have any questions, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "stock_name", "isin_number", "quantity", "dp_id", "transfer_date"],
        "is_active": True
    },
    "purchase_order_created": {
        "key": "purchase_order_created",
        "name": "Purchase Order Created (Vendor)",
        "subject": "Purchase Order Confirmation - {{stock_symbol}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Purchase Order Confirmation</h2>
            <p>Dear {{vendor_name}},</p>
            <p>A purchase order has been created for your stock.</p>
            
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
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Price per Unit</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{price_per_unit}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
            </table>
            
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["vendor_name", "stock_symbol", "quantity", "price_per_unit", "total_amount"],
        "is_active": True
    },
    "vendor_payment_received": {
        "key": "vendor_payment_received",
        "name": "Vendor Payment Received",
        "subject": "Payment Received - {{stock_symbol}} Purchase | ₹{{payment_amount}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">Payment Received</h2>
            <p>Dear {{vendor_name}},</p>
            <p>We are pleased to inform you that a payment has been processed for your stock purchase.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Payment Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}} - {{stock_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Purchase Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{quantity}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Purchase Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{purchase_date}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Purchase Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_amount}}</td>
                </tr>
                <tr style="background-color: #d1fae5;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>This Payment</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #10b981;">₹{{payment_amount}}</strong></td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Paid Till Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{total_paid}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Balance Remaining</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{remaining_balance}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Payment Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>{{payment_status}}</strong></td>
                </tr>
            </table>
            
            <p>If you have any questions regarding this payment, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["vendor_name", "stock_symbol", "stock_name", "quantity", "purchase_date", "total_amount", "payment_amount", "total_paid", "remaining_balance", "payment_status"],
        "is_active": True
    },
    "password_otp": {
        "key": "password_otp",
        "name": "Password Reset OTP",
        "subject": "Password Reset OTP - Private Equity System",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Password Reset Request</h2>
            <p>Dear {{user_name}},</p>
            <p>Your OTP for password reset is:</p>
            <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
                <h1 style="color: #064E3B; letter-spacing: 5px; margin: 0;">{{otp}}</h1>
            </div>
            <p>This OTP is valid for <strong>{{expiry_minutes}} minutes</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">If you did not request this password reset, please ignore this email.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["user_name", "otp", "expiry_minutes"],
        "is_active": True
    },
    "user_created": {
        "key": "user_created",
        "name": "User Account Created",
        "subject": "Welcome to Private Equity System - Account Created",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Welcome to SMIFS Private Equity System</h2>
            <p>Dear {{user_name}},</p>
            <p>Your staff account has been created successfully!</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Email</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{email}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Role</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{role_name}}</td>
                </tr>
            </table>
            
            <p>You can now log in to the system using your credentials.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["user_name", "email", "role_name"],
        "is_active": True
    },
    "refund_completed": {
        "key": "refund_completed",
        "name": "Refund Completed",
        "subject": "Refund Processed - Booking {{booking_number}}",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Refund Processed Successfully</h2>
            <p>Dear {{client_name}},</p>
            <p>We are pleased to inform you that your refund has been processed successfully.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #064E3B; color: white;">
                    <th style="padding: 10px; text-align: left;" colspan="2">Refund Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{stock_symbol}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Refund Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #059669;">₹{{refund_amount}}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Reference Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{reference_number}}</td>
                </tr>
            </table>
            
            <p>The refund amount has been credited to your registered bank account. Please allow 2-3 business days for the amount to reflect in your account.</p>
            <p>If you have any questions regarding this refund, please contact us.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["client_name", "booking_number", "stock_symbol", "refund_amount", "reference_number"],
        "is_active": True
    },
    "rp_deal_notification": {
        "key": "rp_deal_notification",
        "name": "RP Deal Notification",
        "subject": "Revenue Booked - Booking {{booking_number}} | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ New Revenue Booked</h2>
            <p>Dear {{rp_name}},</p>
            <p>We are pleased to inform you that a stock transfer has been completed for a booking you referred. Your commission has been booked.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Deal Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Your RP Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace;">{{rp_code}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Reference</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{booking_number}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{client_name}}</td>
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
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Transfer Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{transfer_date}}</td>
                </tr>
            </table>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #7c3aed; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Your Commission</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Deal Profit</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{{profit}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Your Share</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{revenue_share_percent}}%</td>
                </tr>
                <tr style="background-color: #d1fae5;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Commission Amount</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong style="color: #059669; font-size: 18px;">₹{{payment_amount}}</strong></td>
                </tr>
            </table>
            
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;"><strong>Note:</strong> Your commission is now pending and will be processed as per our payment cycle.</p>
            </div>
            
            <p>Thank you for your continued partnership!</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "booking_number", "client_name", "stock_symbol", "stock_name", "quantity", "transfer_date", "profit", "revenue_share_percent", "payment_amount"],
        "is_active": True
    },
    "rp_approval_notification": {
        "key": "rp_approval_notification",
        "name": "RP Approval Notification",
        "subject": "Welcome! Your Referral Partner Application is Approved | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #10b981;">✓ Application Approved</h2>
            <p>Dear {{rp_name}},</p>
            <p>We are pleased to inform you that your Referral Partner application has been <strong style="color: #10b981;">APPROVED</strong>.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #064E3B; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Your RP Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Your RP Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace; font-size: 16px; color: #059669;"><strong>{{rp_code}}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{rp_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>PAN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{pan_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approved_by}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approval Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{approval_date}}</td>
                </tr>
            </table>
            
            <div style="background-color: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #065f46;"><strong>What's Next?</strong> You can now refer clients and earn commissions on successful bookings. Share your RP code <strong>{{rp_code}}</strong> with potential clients.</p>
            </div>
            
            <p>Thank you for partnering with us!</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "pan_number", "approved_by", "approval_date"],
        "is_active": True
    },
    "rp_rejection_notification": {
        "key": "rp_rejection_notification",
        "name": "RP Rejection Notification",
        "subject": "Referral Partner Application Update | SMIFS PE",
        "body": """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc2626;">Application Not Approved</h2>
            <p>Dear {{rp_name}},</p>
            <p>We regret to inform you that your Referral Partner application has not been approved at this time.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 1px solid #e5e7eb;">
                <tr style="background-color: #7f1d1d; color: white;">
                    <th colspan="2" style="padding: 12px; text-align: left;">Application Details</th>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb; width: 40%;"><strong>Application Code</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb; font-family: monospace;">{{rp_code}}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Name</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{rp_name}}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>PAN Number</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{{pan_number}}</td>
                </tr>
            </table>
            
            <div style="background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #991b1b;"><strong>Reason for Rejection:</strong></p>
                <p style="margin: 8px 0 0 0; color: #7f1d1d;">{{rejection_reason}}</p>
            </div>
            
            <p>If you believe this decision was made in error or would like to re-apply with corrected information, please contact our PE Desk.</p>
            <p>Best regards,<br><strong>SMIFS Private Equity System</strong></p>
        </div>
        """,
        "variables": ["rp_name", "rp_code", "pan_number", "rejection_reason"],
        "is_active": True
    }
}
