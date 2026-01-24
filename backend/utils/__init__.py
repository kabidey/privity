"""
Utils package
"""
from utils.auth import hash_password, verify_password, create_token, decode_token, get_current_user, check_permission
from utils.email import send_email, generate_otp, send_otp_email
from utils.notifications import manager, create_notification, notify_role, notify_roles
