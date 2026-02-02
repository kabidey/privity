"""
TOTP Service for Two-Factor Authentication

Implements RFC 6238 Time-Based One-Time Password (TOTP) generation and verification
using the PyOTP library for secure second-factor authentication.
"""
import pyotp
import qrcode
import io
import base64
import secrets
import string
from typing import List, Tuple, Optional
from datetime import datetime, timezone
import hashlib
import bcrypt

# Configuration
TOTP_ISSUER = "SMIFS Privity"
TOTP_DIGITS = 6
TOTP_PERIOD = 30  # seconds (RFC 6238 recommendation)


class TOTPService:
    """Service for TOTP operations"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new random TOTP secret using base32 encoding"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_instance(secret: str) -> pyotp.TOTP:
        """Create a TOTP instance for a given secret"""
        return pyotp.TOTP(
            secret,
            digits=TOTP_DIGITS,
            interval=TOTP_PERIOD,
            issuer=TOTP_ISSUER
        )
    
    @staticmethod
    def generate_provisioning_uri(secret: str, user_email: str) -> str:
        """Generate OTPAuth URI for QR code provisioning"""
        totp = TOTPService.get_totp_instance(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=TOTP_ISSUER
        )
    
    @staticmethod
    def generate_qr_code_image(provisioning_uri: str) -> bytes:
        """Generate QR code image as PNG bytes"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_qr_code_data_url(qr_code_bytes: bytes) -> str:
        """Convert QR code PNG bytes to data URL for frontend display"""
        base64_data = base64.b64encode(qr_code_bytes).decode()
        return f"data:image/png;base64,{base64_data}"
    
    @staticmethod
    def verify_token(secret: str, token: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP token against the secret
        valid_window allows for time drift (default: 1 time step = ±30s)
        """
        if not token or len(token) != TOTP_DIGITS:
            return False
        
        # Ensure token is only digits
        if not token.isdigit():
            return False
        
        totp = TOTPService.get_totp_instance(secret)
        
        try:
            return totp.verify(token, valid_window=valid_window)
        except Exception:
            return False
    
    @staticmethod
    def get_current_token(secret: str) -> str:
        """Get the current TOTP token (primarily for testing)"""
        totp = TOTPService.get_totp_instance(secret)
        return totp.now()
    
    @staticmethod
    def get_time_remaining() -> int:
        """Get seconds remaining for current TOTP token"""
        elapsed = datetime.now(timezone.utc).timestamp() % TOTP_PERIOD
        return int(TOTP_PERIOD - elapsed)


class BackupCodeService:
    """Service for backup/recovery code operations"""
    
    @staticmethod
    def generate_backup_codes(count: int = 10, length: int = 8) -> List[str]:
        """Generate cryptographically secure backup codes"""
        backup_codes = []
        for _ in range(count):
            # Generate code with alphanumeric characters (easy to type)
            code = ''.join(
                secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
                for _ in range(length)
            )
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            backup_codes.append(formatted_code)
        return backup_codes
    
    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash a backup code using bcrypt for secure storage"""
        # Remove formatting dash before hashing
        clean_code = code.replace("-", "")
        return bcrypt.hashpw(clean_code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_backup_code(plain_code: str, hashed_code: str) -> bool:
        """Verify a backup code against its bcrypt hash"""
        try:
            # Remove formatting dash before verification
            clean_code = plain_code.replace("-", "").upper()
            return bcrypt.checkpw(clean_code.encode('utf-8'), hashed_code.encode('utf-8'))
        except Exception:
            return False


class TwoFactorManager:
    """Main manager class for 2FA operations"""
    
    @staticmethod
    def setup_2fa(user_email: str) -> dict:
        """
        Initialize 2FA setup for a user.
        Returns secret, QR code data URL, and backup codes.
        """
        # Generate TOTP secret
        secret = TOTPService.generate_secret()
        
        # Generate provisioning URI
        provisioning_uri = TOTPService.generate_provisioning_uri(secret, user_email)
        
        # Generate QR code
        qr_code_bytes = TOTPService.generate_qr_code_image(provisioning_uri)
        qr_code_url = TOTPService.generate_qr_code_data_url(qr_code_bytes)
        
        # Generate backup codes
        backup_codes = BackupCodeService.generate_backup_codes()
        
        # Hash backup codes for storage
        backup_codes_hashed = [BackupCodeService.hash_backup_code(code) for code in backup_codes]
        
        return {
            "secret": secret,
            "qr_code_url": qr_code_url,
            "backup_codes": backup_codes,
            "backup_codes_hashed": backup_codes_hashed
        }
    
    @staticmethod
    def verify_setup(secret: str, totp_code: str) -> bool:
        """Verify TOTP code during initial setup"""
        return TOTPService.verify_token(secret, totp_code)
    
    @staticmethod
    def verify_login(secret: str, totp_code: str) -> bool:
        """Verify TOTP code during login"""
        return TOTPService.verify_token(secret, totp_code)
    
    @staticmethod
    def verify_backup_code(input_code: str, stored_hashed_codes: List[str]) -> Tuple[bool, int]:
        """
        Verify a backup code against stored hashes.
        Returns (is_valid, index_of_used_code) or (False, -1) if not found.
        """
        for index, hashed_code in enumerate(stored_hashed_codes):
            if BackupCodeService.verify_backup_code(input_code, hashed_code):
                return True, index
        return False, -1
