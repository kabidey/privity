"""
Services package initialization
"""
from .email_service import (
    send_email,
    generate_otp,
    send_otp_email,
    send_booking_notification_email,
    send_booking_approval_email,
    send_loss_booking_pending_email,
    send_loss_approval_email
)
from .notification_service import (
    ConnectionManager,
    ws_manager,
    create_notification,
    notify_roles
)
from .audit_service import create_audit_log
from .ocr_service import process_document_ocr
from .inventory_service import (
    update_inventory,
    get_stock_weighted_avg_price,
    check_stock_availability
)

__all__ = [
    # Email
    'send_email',
    'generate_otp',
    'send_otp_email',
    'send_booking_notification_email',
    'send_booking_approval_email',
    'send_loss_booking_pending_email',
    'send_loss_approval_email',
    # Notifications
    'ConnectionManager',
    'ws_manager',
    'create_notification',
    'notify_roles',
    # Audit
    'create_audit_log',
    # OCR
    'process_document_ocr',
    # Inventory
    'update_inventory',
    'get_stock_weighted_avg_price',
    'check_stock_availability',
]
