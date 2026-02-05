"""
CAPTCHA Service
Provides simple math-based CAPTCHA for login protection
No external API keys required
"""
import random
import hashlib
import time
import logging
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class CaptchaService:
    """
    Simple math-based CAPTCHA service
    Generates math problems that users must solve after failed login attempts
    """
    
    def __init__(self):
        # Store active CAPTCHA challenges: {token: (answer, expiry_time, email)}
        self.challenges: Dict[str, Tuple[int, float, str]] = {}
        self.challenge_expiry = 300  # 5 minutes
        
    def _cleanup_expired(self):
        """Remove expired challenges"""
        now = time.time()
        expired = [token for token, (_, expiry, _) in self.challenges.items() if now > expiry]
        for token in expired:
            del self.challenges[token]
    
    def generate_challenge(self, email: str) -> dict:
        """
        Generate a new CAPTCHA challenge
        Returns: {token, question, image_data (optional)}
        """
        self._cleanup_expired()
        
        # Generate random math problem
        operation = random.choice(['addition', 'subtraction', 'multiplication'])
        
        if operation == 'addition':
            a = random.randint(10, 50)
            b = random.randint(1, 20)
            answer = a + b
            question = f"What is {a} + {b}?"
            
        elif operation == 'subtraction':
            a = random.randint(20, 50)
            b = random.randint(1, 19)
            answer = a - b
            question = f"What is {a} - {b}?"
            
        else:  # multiplication
            a = random.randint(2, 12)
            b = random.randint(2, 9)
            answer = a * b
            question = f"What is {a} × {b}?"
        
        # Generate unique token
        token = hashlib.sha256(
            f"{email}{time.time()}{random.random()}".encode()
        ).hexdigest()[:32]
        
        # Store challenge
        expiry = time.time() + self.challenge_expiry
        self.challenges[token] = (answer, expiry, email)
        
        logger.info(f"Generated CAPTCHA challenge for {email}")
        
        return {
            "captcha_token": token,
            "captcha_question": question,
            "captcha_type": "math",
            "expires_in": self.challenge_expiry
        }
    
    def verify_challenge(self, token: str, user_answer: str, email: str) -> Tuple[bool, str]:
        """
        Verify a CAPTCHA answer
        Returns: (is_valid, message)
        """
        self._cleanup_expired()
        
        if not token or token not in self.challenges:
            return False, "CAPTCHA expired or invalid. Please request a new one."
        
        correct_answer, expiry, challenge_email = self.challenges[token]
        
        # Check if expired
        if time.time() > expiry:
            del self.challenges[token]
            return False, "CAPTCHA has expired. Please request a new one."
        
        # Check if email matches
        if challenge_email.lower() != email.lower():
            return False, "CAPTCHA token does not match this email."
        
        # Verify answer
        try:
            user_int = int(user_answer.strip())
            if user_int == correct_answer:
                # Remove used challenge
                del self.challenges[token]
                return True, "CAPTCHA verified successfully."
            else:
                return False, "Incorrect CAPTCHA answer. Please try again."
        except ValueError:
            return False, "Please enter a valid number."
    
    def requires_captcha(self, failed_attempts: int) -> bool:
        """Check if CAPTCHA is required based on failed attempts"""
        return failed_attempts >= 3

# Global captcha service instance
captcha_service = CaptchaService()


class SecurityAlertService:
    """
    Service for sending security-related email alerts
    """
    
    @staticmethod
    async def send_account_locked_alert(email: str, ip_address: str, lockout_minutes: int):
        """Send alert when account is locked due to failed attempts"""
        from services.email_service import send_email
        from database import db
        
        # Get user info
        user = await db.users.find_one({"email": email}, {"_id": 0, "name": 1})
        user_name = user.get("name", "User") if user else "User"
        
        # Get PE Desk users for alert
        pe_users = await db.users.find(
            {"role": {"$in": [1, 2]}},  # PE Desk and PE Manager
            {"_id": 0, "email": 1, "name": 1}
        ).to_list(10)
        
        subject = f"🔒 Security Alert: Account Locked - {email}"
        
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">🔒 Security Alert</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Account Locked Due to Failed Login Attempts</p>
            </div>
            
            <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
                <p>An account has been temporarily locked due to multiple failed login attempts:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Account Email</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">User Name</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{user_name}</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">IP Address</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{ip_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Lockout Duration</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{lockout_minutes} minutes</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Time</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                </table>
                
                <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 5px; padding: 15px; margin-top: 15px;">
                    <p style="margin: 0; color: #92400e;">
                        <strong>⚠️ Action Required:</strong> If this was not a legitimate login attempt, 
                        please investigate the source IP address and consider blocking it if suspicious.
                    </p>
                </div>
                
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">
                    This is an automated security alert from PRIVITY Share Booking System.
                </p>
            </div>
        </div>
        """
        
        # Send to all PE users
        for pe_user in pe_users:
            try:
                await send_email(
                    to_email=pe_user["email"],
                    subject=subject,
                    body=body
                )
                logger.info(f"Sent account locked alert to {pe_user['email']}")
            except Exception as e:
                logger.error(f"Failed to send alert to {pe_user['email']}: {e}")
    
    @staticmethod
    async def send_suspicious_activity_alert(
        event_type: str,
        ip_address: str,
        details: dict
    ):
        """Send alert for suspicious activity"""
        from services.email_service import send_email
        from database import db
        
        # Get PE Desk users for alert
        pe_users = await db.users.find(
            {"role": 1},  # PE Desk only for suspicious activity
            {"_id": 0, "email": 1}
        ).to_list(5)
        
        subject = f"⚠️ Security Alert: Suspicious Activity Detected"
        
        details_html = "".join([
            f'<tr><td style="padding: 8px; border: 1px solid #e5e7eb;">{k}</td>'
            f'<td style="padding: 8px; border: 1px solid #e5e7eb;">{v}</td></tr>'
            for k, v in details.items()
        ])
        
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">⚠️ Suspicious Activity Detected</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">{event_type}</p>
            </div>
            
            <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
                <p>Suspicious activity has been detected on the system:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Event Type</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{event_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">IP Address</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{ip_address}</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Time</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    {details_html}
                </table>
                
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">
                    This is an automated security alert from PRIVITY Share Booking System.
                </p>
            </div>
        </div>
        """
        
        # Send to PE Desk users
        for pe_user in pe_users:
            try:
                await send_email(
                    to_email=pe_user["email"],
                    subject=subject,
                    body=body
                )
            except Exception as e:
                logger.error(f"Failed to send suspicious activity alert: {e}")
    
    @staticmethod
    async def send_new_login_alert(user_email: str, user_name: str, ip_address: str, user_agent: str):
        """Send alert to user about new login"""
        from services.email_service import send_email
        
        subject = "🔐 New Login to Your PRIVITY Account"
        
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">🔐 New Login Detected</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Your PRIVITY account was accessed</p>
            </div>
            
            <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
                <p>Hello {user_name},</p>
                <p>We detected a new login to your PRIVITY account:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Time</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">IP Address</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{ip_address}</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Device</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{user_agent[:100]}...</td>
                    </tr>
                </table>
                
                <div style="background: #fef3c7; border: 1px solid #f59e0b; border-radius: 5px; padding: 15px; margin-top: 15px;">
                    <p style="margin: 0; color: #92400e;">
                        <strong>Not you?</strong> If you did not make this login, please change your password immediately 
                        and contact your administrator.
                    </p>
                </div>
                
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">
                    This is an automated security notification from PRIVITY Share Booking System.
                </p>
            </div>
        </div>
        """
        
        try:
            await send_email(
                to_email=user_email,
                subject=subject,
                body=body
            )
            logger.info(f"Sent new login alert to {user_email}")
        except Exception as e:
            logger.error(f"Failed to send login alert to {user_email}: {e}")
    
    @staticmethod
    async def send_unusual_login_alert(
        user_email: str,
        user_name: str,
        ip_address: str,
        user_agent: str,
        location_data: dict
    ):
        """Send alert for unusual login location"""
        from services.email_service import send_email
        from database import db
        
        location = location_data.get("location", {})
        alerts = location_data.get("alerts", [])
        risk_level = location_data.get("risk_level", "unknown")
        
        # Determine color based on risk
        color_map = {
            "critical": ("#dc2626", "#ef4444", "🚨"),
            "high": ("#ea580c", "#f97316", "⚠️"),
            "medium": ("#d97706", "#f59e0b", "⚡"),
            "low": ("#0891b2", "#06b6d4", "ℹ️")
        }
        color1, color2, emoji = color_map.get(risk_level, ("#6b7280", "#9ca3af", "❓"))
        
        # Build alerts HTML
        alerts_html = ""
        for alert in alerts:
            severity_colors = {
                "critical": "#dc2626",
                "high": "#ea580c", 
                "medium": "#d97706",
                "low": "#0891b2"
            }
            alert_color = severity_colors.get(alert.get("severity"), "#6b7280")
            alerts_html += f'''
            <div style="background: {alert_color}15; border-left: 4px solid {alert_color}; padding: 10px; margin: 5px 0; border-radius: 0 5px 5px 0;">
                <strong style="color: {alert_color};">{alert.get("type", "Alert").replace("_", " ").title()}</strong>
                <p style="margin: 5px 0 0 0; color: #374151;">{alert.get("message", "")}</p>
            </div>
            '''
        
        subject = f"{emoji} Unusual Login Alert - {user_email}"
        
        body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, {color1}, {color2}); color: white; padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="margin: 0;">{emoji} Unusual Login Detected</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Risk Level: {risk_level.upper()}</p>
            </div>
            
            <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
                <p>An unusual login has been detected for account: <strong>{user_email}</strong></p>
                
                <h3 style="color: #374151; margin-top: 20px;">📍 Location Details</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Country</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{location.get("country", "Unknown")}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">City</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{location.get("city", "Unknown")}</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">ISP</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{location.get("isp", "Unknown")}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">IP Address</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{ip_address}</td>
                    </tr>
                    <tr style="background: #f9fafb;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">VPN/Proxy</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{"Yes ⚠️" if location_data.get("is_proxy") else "No"}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb; font-weight: bold;">Time</td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                </table>
                
                <h3 style="color: #374151; margin-top: 20px;">🚨 Security Alerts</h3>
                {alerts_html if alerts_html else '<p style="color: #6b7280;">No specific alerts</p>'}
                
                <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 5px; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0; color: #991b1b;">
                        <strong>Action Required:</strong> If this login was not authorized, please:
                        <ol style="margin: 10px 0 0 0; padding-left: 20px;">
                            <li>Change the user's password immediately</li>
                            <li>Check the Security Status dashboard for more details</li>
                            <li>Consider blocking the IP address if suspicious</li>
                        </ol>
                    </p>
                </div>
                
                <p style="margin-top: 20px; color: #6b7280; font-size: 12px;">
                    This is an automated security alert from PRIVITY Share Booking System.
                </p>
            </div>
        </div>
        """
        
        # Send to PE Desk users
        pe_users = await db.users.find(
            {"role": {"$in": [1, 2]}},
            {"_id": 0, "email": 1}
        ).to_list(10)
        
        for pe_user in pe_users:
            try:
                await send_email(
                    to_email=pe_user["email"],
                    subject=subject,
                    body=body
                )
                logger.info(f"Sent unusual login alert to {pe_user['email']}")
            except Exception as e:
                logger.error(f"Failed to send unusual login alert: {e}")
        
        # Also notify the user themselves
        try:
            await send_email(
                to_email=user_email,
                subject=f"{emoji} Security Alert: Unusual login to your account",
                body=body
            )
        except Exception as e:
            logger.error(f"Failed to send unusual login alert to user: {e}")


# Export
__all__ = ['CaptchaService', 'captcha_service', 'SecurityAlertService']
