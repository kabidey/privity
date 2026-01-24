from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import io
import csv
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import aiofiles
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import asyncio
import random
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Emergent LLM Key for OCR
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# OTP Configuration
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# WebSocket Connection Manager for Real-time Notifications
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logging.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.error(f"Failed to send to user {user_id}: {e}")
    
    async def send_to_roles(self, roles: List[int], message: dict):
        users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
        for user in users:
            await self.send_to_user(user["id"], message)

ws_manager = ConnectionManager()

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
    2: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],  # Zonal Manager - no vendor access
    3: ["view_all", "manage_clients", "manage_bookings", "manage_purchases", "view_reports", "approve_clients"],  # Manager - no vendor access
    4: ["view_own", "create_bookings", "view_clients", "create_clients"],  # Employee - no vendor access, can only see own clients
    5: ["view_own"]  # Viewer - read only
}

# Allowed email domains for registration
ALLOWED_EMAIL_DOMAINS = ["smifs.com"]

# Audit Log Types
AUDIT_ACTIONS = {
    "USER_REGISTER": "User Registration",
    "USER_LOGIN": "User Login",
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
    "INVENTORY_ADJUST": "Inventory Adjusted",
}

# Audit Log Model
class AuditLog(BaseModel):
    id: str
    action: str
    action_description: str
    entity_type: str  # user, client, vendor, stock, purchase, booking
    entity_id: str
    entity_name: Optional[str] = None
    user_id: str
    user_name: str
    user_role: int
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: str

async def create_audit_log(
    action: str,
    entity_type: str,
    entity_id: str,
    user_id: str,
    user_name: str,
    user_role: int,
    entity_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """Create an audit log entry"""
    try:
        audit_doc = {
            "id": str(uuid.uuid4()),
            "action": action,
            "action_description": AUDIT_ACTIONS.get(action, action),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_doc)
        logging.info(f"Audit: {action} by {user_name} on {entity_type}/{entity_id}")
    except Exception as e:
        logging.error(f"Failed to create audit log: {e}")

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: int = 4  # Default to Employee for smifs.com domain

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: int
    role_name: str
    created_at: str

class TokenResponse(BaseModel):
    token: str
    user: User

# Password Reset Models
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetVerify(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

# Notification Model
class Notification(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: str

class BankAccount(BaseModel):
    bank_name: str
    account_number: str
    ifsc_code: str
    branch_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    source: str = "manual"  # manual, cml_copy, cancelled_cheque

class ClientDocument(BaseModel):
    doc_type: str  # pan_card, cml_copy, cancelled_cheque
    filename: str
    file_path: str = ""
    upload_date: str
    ocr_data: Optional[Dict[str, Any]] = None

class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: str
    dp_id: str
    address: Optional[str] = None
    pin_code: Optional[str] = None
    bank_accounts: List[BankAccount] = []
    is_vendor: bool = False

class Client(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    otc_ucc: str  # Unique OTC UCC code
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: str
    dp_id: str
    address: Optional[str] = None
    pin_code: Optional[str] = None
    bank_accounts: List[BankAccount] = []
    is_vendor: bool = False
    is_active: bool = True  # Requires approval for employee-created clients
    approval_status: str = "approved"  # pending, approved, rejected
    documents: List[ClientDocument] = []
    created_at: str
    created_by: str
    created_by_role: int = 5
    mapped_employee_id: Optional[str] = None
    mapped_employee_name: Optional[str] = None

class StockCreate(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None
    isin_number: Optional[str] = None
    sector: Optional[str] = None
    product: Optional[str] = None
    face_value: Optional[float] = None

class Stock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    symbol: str
    name: str
    exchange: Optional[str] = None
    isin_number: Optional[str] = None
    sector: Optional[str] = None
    product: Optional[str] = None
    face_value: Optional[float] = None
    created_at: str

# Corporate Actions Models
class CorporateActionCreate(BaseModel):
    stock_id: str
    action_type: str  # stock_split, bonus
    ratio_from: int  # e.g., 1 (for 1:2 split) or existing shares
    ratio_to: int  # e.g., 2 (for 1:2 split) or bonus shares
    new_face_value: Optional[float] = None  # For stock split
    record_date: str  # Date on which adjustment applies
    notes: Optional[str] = None

class CorporateAction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    stock_id: str
    stock_symbol: str
    stock_name: str
    action_type: str
    ratio_from: int
    ratio_to: int
    new_face_value: Optional[float] = None
    record_date: str
    status: str = "pending"  # pending, applied
    applied_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    created_by: str

class PurchaseCreate(BaseModel):
    vendor_id: str
    stock_id: str
    quantity: int
    price_per_unit: float
    purchase_date: str
    notes: Optional[str] = None

class Purchase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    vendor_id: str
    vendor_name: str
    stock_id: str
    stock_symbol: str
    quantity: int
    price_per_unit: float
    total_amount: float
    purchase_date: str
    notes: Optional[str] = None
    created_at: str
    created_by: str

class Inventory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    stock_id: str
    stock_symbol: str
    stock_name: str
    available_quantity: int
    weighted_avg_price: float
    total_value: float

class BookingCreate(BaseModel):
    client_id: str
    stock_id: str
    quantity: int
    buying_price: Optional[float] = None  # Will use weighted avg if not provided
    selling_price: Optional[float] = None
    booking_date: str
    status: str = "open"
    notes: Optional[str] = None

# Payment Tranche Model
class PaymentTranche(BaseModel):
    tranche_number: int  # 1 to 4
    amount: float
    payment_date: str
    recorded_by: str
    recorded_at: str
    notes: Optional[str] = None

class PaymentTrancheCreate(BaseModel):
    amount: float
    payment_date: str
    notes: Optional[str] = None

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    stock_id: str
    quantity: int
    buying_price: float
    selling_price: Optional[float] = None
    booking_date: str
    status: str
    approval_status: str = "pending"  # pending, approved, rejected - for inventory adjustment
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    created_by: str
    # Payment tracking
    payments: List[PaymentTranche] = []
    total_paid: float = 0
    payment_status: str = "pending"  # pending, partial, completed
    payment_completed_at: Optional[str] = None
    dp_transfer_ready: bool = False

class BookingWithDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    client_name: str
    client_pan: Optional[str] = None
    client_dp_id: Optional[str] = None
    stock_id: str
    stock_symbol: str
    stock_name: str
    quantity: int
    buying_price: float
    selling_price: Optional[float] = None
    total_amount: Optional[float] = None
    booking_date: str
    status: str
    approval_status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    profit_loss: Optional[float] = None
    created_at: str
    created_by: str
    created_by_name: str
    # Payment tracking
    payments: List[PaymentTranche] = []
    total_paid: float = 0
    payment_status: str = "pending"
    payment_completed_at: Optional[str] = None
    dp_transfer_ready: bool = False

# DP Transfer Report Model
class DPTransferRecord(BaseModel):
    booking_id: str
    client_name: str
    pan_number: str
    dp_id: str
    stock_symbol: str
    stock_name: str
    quantity: int
    total_amount: float
    total_paid: float
    payment_completed_at: str

class DashboardStats(BaseModel):
    total_clients: int
    total_vendors: int
    total_stocks: int
    total_bookings: int
    open_bookings: int
    closed_bookings: int
    total_profit_loss: float
    total_inventory_value: float
    total_purchases: int

class ClientPortfolio(BaseModel):
    client_id: str
    client_name: str
    total_bookings: int
    open_bookings: int
    closed_bookings: int
    total_profit_loss: float
    bookings: List[BookingWithDetails]

# Helper Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def check_permission(user: dict, required_permission: str):
    user_role = user.get("role", 5)
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    
    if "all" in permissions:
        return True
    
    if required_permission in permissions:
        return True
    
    raise HTTPException(status_code=403, detail="Insufficient permissions")

async def send_email(to_email: str, subject: str, body: str, cc_email: Optional[str] = None):
    """Send email via MS Exchange with optional CC"""
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logging.warning("Email credentials not configured")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        if cc_email:
            msg['Cc'] = cc_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logging.info(f"Email sent to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")

def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))

async def send_otp_email(to_email: str, otp: str, user_name: str = "User"):
    """Send OTP email for password reset"""
    subject = "Password Reset OTP - Share Booking System"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Password Reset Request</h2>
        <p>Dear {user_name},</p>
        <p>You have requested to reset your password. Use the following OTP to proceed:</p>
        <div style="background: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
            <h1 style="color: #007bff; letter-spacing: 5px; margin: 0;">{otp}</h1>
        </div>
        <p><strong>This OTP is valid for {OTP_EXPIRY_MINUTES} minutes.</strong></p>
        <p>If you did not request this password reset, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">This is an automated message from Share Booking System.</p>
    </div>
    """
    await send_email(to_email, subject, body)

async def create_notification(user_id: str, notif_type: str, title: str, message: str, data: dict = None):
    """Create and store notification, then send via WebSocket"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": notif_type,
        "title": title,
        "message": message,
        "data": data or {},
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notifications.insert_one(notification)
    
    # Send via WebSocket
    await ws_manager.send_to_user(user_id, {
        "event": "notification",
        "data": notification
    })
    
    return notification

async def notify_roles(roles: List[int], notif_type: str, title: str, message: str, data: dict = None):
    """Create notifications for all users with specified roles"""
    users = await db.users.find({"role": {"$in": roles}}, {"id": 1}).to_list(1000)
    for user in users:
        await create_notification(user["id"], notif_type, title, message, data)

async def process_document_ocr(file_path: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """Process document OCR using AI vision model"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        
        # Read and encode the file
        file_ext = file_path.lower().split('.')[-1]
        
        # For PDF, convert first page to image
        if file_ext == 'pdf':
            try:
                # Convert PDF to images (first page only for speed)
                images = convert_from_path(file_path, first_page=1, last_page=1, dpi=150)
                if not images:
                    return {
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "doc_type": doc_type,
                        "status": "error",
                        "error": "Could not convert PDF to image",
                        "extracted_data": {}
                    }
                # Convert PIL image to base64
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='PNG')
                image_bytes = img_byte_arr.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                logging.info(f"Converted PDF to image for OCR processing")
            except Exception as pdf_err:
                logging.error(f"PDF conversion failed: {pdf_err}")
                return {
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "doc_type": doc_type,
                    "status": "error",
                    "error": f"PDF conversion failed: {str(pdf_err)}",
                    "extracted_data": {}
                }
        else:
            # Read image and convert to base64
            async with aiofiles.open(file_path, 'rb') as f:
                image_bytes = await f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine prompt based on document type
        if doc_type == "pan_card":
            prompt = """Extract the following information from this PAN card image:
1. PAN Number (10 character alphanumeric)
2. Full Name
3. Father's Name
4. Date of Birth

Return ONLY a JSON object with keys: pan_number, name, father_name, date_of_birth
If any field is not visible, use null."""

        elif doc_type == "cancelled_cheque":
            prompt = """Extract the following information from this cancelled cheque image:
1. Account Number
2. IFSC Code
3. Bank Name
4. Branch Name
5. Account Holder Name

Return ONLY a JSON object with keys: account_number, ifsc_code, bank_name, branch_name, account_holder_name
If any field is not visible, use null."""

        elif doc_type == "cml_copy":
            prompt = """Extract the following information from this CML (Client Master List) copy:
1. DP ID (Depository Participant ID - usually starts with IN followed by numbers, e.g., IN301629)
2. Client ID (the client-specific ID number that follows the DP ID)
3. Full DP Client ID (combination of DP ID + Client ID, e.g., IN301629-10242225 or the complete identifier shown)
4. Client Name
5. PAN Number
6. Email Address
7. Mobile Number
8. Address (full address including city, state)
9. Pin Code
10. Bank Name
11. Bank Account Number
12. IFSC Code
13. Branch Name

Return ONLY a JSON object with keys: dp_id, client_id, full_dp_client_id, client_name, pan_number, email, mobile, address, pin_code, bank_name, account_number, ifsc_code, branch_name
If any field is not visible, use null. For full_dp_client_id, combine dp_id and client_id if they appear separately."""
        else:
            prompt = "Extract all text and relevant information from this document. Return as JSON."

        # Use AI for OCR
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4()}",
            system_message="You are an OCR specialist. Extract information from documents accurately. IMPORTANT: Always respond with ONLY valid JSON, no explanations, no markdown code blocks, just the raw JSON object."
        ).with_model("openai", "gpt-4o")
        
        # Create ImageContent for vision processing
        image_content = ImageContent(image_base64=image_base64)
        user_message = UserMessage(text=prompt, file_contents=[image_content])
        
        response = await chat.send_message(user_message)
        
        # Parse the response as JSON
        import json
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            # Remove markdown code blocks
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line if it's closing ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned = '\n'.join(lines).strip()
            # Handle case where it starts with 'json' without backticks
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            
            # Try to find JSON object in the response
            if not cleaned.startswith('{'):
                # Look for JSON object in the text
                start_idx = cleaned.find('{')
                end_idx = cleaned.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
            
            extracted_data = json.loads(cleaned)
            logging.info(f"OCR extracted data: {extracted_data}")
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse OCR JSON response: {e}. Raw: {response[:200]}")
            extracted_data = {"raw_text": response, "parse_error": str(e)}
        
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "processed",
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        logging.error(f"OCR processing failed: {str(e)}")
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "error",
            "error": str(e),
            "extracted_data": {}
        }

def generate_otc_ucc() -> str:
    """Generate unique OTC UCC code"""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = str(uuid.uuid4())[:8].upper()
    return f"OTC{date_part}{unique_part}"

async def update_inventory(stock_id: str):
    """Recalculate weighted average and available quantity for a stock"""
    # Get all purchases for this stock
    purchases = await db.purchases.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    # Get all bookings (sales) for this stock
    bookings = await db.bookings.find({"stock_id": stock_id}, {"_id": 0}).to_list(10000)
    
    # Calculate total purchased
    total_purchased_qty = sum(p["quantity"] for p in purchases)
    total_purchased_value = sum(p["quantity"] * p["price_per_unit"] for p in purchases)
    
    # Calculate total sold
    total_sold_qty = sum(b["quantity"] for b in bookings)
    
    # Calculate weighted average
    weighted_avg = total_purchased_value / total_purchased_qty if total_purchased_qty > 0 else 0
    available_qty = total_purchased_qty - total_sold_qty
    
    # Get stock details
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    
    # Update or insert inventory
    inventory_data = {
        "stock_id": stock_id,
        "stock_symbol": stock["symbol"] if stock else "Unknown",
        "stock_name": stock["name"] if stock else "Unknown",
        "available_quantity": available_qty,
        "weighted_avg_price": weighted_avg,
        "total_value": available_qty * weighted_avg
    }
    
    await db.inventory.update_one(
        {"stock_id": stock_id},
        {"$set": inventory_data},
        upsert=True
    )
    
    return inventory_data

# Startup event to seed admin user
@app.on_event("startup")
async def seed_admin_user():
    """Create default admin user if no admin exists"""
    try:
        # Check if any admin user exists (role 1 or 2)
        admin_exists = await db.users.find_one({"role": {"$lte": 2}}, {"_id": 0})
        if not admin_exists:
            admin_id = str(uuid.uuid4())
            admin_doc = {
                "id": admin_id,
                "email": "admin@privity.com",
                "password": hash_password("Admin@123"),
                "name": "Admin User",
                "role": 1,  # PE Desk - full access
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(admin_doc)
            logging.info("Default admin user created: admin@privity.com")
        else:
            logging.info("Admin user already exists, skipping seed")
    except Exception as e:
        logging.error(f"Error seeding admin user: {e}")

# Auth Routes
@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, request: Request = None):
    # Check email domain restriction
    email_domain = user_data.email.split('@')[-1].lower()
    if email_domain not in ALLOWED_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400, 
            detail=f"Registration is restricted to employees with @smifs.com email addresses"
        )
    
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(user_data.password)
    
    # Default role is Employee (4) for smifs.com domain
    user_role = 4  # Employee
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hashed_pw,
        "name": user_data.name,
        "role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Create audit log
    await create_audit_log(
        action="USER_REGISTER",
        entity_type="user",
        entity_id=user_id,
        user_id=user_id,
        user_name=user_data.name,
        user_role=user_role,
        entity_name=user_data.name,
        details={"email": user_data.email, "role": user_role}
    )
    
    token = create_token(user_id, user_data.email)
    user_response = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_role,
        role_name=ROLES.get(user_role, "Employee"),
        created_at=user_doc["created_at"]
    )
    
    return TokenResponse(token=token, user=user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create audit log for login
    await create_audit_log(
        action="USER_LOGIN",
        entity_type="user",
        entity_id=user["id"],
        user_id=user["id"],
        user_name=user["name"],
        user_role=user.get("role", 5),
        entity_name=user["name"]
    )
    
    token = create_token(user["id"], user["email"])
    user_response = User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user.get("role", 5),
        role_name=ROLES.get(user.get("role", 5), "Viewer"),
        created_at=user["created_at"]
    )
    
    return TokenResponse(token=token, user=user_response)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user.get("role", 5),
        role_name=ROLES.get(current_user.get("role", 5), "Viewer"),
        created_at=current_user["created_at"]
    )

@api_router.post("/auth/forgot-password")
async def forgot_password(data: PasswordResetRequest):
    """Request password reset OTP"""
    user = await db.users.find_one({"email": data.email.lower()})
    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, an OTP has been sent"}
    
    # Check rate limiting
    recent_otps = await db.password_resets.count_documents({
        "email": data.email.lower(),
        "created_at": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=OTP_EXPIRY_MINUTES)}
    })
    
    if recent_otps >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again later.")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP
    await db.password_resets.insert_one({
        "id": str(uuid.uuid4()),
        "email": data.email.lower(),
        "otp": otp,
        "attempts": 0,
        "used": False,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
    })
    
    # Send email
    await send_otp_email(data.email, otp, user["name"])
    
    return {"message": "If the email exists, an OTP has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(data: PasswordResetVerify, request: Request):
    """Reset password with OTP verification"""
    # Find valid OTP
    otp_record = await db.password_resets.find_one({
        "email": data.email.lower(),
        "otp": data.otp,
        "used": False,
        "expires_at": {"$gte": datetime.now(timezone.utc)}
    })
    
    if not otp_record:
        # Increment attempts for any matching unused OTP
        await db.password_resets.update_many(
            {"email": data.email.lower(), "used": False},
            {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    # Check attempts
    if otp_record.get("attempts", 0) >= OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")
    
    # Mark OTP as used
    await db.password_resets.update_one(
        {"id": otp_record["id"]},
        {"$set": {"used": True}}
    )
    
    # Update password
    user = await db.users.find_one({"email": data.email.lower()})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed = bcrypt.hashpw(data.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await db.users.update_one(
        {"email": data.email.lower()},
        {"$set": {"hashed_password": hashed}}
    )
    
    # Create audit log
    await create_audit_log(
        "USER_PASSWORD_RESET", "user", user["id"], user["id"], user["name"], user["role"],
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Password reset successfully"}

# User Management Routes
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_users")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(**{**u, "role_name": ROLES.get(u.get("role", 5), "Viewer")}) for u in users]

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: int, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_users")
    
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User role updated successfully"}

# Client Routes with Document Upload
@api_router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Employees can only create clients (not vendors)
    if user_role == 4 and client_data.is_vendor:
        raise HTTPException(status_code=403, detail="Employees cannot create vendors")
    
    # Check permission based on whether it's a client or vendor
    if client_data.is_vendor:
        check_permission(current_user, "manage_vendors")
    else:
        if user_role == 4:
            check_permission(current_user, "create_clients")
        else:
            check_permission(current_user, "manage_clients")
    
    client_id = str(uuid.uuid4())
    # Generate unique OTC UCC code
    otc_ucc = f"OTC{datetime.now().strftime('%Y%m%d')}{client_id[:8].upper()}"
    
    # Determine approval status - employees need approval
    is_active = True
    approval_status = "approved"
    if user_role == 4 and not client_data.is_vendor:
        is_active = False
        approval_status = "pending"
    
    client_doc = {
        "id": client_id,
        "otc_ucc": otc_ucc,
        **client_data.model_dump(),
        "bank_accounts": [acc.model_dump() if hasattr(acc, 'model_dump') else acc for acc in client_data.bank_accounts] if client_data.bank_accounts else [],
        "is_active": is_active,
        "approval_status": approval_status,
        "documents": [],
        "mapped_employee_id": current_user["id"] if user_role == 4 else None,
        "mapped_employee_name": current_user["name"] if user_role == 4 else None,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.clients.insert_one(client_doc)
    
    # Send email notification
    if client_data.email and is_active:
        await send_email(
            client_data.email,
            "Welcome to Share Booking System",
            f"<p>Dear {client_data.name},</p><p>Your account has been created successfully.</p>"
        )
    
    # Real-time notification for pending approval
    if approval_status == "pending":
        # Notify managers (roles 1, 2, 3) about pending client
        await notify_roles(
            [1, 2, 3],
            "client_pending",
            "New Client Pending Approval",
            f"Client '{client_data.name}' created by {current_user['name']} is pending approval",
            {"client_id": client_id, "client_name": client_data.name}
        )
    
    return Client(**{k: v for k, v in client_doc.items() if k != "user_id"})

@api_router.put("/clients/{client_id}/approve")
async def approve_client(client_id: str, approve: bool = True, current_user: dict = Depends(get_current_user)):
    """Approve or reject a client created by employee"""
    check_permission(current_user, "approve_clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {
        "is_active": approve,
        "approval_status": "approved" if approve else "rejected"
    }
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    # Send notification email if approved
    if approve and client.get("email"):
        await send_email(
            client["email"],
            "Account Approved - Share Booking System",
            f"<p>Dear {client['name']},</p><p>Your account has been approved and is now active.</p>"
        )
    
    # Real-time notification to creator
    if client.get("created_by"):
        notif_type = "client_approved" if approve else "client_rejected"
        notif_title = f"Client {'Approved' if approve else 'Rejected'}"
        notif_message = f"Client '{client['name']}' has been {'approved' if approve else 'rejected'} by {current_user['name']}"
        await create_notification(
            client["created_by"],
            notif_type,
            notif_title,
            notif_message,
            {"client_id": client_id, "client_name": client["name"]}
        )
    
    return {"message": f"Client {'approved' if approve else 'rejected'} successfully"}

@api_router.post("/clients/{client_id}/bank-account")
async def add_bank_account(client_id: str, bank_account: BankAccount, current_user: dict = Depends(get_current_user)):
    """Add another bank account to client"""
    check_permission(current_user, "manage_clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"bank_accounts": bank_account.model_dump()}}
    )
    
    return {"message": "Bank account added successfully"}

@api_router.post("/clients/{client_id}/documents")
async def upload_client_document(
    client_id: str,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Allow both manage_clients (managers+) and create_clients (employees) to upload docs
    user_role = current_user.get("role", 5)
    if user_role == 4:
        check_permission(current_user, "create_clients")
        # Employees can only upload docs to their own clients
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only upload documents to your own clients")
    else:
        check_permission(current_user, "manage_clients")
    
    # Verify client exists (only if not already verified for employees)
    if user_role != 4:
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
    
    # Create client directory
    client_dir = UPLOAD_DIR / client_id
    client_dir.mkdir(exist_ok=True)
    
    # Save file
    file_ext = Path(file.filename).suffix
    filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
    file_path = client_dir / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Process OCR
    ocr_data = await process_document_ocr(str(file_path), doc_type)
    
    # Update client document record
    doc_record = {
        "doc_type": doc_type,
        "filename": filename,
        "file_path": str(file_path),
        "upload_date": datetime.now(timezone.utc).isoformat(),
        "ocr_data": ocr_data
    }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$push": {"documents": doc_record}}
    )
    
    return {"message": "Document uploaded successfully", "document": doc_record}

@api_router.get("/clients/{client_id}/documents/{filename}")
async def download_client_document(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    file_path = UPLOAD_DIR / client_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    
    return FileResponse(file_path, filename=filename)

@api_router.post("/ocr/preview")
async def ocr_preview(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Process OCR on a document without saving - for auto-fill preview"""
    # Save temporarily
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    file_ext = Path(file.filename).suffix
    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    temp_path = temp_dir / temp_filename
    
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Process OCR
        ocr_data = await process_document_ocr(str(temp_path), doc_type)
        return ocr_data
    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()

@api_router.get("/clients/{client_id}/documents/{filename}/ocr")
async def get_document_ocr(
    client_id: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Get OCR data for a specific document"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Find the document
    document = None
    for doc in client.get("documents", []):
        if doc["filename"] == filename:
            document = doc
            break
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "filename": filename,
        "doc_type": document.get("doc_type"),
        "ocr_data": document.get("ocr_data"),
        "upload_date": document.get("upload_date")
    }

@api_router.put("/clients/{client_id}/employee-mapping")
async def update_client_employee_mapping(
    client_id: str,
    employee_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Map or unmap a client to an employee (admin only)"""
    # Only PE Desk and Zonal Manager can map/unmap clients
    if current_user.get("role", 5) > 2:
        raise HTTPException(status_code=403, detail="Only admins can map/unmap clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = {}
    
    if employee_id:
        # Map to employee
        employee = await db.users.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        update_data = {
            "mapped_employee_id": employee_id,
            "mapped_employee_name": employee.get("name")
        }
    else:
        # Unmap (set to None)
        update_data = {
            "mapped_employee_id": None,
            "mapped_employee_name": None
        }
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": update_data}
    )
    
    action = "mapped" if employee_id else "unmapped"
    return {"message": f"Client successfully {action}", "client_id": client_id, **update_data}

@api_router.get("/employees", response_model=List[User])
async def get_employees(current_user: dict = Depends(get_current_user)):
    """Get list of employees for mapping"""
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return [User(
        id=u["id"],
        email=u["email"],
        name=u["name"],
        role=u["role"],
        role_name=ROLES.get(u["role"], "Unknown"),
        created_at=u["created_at"]
    ) for u in users]

@api_router.get("/clients", response_model=List[Client])
async def get_clients(
    search: Optional[str] = None,
    is_vendor: Optional[bool] = None,
    pending_approval: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    user_role = current_user.get("role", 5)
    user_id = current_user.get("id")
    
    # Employee restrictions
    if user_role == 4:
        # Employees cannot see vendors
        if is_vendor == True:
            raise HTTPException(status_code=403, detail="Employees cannot access vendors")
        query["is_vendor"] = False
        # Employees can only see their own clients
        query["$or"] = [
            {"mapped_employee_id": user_id},
            {"created_by": user_id}
        ]
    else:
        # Vendor filter for non-employees
        if is_vendor is not None:
            query["is_vendor"] = is_vendor
    
    # Pending approval filter (for admins)
    if pending_approval and user_role <= 3:
        query["approval_status"] = "pending"
    
    # Search filter
    if search:
        search_query = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"pan_number": {"$regex": search, "$options": "i"}},
            {"otc_ucc": {"$regex": search, "$options": "i"}}
        ]
        if "$or" in query:
            # Combine with existing $or
            existing_or = query.pop("$or")
            query["$and"] = [{"$or": existing_or}, {"$or": search_query}]
        else:
            query["$or"] = search_query
    
    clients = await db.clients.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    return clients

@api_router.get("/clients/pending-approval", response_model=List[Client])
async def get_pending_clients(current_user: dict = Depends(get_current_user)):
    """Get clients pending approval (admin only)"""
    check_permission(current_user, "approve_clients")
    
    clients = await db.clients.find(
        {"approval_status": "pending", "is_vendor": False},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    return clients

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id}, {"_id": 0, "user_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientCreate, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_clients")
    
    result = await db.clients.update_one(
        {"id": client_id},
        {"$set": client_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    updated_client = await db.clients.find_one({"id": client_id}, {"_id": 0, "user_id": 0})
    return updated_client

@api_router.put("/clients/{client_id}/employee-mapping")
async def update_client_employee_mapping(
    client_id: str,
    employee_id: str,
    employee_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Map a client to an employee"""
    check_permission(current_user, "manage_clients")
    
    result = await db.clients.update_one(
        {"id": client_id},
        {"$set": {
            "mapped_employee_id": employee_id,
            "mapped_employee_name": employee_name
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {"message": "Employee mapping updated successfully"}

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_clients")
    
    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

# Bulk Upload Routes
@api_router.post("/clients/bulk-upload")
async def bulk_upload_clients(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_clients")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["name", "pan_number", "dp_id"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        clients_created = 0
        for _, row in df.iterrows():
            client_id = str(uuid.uuid4())
            # Generate unique OTC UCC code
            otc_ucc = f"OTC{datetime.now().strftime('%Y%m%d')}{client_id[:8].upper()}"
            
            client_doc = {
                "id": client_id,
                "otc_ucc": otc_ucc,
                "name": str(row["name"]),
                "email": str(row.get("email", "")) if pd.notna(row.get("email")) else None,
                "phone": str(row.get("phone", "")) if pd.notna(row.get("phone")) else None,
                "pan_number": str(row["pan_number"]),
                "dp_id": str(row["dp_id"]),
                "bank_name": str(row.get("bank_name", "")) if pd.notna(row.get("bank_name")) else None,
                "account_number": str(row.get("account_number", "")) if pd.notna(row.get("account_number")) else None,
                "ifsc_code": str(row.get("ifsc_code", "")) if pd.notna(row.get("ifsc_code")) else None,
                "is_vendor": bool(row.get("is_vendor", False)) if pd.notna(row.get("is_vendor")) else False,
                "documents": [],
                "mapped_employee_id": None,
                "mapped_employee_name": None,
                "user_id": current_user["id"],
                "created_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.clients.insert_one(client_doc)
            clients_created += 1
        
        return {"message": f"Successfully uploaded {clients_created} clients"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

# Stock Routes (PE Desk Only for creation/edit)
@api_router.post("/stocks", response_model=Stock)
async def create_stock(stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Only PE Desk can create stocks
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can add stocks")
    
    stock_id = str(uuid.uuid4())
    stock_doc = {
        "id": stock_id,
        **stock_data.model_dump(),
        "user_id": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stocks.insert_one(stock_doc)
    
    # Create audit log
    await create_audit_log(
        action="STOCK_CREATE",
        entity_type="stock",
        entity_id=stock_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=stock_data.symbol,
        details={"symbol": stock_data.symbol, "name": stock_data.name, "isin": stock_data.isin_number}
    )
    
    return Stock(**{k: v for k, v in stock_doc.items() if k != "user_id"})

@api_router.get("/stocks", response_model=List[Stock])
async def get_stocks(search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    
    if search:
        query["$or"] = [
            {"symbol": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}}
        ]
    
    stocks = await db.stocks.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    return stocks

@api_router.get("/stocks/{stock_id}", response_model=Stock)
async def get_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "user_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@api_router.put("/stocks/{stock_id}", response_model=Stock)
async def update_stock(stock_id: str, stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Only PE Desk can update stocks
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can update stocks")
    
    result = await db.stocks.update_one(
        {"id": stock_id},
        {"$set": stock_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    updated_stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0, "user_id": 0})
    return updated_stock

@api_router.delete("/stocks/{stock_id}")
async def delete_stock(stock_id: str, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Only PE Desk can delete stocks
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete stocks")
    
    result = await db.stocks.delete_one({"id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}

@api_router.post("/stocks/bulk-upload")
async def bulk_upload_stocks(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Only PE Desk can bulk upload stocks
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can bulk upload stocks")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["symbol", "name"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        stocks_created = 0
        for _, row in df.iterrows():
            stock_id = str(uuid.uuid4())
            stock_doc = {
                "id": stock_id,
                "symbol": str(row["symbol"]).upper(),
                "name": str(row["name"]),
                "exchange": str(row.get("exchange", "")) if pd.notna(row.get("exchange")) else None,
                "user_id": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.stocks.insert_one(stock_doc)
            stocks_created += 1
        
        return {"message": f"Successfully uploaded {stocks_created} stocks"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

# Corporate Actions Routes (PE Desk Only)
@api_router.post("/corporate-actions", response_model=CorporateAction)
async def create_corporate_action(
    action_data: CorporateActionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a corporate action (Stock Split or Bonus) - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can create corporate actions")
    
    # Verify stock exists
    stock = await db.stocks.find_one({"id": action_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Validate action type
    if action_data.action_type not in ["stock_split", "bonus"]:
        raise HTTPException(status_code=400, detail="Action type must be 'stock_split' or 'bonus'")
    
    # For stock split, new_face_value is required
    if action_data.action_type == "stock_split" and not action_data.new_face_value:
        raise HTTPException(status_code=400, detail="New face value is required for stock split")
    
    action_id = str(uuid.uuid4())
    action_doc = {
        "id": action_id,
        "stock_id": action_data.stock_id,
        "action_type": action_data.action_type,
        "ratio_from": action_data.ratio_from,
        "ratio_to": action_data.ratio_to,
        "new_face_value": action_data.new_face_value,
        "record_date": action_data.record_date,
        "status": "pending",
        "applied_at": None,
        "notes": action_data.notes,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.corporate_actions.insert_one(action_doc)
    
    # Create audit log
    await create_audit_log(
        action="CORPORATE_ACTION_CREATE",
        entity_type="corporate_action",
        entity_id=action_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol']} - {action_data.action_type}",
        details={
            "stock_symbol": stock["symbol"],
            "action_type": action_data.action_type,
            "ratio": f"{action_data.ratio_from}:{action_data.ratio_to}",
            "record_date": action_data.record_date
        }
    )
    
    return CorporateAction(
        **action_doc,
        stock_symbol=stock["symbol"],
        stock_name=stock["name"]
    )

@api_router.get("/corporate-actions", response_model=List[CorporateAction])
async def get_corporate_actions(
    stock_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get corporate actions - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view corporate actions")
    
    query = {}
    if stock_id:
        query["stock_id"] = stock_id
    if status:
        query["status"] = status
    
    actions = await db.corporate_actions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich with stock details
    stock_ids = list(set(a["stock_id"] for a in actions))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    enriched = []
    for a in actions:
        stock = stock_map.get(a["stock_id"], {})
        enriched.append(CorporateAction(
            **a,
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown")
        ))
    
    return enriched

@api_router.put("/corporate-actions/{action_id}/apply")
async def apply_corporate_action(
    action_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Apply a corporate action on record date - adjusts buy prices in inventory"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can apply corporate actions")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    if action["status"] == "applied":
        raise HTTPException(status_code=400, detail="Corporate action already applied")
    
    # Check if today is the record date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if action["record_date"] != today:
        raise HTTPException(
            status_code=400, 
            detail=f"Corporate action can only be applied on record date ({action['record_date']}). Today is {today}"
        )
    
    stock_id = action["stock_id"]
    ratio_from = action["ratio_from"]
    ratio_to = action["ratio_to"]
    action_type = action["action_type"]
    
    # Calculate adjustment factor
    if action_type == "stock_split":
        # Stock split: If 1:2 split, new price = old price / 2
        adjustment_factor = ratio_from / ratio_to
    else:  # bonus
        # Bonus: If 1:1 bonus, shares double, price halves
        # ratio_from:ratio_to means for every ratio_from shares, you get ratio_to bonus
        adjustment_factor = ratio_from / (ratio_from + ratio_to)
    
    # Update inventory weighted average price
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if inventory:
        new_avg_price = inventory["weighted_avg_price"] * adjustment_factor
        
        # For bonus/split, quantity increases
        if action_type == "stock_split":
            new_quantity = int(inventory["available_quantity"] * (ratio_to / ratio_from))
        else:  # bonus
            bonus_shares = int(inventory["available_quantity"] * (ratio_to / ratio_from))
            new_quantity = inventory["available_quantity"] + bonus_shares
        
        await db.inventory.update_one(
            {"stock_id": stock_id},
            {"$set": {
                "weighted_avg_price": new_avg_price,
                "available_quantity": new_quantity
            }}
        )
    
    # Update all purchases for this stock (historical record)
    await db.purchases.update_many(
        {"stock_id": stock_id},
        {"$mul": {"price_per_unit": adjustment_factor}}
    )
    
    # Update all bookings for this stock
    await db.bookings.update_many(
        {"stock_id": stock_id},
        {"$mul": {"buying_price": adjustment_factor}}
    )
    
    # Update stock face value if stock split
    if action_type == "stock_split" and action.get("new_face_value"):
        await db.stocks.update_one(
            {"id": stock_id},
            {"$set": {"face_value": action["new_face_value"]}}
        )
    
    # Mark action as applied
    await db.corporate_actions.update_one(
        {"id": action_id},
        {"$set": {
            "status": "applied",
            "applied_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Create audit log
    stock = await db.stocks.find_one({"id": stock_id}, {"_id": 0})
    await create_audit_log(
        action="CORPORATE_ACTION_APPLY",
        entity_type="corporate_action",
        entity_id=action_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol'] if stock else 'Unknown'} - {action_type}",
        details={
            "adjustment_factor": adjustment_factor,
            "action_type": action_type,
            "ratio": f"{ratio_from}:{ratio_to}"
        }
    )
    
    return {
        "message": f"Corporate action applied successfully. Prices adjusted by factor {adjustment_factor:.4f}",
        "adjustment_factor": adjustment_factor
    }

@api_router.delete("/corporate-actions/{action_id}")
async def delete_corporate_action(action_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a pending corporate action - PE Desk only"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can delete corporate actions")
    
    action = await db.corporate_actions.find_one({"id": action_id}, {"_id": 0})
    if not action:
        raise HTTPException(status_code=404, detail="Corporate action not found")
    
    if action["status"] == "applied":
        raise HTTPException(status_code=400, detail="Cannot delete applied corporate action")
    
    await db.corporate_actions.delete_one({"id": action_id})
    return {"message": "Corporate action deleted successfully"}

# Purchase Routes (from Vendors)
@api_router.post("/purchases", response_model=Purchase)
async def create_purchase(purchase_data: PurchaseCreate, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Employees cannot create purchases
    if user_role == 4:
        raise HTTPException(status_code=403, detail="Employees cannot create vendor purchases")
    
    check_permission(current_user, "manage_purchases")
    
    # Verify vendor is a client with is_vendor=True
    vendor = await db.clients.find_one({"id": purchase_data.vendor_id, "is_vendor": True}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Verify stock exists
    stock = await db.stocks.find_one({"id": purchase_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    purchase_id = str(uuid.uuid4())
    total_amount = purchase_data.quantity * purchase_data.price_per_unit
    
    purchase_doc = {
        "id": purchase_id,
        **purchase_data.model_dump(),
        "total_amount": total_amount,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.purchases.insert_one(purchase_doc)
    
    # Update inventory
    await update_inventory(purchase_data.stock_id)
    
    # Send email notification to vendor
    if vendor.get("email"):
        await send_email(
            vendor["email"],
            "Purchase Order Confirmation",
            f"<p>Dear {vendor['name']},</p><p>A purchase order has been created for {purchase_data.quantity} units of {stock['symbol']}.</p>"
        )
    
    return Purchase(
        id=purchase_id,
        vendor_id=purchase_data.vendor_id,
        vendor_name=vendor["name"],
        stock_id=purchase_data.stock_id,
        stock_symbol=stock["symbol"],
        quantity=purchase_data.quantity,
        price_per_unit=purchase_data.price_per_unit,
        total_amount=total_amount,
        purchase_date=purchase_data.purchase_date,
        notes=purchase_data.notes,
        created_at=purchase_doc["created_at"],
        created_by=current_user["id"]
    )

@api_router.get("/purchases", response_model=List[Purchase])
async def get_purchases(
    vendor_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user.get("role", 5)
    
    # Employees cannot view purchase history
    if user_role == 4:
        raise HTTPException(status_code=403, detail="Employees cannot access vendor purchase history")
    
    check_permission(current_user, "manage_purchases")
    
    query = {}
    if vendor_id:
        query["vendor_id"] = vendor_id
    if stock_id:
        query["stock_id"] = stock_id
    
    purchases = await db.purchases.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    # Enrich with vendor and stock details
    if purchases:
        vendor_ids = list(set(p["vendor_id"] for p in purchases))
        stock_ids = list(set(p["stock_id"] for p in purchases))
        
        vendors = await db.clients.find({"id": {"$in": vendor_ids}}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
        
        vendor_map = {v["id"]: v for v in vendors}
        stock_map = {s["id"]: s for s in stocks}
        
        enriched_purchases = []
        for p in purchases:
            vendor = vendor_map.get(p["vendor_id"])
            stock = stock_map.get(p["stock_id"])
            enriched_purchases.append(Purchase(
                **p,
                vendor_name=vendor["name"] if vendor else "Unknown",
                stock_symbol=stock["symbol"] if stock else "Unknown"
            ))
        
        return enriched_purchases
    
    return []

# Inventory Routes
@api_router.get("/inventory", response_model=List[Inventory])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    inventory_items = await db.inventory.find({}, {"_id": 0}).to_list(1000)
    return inventory_items

@api_router.get("/inventory/{stock_id}", response_model=Inventory)
async def get_stock_inventory(stock_id: str, current_user: dict = Depends(get_current_user)):
    inventory = await db.inventory.find_one({"stock_id": stock_id}, {"_id": 0})
    if not inventory:
        # Try to calculate if not exists
        inventory = await update_inventory(stock_id)
    return inventory

# Booking Routes
@api_router.post("/bookings", response_model=Booking)
async def create_booking(booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    user_role = current_user.get("role", 5)
    
    # Employees can create bookings
    if user_role == 4:
        check_permission(current_user, "create_bookings")
    else:
        check_permission(current_user, "manage_bookings")
    
    # Verify client exists and is active
    client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check if client is active (approved)
    if not client.get("is_active", True):
        raise HTTPException(status_code=400, detail="Client is pending approval and cannot be used for bookings")
    
    # Employees can only create bookings for their own clients
    if user_role == 4:
        if client.get("mapped_employee_id") != current_user["id"] and client.get("created_by") != current_user["id"]:
            raise HTTPException(status_code=403, detail="You can only create bookings for your own clients")
    
    # Verify stock exists
    stock = await db.stocks.find_one({"id": booking_data.stock_id}, {"_id": 0})
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Get inventory to check availability and weighted average
    inventory = await db.inventory.find_one({"stock_id": booking_data.stock_id}, {"_id": 0})
    
    if not inventory or inventory["available_quantity"] < booking_data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient inventory. Available: {inventory['available_quantity'] if inventory else 0}"
        )
    
    # Employees MUST use weighted average as buying price (cannot edit)
    if user_role == 4:
        buying_price = inventory["weighted_avg_price"]
    else:
        buying_price = booking_data.buying_price if booking_data.buying_price else inventory["weighted_avg_price"]
    
    booking_id = str(uuid.uuid4())
    
    # All bookings require PE Desk approval before inventory adjustment
    booking_doc = {
        "id": booking_id,
        "client_id": booking_data.client_id,
        "stock_id": booking_data.stock_id,
        "quantity": booking_data.quantity,
        "buying_price": buying_price,
        "selling_price": booking_data.selling_price,
        "booking_date": booking_data.booking_date,
        "status": booking_data.status,
        "approval_status": "pending",  # Requires PE Desk approval
        "approved_by": None,
        "approved_at": None,
        "notes": booking_data.notes,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_by_name": current_user["name"],
        "created_by_role": user_role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.insert_one(booking_doc)
    
    # DO NOT update inventory yet - wait for PE Desk approval
    # await update_inventory(booking_data.stock_id)
    
    # Create audit log
    await create_audit_log(
        action="BOOKING_CREATE",
        entity_type="booking",
        entity_id=booking_id,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=user_role,
        entity_name=f"{stock['symbol']} - {client['name']}",
        details={
            "client_id": booking_data.client_id,
            "client_name": client["name"],
            "stock_id": booking_data.stock_id,
            "stock_symbol": stock["symbol"],
            "quantity": booking_data.quantity,
            "buying_price": buying_price,
            "selling_price": booking_data.selling_price
        }
    )
    
    # Send detailed email notification to client with CC to user
    if client.get("email"):
        email_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #064E3B;">Booking Order Created</h2>
            <p>Dear {client['name']},</p>
            <p>A new booking order has been created in our system with the following details:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Order ID</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_id[:8].upper()}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Client OTC UCC</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{client.get('otc_ucc', 'N/A')}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol']} - {stock['name']}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_data.quantity}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Buying Price</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{buying_price:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Total Value</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">₹{(buying_price * booking_data.quantity):,.2f}</td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Booking Date</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking_data.booking_date}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Status</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><span style="color: #f59e0b;">Pending Approval</span></td>
                </tr>
                <tr style="background-color: #f3f4f6;">
                    <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Created By</strong></td>
                    <td style="padding: 10px; border: 1px solid #e5e7eb;">{current_user['name']}</td>
                </tr>
            </table>
            
            <p style="color: #6b7280; font-size: 14px;">This order is pending approval from PE Desk. You will receive another notification once approved.</p>
            
            <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
        </div>
        """
        
        await send_email(
            client["email"],
            f"Booking Order Created - {stock['symbol']} | {booking_id[:8].upper()}",
            email_body,
            cc_email=current_user.get("email")  # CC to the user who created booking
        )
    
    # Real-time notification to PE Desk about pending booking
    await notify_roles(
        [1],  # PE Desk only
        "booking_pending",
        "New Booking Pending Approval",
        f"Booking for '{client['name']}' - {stock['symbol']} x {booking_data.quantity} is pending approval",
        {"booking_id": booking_id, "client_name": client["name"], "stock_symbol": stock["symbol"]}
    )
    
    return Booking(**{k: v for k, v in booking_doc.items() if k not in ["user_id", "created_by_name"]})

@api_router.put("/bookings/{booking_id}/approve")
async def approve_booking(
    booking_id: str,
    approve: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a booking for inventory adjustment (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    # Only PE Desk (role 1) can approve bookings
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can approve bookings for inventory adjustment")
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.get("approval_status") != "pending":
        raise HTTPException(status_code=400, detail="Booking already processed")
    
    update_data = {
        "approval_status": "approved" if approve else "rejected",
        "approved_by": current_user["id"],
        "approved_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})
    
    # If approved, now update inventory
    if approve:
        await update_inventory(booking["stock_id"])
        
        # Create audit log
        await create_audit_log(
            action="BOOKING_APPROVE",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        # Send approval notification to client
        client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        creator = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
        
        if client and client.get("email"):
            email_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #10b981;">Booking Order Approved ✓</h2>
                <p>Dear {client['name']},</p>
                <p>Your booking order has been <strong style="color: #10b981;">APPROVED</strong> and inventory has been adjusted.</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background-color: #f3f4f6;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Stock</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{stock['symbol'] if stock else 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Quantity</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{booking['quantity']}</td>
                    </tr>
                    <tr style="background-color: #f3f4f6;">
                        <td style="padding: 10px; border: 1px solid #e5e7eb;"><strong>Approved By</strong></td>
                        <td style="padding: 10px; border: 1px solid #e5e7eb;">{current_user['name']} (PE Desk)</td>
                    </tr>
                </table>
                
                <p>Best regards,<br><strong>SMIFS Share Booking System</strong></p>
            </div>
            """
            await send_email(
                client["email"],
                f"Booking Approved - {stock['symbol'] if stock else 'N/A'} | {booking_id[:8].upper()}",
                email_body,
                cc_email=creator.get("email") if creator else None
            )
        
        # Real-time notification to booking creator
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_approved",
                "Booking Approved",
                f"Your booking for '{stock['symbol'] if stock else 'N/A'}' has been approved",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    else:
        # Create audit log for rejection
        await create_audit_log(
            action="BOOKING_REJECT",
            entity_type="booking",
            entity_id=booking_id,
            user_id=current_user["id"],
            user_name=current_user["name"],
            user_role=user_role,
            details={"stock_id": booking["stock_id"], "quantity": booking["quantity"]}
        )
        
        # Real-time notification to booking creator for rejection
        stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
        if booking.get("created_by"):
            await create_notification(
                booking["created_by"],
                "booking_rejected",
                "Booking Rejected",
                f"Your booking for '{stock['symbol'] if stock else 'N/A'}' has been rejected",
                {"booking_id": booking_id, "stock_symbol": stock['symbol'] if stock else None}
            )
    
    return {"message": f"Booking {'approved' if approve else 'rejected'} successfully"}

@api_router.get("/bookings/pending-approval", response_model=List[BookingWithDetails])
async def get_pending_bookings(current_user: dict = Depends(get_current_user)):
    """Get bookings pending approval (PE Desk only)"""
    user_role = current_user.get("role", 5)
    
    if user_role != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can view pending bookings")
    
    bookings = await db.bookings.find(
        {"approval_status": "pending"},
        {"_id": 0, "user_id": 0}
    ).to_list(1000)
    
    if not bookings:
        return []
    
    # Enrich with client and stock details
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    enriched = []
    for b in bookings:
        client = client_map.get(b["client_id"], {})
        stock = stock_map.get(b["stock_id"], {})
        enriched.append(BookingWithDetails(
            **b,
            client_name=client.get("name", "Unknown"),
            stock_symbol=stock.get("symbol", "Unknown"),
            stock_name=stock.get("name", "Unknown")
        ))
    
    return enriched

@api_router.get("/bookings", response_model=List[BookingWithDetails])
async def get_bookings(
    client_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    
    # Role-based filtering
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query["created_by"] = current_user["id"]
    
    if client_id:
        query["client_id"] = client_id
    if stock_id:
        query["stock_id"] = stock_id
    if status:
        query["status"] = status
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    if not bookings:
        return []
    
    # Batch fetch related data
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    user_ids = list(set(b["created_by"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    user_map = {u["id"]: u for u in users}
    
    enriched_bookings = []
    for booking in bookings:
        client = client_map.get(booking["client_id"])
        stock = stock_map.get(booking["stock_id"])
        user = user_map.get(booking["created_by"])
        
        profit_loss = None
        if booking.get("selling_price") and booking["status"] == "closed":
            profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
        
        enriched_bookings.append(BookingWithDetails(
            **booking,
            client_name=client["name"] if client else "Unknown",
            stock_symbol=stock["symbol"] if stock else "Unknown",
            stock_name=stock["name"] if stock else "Unknown",
            created_by_name=user["name"] if user else "Unknown",
            profit_loss=profit_loss
        ))
    
    return enriched_bookings

@api_router.get("/bookings/{booking_id}", response_model=BookingWithDetails)
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0, "user_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    client = await db.clients.find_one({"id": booking["client_id"]}, {"_id": 0})
    stock = await db.stocks.find_one({"id": booking["stock_id"]}, {"_id": 0})
    user = await db.users.find_one({"id": booking["created_by"]}, {"_id": 0})
    
    profit_loss = None
    if booking.get("selling_price") and booking["status"] == "closed":
        profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
    
    return BookingWithDetails(
        **booking,
        client_name=client["name"] if client else "Unknown",
        stock_symbol=stock["symbol"] if stock else "Unknown",
        stock_name=stock["name"] if stock else "Unknown",
        created_by_name=user["name"] if user else "Unknown",
        profit_loss=profit_loss
    )

@api_router.put("/bookings/{booking_id}", response_model=Booking)
async def update_booking(booking_id: str, booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_bookings")
    
    # Get old booking to check status change
    old_booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not old_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    result = await db.bookings.update_one(
        {"id": booking_id},
        {"$set": booking_data.model_dump()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update inventory
    await update_inventory(booking_data.stock_id)
    
    # Send email if status changed
    if old_booking["status"] != booking_data.status:
        client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
        if client and client.get("email"):
            await send_email(
                client["email"],
                "Booking Status Updated",
                f"<p>Dear {client['name']},</p><p>Your booking status has been updated to: {booking_data.status}</p>"
            )
    
    updated_booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0, "user_id": 0})
    return updated_booking

@api_router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_bookings")
    
    result = await db.bookings.delete_one({"id": booking_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Booking deleted successfully"}

@api_router.post("/bookings/bulk-upload")
async def bulk_upload_bookings(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_bookings")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        required_columns = ["client_id", "stock_id", "quantity", "booking_date"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"CSV must contain columns: {', '.join(required_columns)}")
        
        bookings_created = 0
        for _, row in df.iterrows():
            # Get inventory for weighted average
            inventory = await db.inventory.find_one({"stock_id": str(row["stock_id"])}, {"_id": 0})
            buying_price = float(row.get("buying_price", inventory["weighted_avg_price"] if inventory else 0))
            
            booking_id = str(uuid.uuid4())
            booking_doc = {
                "id": booking_id,
                "client_id": str(row["client_id"]),
                "stock_id": str(row["stock_id"]),
                "quantity": int(row["quantity"]),
                "buying_price": buying_price,
                "selling_price": float(row["selling_price"]) if pd.notna(row.get("selling_price")) else None,
                "booking_date": str(row["booking_date"]),
                "status": str(row.get("status", "open")),
                "notes": str(row.get("notes", "")) if pd.notna(row.get("notes")) else None,
                "user_id": current_user["id"],
                "created_by": current_user["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.bookings.insert_one(booking_doc)
            await update_inventory(str(row["stock_id"]))
            bookings_created += 1
        
        return {"message": f"Successfully uploaded {bookings_created} bookings"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

# Dashboard & Analytics
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    query_filter = {}
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query_filter = {"created_by": current_user["id"]}
    
    total_clients = await db.clients.count_documents({})
    total_vendors = await db.clients.count_documents({"is_vendor": True})
    total_stocks = await db.stocks.count_documents({})
    total_bookings = await db.bookings.count_documents(query_filter)
    open_bookings = await db.bookings.count_documents({**query_filter, "status": "open"})
    closed_bookings = await db.bookings.count_documents({**query_filter, "status": "closed"})
    total_purchases = await db.purchases.count_documents({})
    
    # Calculate total P&L
    bookings = await db.bookings.find({**query_filter, "status": "closed"}, {"_id": 0}).to_list(1000)
    total_profit_loss = sum(
        (b["selling_price"] - b["buying_price"]) * b["quantity"]
        for b in bookings if b.get("selling_price")
    )
    
    # Calculate total inventory value
    inventory_items = await db.inventory.find({}, {"_id": 0}).to_list(1000)
    total_inventory_value = sum(item.get("total_value", 0) for item in inventory_items)
    
    return DashboardStats(
        total_clients=total_clients,
        total_vendors=total_vendors,
        total_stocks=total_stocks,
        total_bookings=total_bookings,
        open_bookings=open_bookings,
        closed_bookings=closed_bookings,
        total_profit_loss=total_profit_loss,
        total_inventory_value=total_inventory_value,
        total_purchases=total_purchases
    )

@api_router.get("/dashboard/analytics")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get analytics data for charts"""
    query_filter = {}
    if current_user.get("role", 5) >= 3:
        if "view_all" not in ROLE_PERMISSIONS.get(current_user.get("role", 5), []):
            query_filter = {"created_by": current_user["id"]}
    
    # P&L Trend over time (last 12 months)
    bookings = await db.bookings.find({**query_filter, "status": "closed"}, {"_id": 0}).to_list(10000)
    
    # Group by month
    monthly_pnl = {}
    for booking in bookings:
        if booking.get("selling_price"):
            booking_date = datetime.fromisoformat(booking["booking_date"]).strftime("%Y-%m")
            pnl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            monthly_pnl[booking_date] = monthly_pnl.get(booking_date, 0) + pnl
    
    # Top performing stocks
    stock_performance = {}
    for booking in bookings:
        if booking.get("selling_price"):
            stock_id = booking["stock_id"]
            pnl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            if stock_id not in stock_performance:
                stock_performance[stock_id] = {"pnl": 0, "quantity": 0}
            stock_performance[stock_id]["pnl"] += pnl
            stock_performance[stock_id]["quantity"] += booking["quantity"]
    
    # Enrich with stock names
    stock_ids = list(stock_performance.keys())
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    top_stocks = [
        {
            "stock_symbol": stock_map.get(stock_id, {}).get("symbol", "Unknown"),
            "pnl": data["pnl"],
            "quantity": data["quantity"]
        }
        for stock_id, data in sorted(stock_performance.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]
    ]
    
    return {
        "monthly_pnl": [{"month": k, "pnl": v} for k, v in sorted(monthly_pnl.items())],
        "top_stocks": top_stocks
    }

# Audit Logs API
@api_router.get("/audit-logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get audit logs (admin only)"""
    user_role = current_user.get("role", 5)
    
    if user_role > 2:
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")
    
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs

@api_router.get("/audit-logs/stats")
async def get_audit_stats(current_user: dict = Depends(get_current_user)):
    """Get audit log statistics"""
    user_role = current_user.get("role", 5)
    
    if user_role > 2:
        raise HTTPException(status_code=403, detail="Only admins can view audit stats")
    
    total_logs = await db.audit_logs.count_documents({})
    
    # Get counts by action type
    pipeline = [
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    action_counts = await db.audit_logs.aggregate(pipeline).to_list(100)
    
    return {
        "total_logs": total_logs,
        "by_action": {item["_id"]: item["count"] for item in action_counts}
    }

# Client Portfolio
@api_router.get("/clients/{client_id}/portfolio", response_model=ClientPortfolio)
async def get_client_portfolio(client_id: str, current_user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    bookings = await db.bookings.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
    
    total_bookings = len(bookings)
    open_bookings = sum(1 for b in bookings if b["status"] == "open")
    closed_bookings = sum(1 for b in bookings if b["status"] == "closed")
    
    total_profit_loss = sum(
        (b["selling_price"] - b["buying_price"]) * b["quantity"]
        for b in bookings if b.get("selling_price") and b["status"] == "closed"
    )
    
    # Enrich bookings
    if bookings:
        stock_ids = list(set(b["stock_id"] for b in bookings))
        user_ids = list(set(b["created_by"] for b in bookings))
        
        stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
        users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0}).to_list(1000)
        
        stock_map = {s["id"]: s for s in stocks}
        user_map = {u["id"]: u for u in users}
        
        enriched_bookings = []
        for booking in bookings:
            stock = stock_map.get(booking["stock_id"])
            user = user_map.get(booking["created_by"])
            
            profit_loss = None
            if booking.get("selling_price") and booking["status"] == "closed":
                profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            
            enriched_bookings.append(BookingWithDetails(
                **booking,
                client_name=client["name"],
                stock_symbol=stock["symbol"] if stock else "Unknown",
                stock_name=stock["name"] if stock else "Unknown",
                created_by_name=user["name"] if user else "Unknown",
                profit_loss=profit_loss
            ))
    else:
        enriched_bookings = []
    
    return ClientPortfolio(
        client_id=client_id,
        client_name=client["name"],
        total_bookings=total_bookings,
        open_bookings=open_bookings,
        closed_bookings=closed_bookings,
        total_profit_loss=total_profit_loss,
        bookings=enriched_bookings
    )

# Advanced Reports
@api_router.get("/reports/pnl")
async def get_pnl_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    client_id: Optional[str] = None,
    stock_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    check_permission(current_user, "view_reports")
    
    query = {}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    if client_id:
        query["client_id"] = client_id
    if stock_id:
        query["stock_id"] = stock_id
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    if not bookings:
        return []
    
    # Batch fetch related data
    client_ids = list(set(b["client_id"] for b in bookings))
    stock_ids = list(set(b["stock_id"] for b in bookings))
    
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    
    client_map = {c["id"]: c for c in clients}
    stock_map = {s["id"]: s for s in stocks}
    
    report = []
    for booking in bookings:
        client = client_map.get(booking["client_id"])
        stock = stock_map.get(booking["stock_id"])
        
        profit_loss = None
        if booking.get("selling_price") and booking["status"] == "closed":
            profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
        
        report.append({
            "booking_id": booking["id"],
            "client_name": client["name"] if client else "Unknown",
            "stock_symbol": stock["symbol"] if stock else "Unknown",
            "stock_name": stock["name"] if stock else "Unknown",
            "quantity": booking["quantity"],
            "buying_price": booking["buying_price"],
            "selling_price": booking.get("selling_price"),
            "booking_date": booking["booking_date"],
            "status": booking["status"],
            "profit_loss": profit_loss
        })
    
    return report

@api_router.get("/reports/export/excel")
async def export_excel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    check_permission(current_user, "view_reports")
    
    query = {}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "P&L Report"
    
    # Headers
    headers = ["Client", "Stock Symbol", "Stock Name", "Quantity", "Buying Price", "Selling Price", "Date", "Status", "P&L"]
    ws.append(headers)
    
    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="064E3B", end_color="064E3B", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    if bookings:
        client_ids = list(set(b["client_id"] for b in bookings))
        stock_ids = list(set(b["stock_id"] for b in bookings))
        
        clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
        
        client_map = {c["id"]: c for c in clients}
        stock_map = {s["id"]: s for s in stocks}
        
        for booking in bookings:
            client = client_map.get(booking["client_id"])
            stock = stock_map.get(booking["stock_id"])
            
            profit_loss = ""
            if booking.get("selling_price") and booking["status"] == "closed":
                profit_loss = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
            
            ws.append([
                client["name"] if client else "Unknown",
                stock["symbol"] if stock else "Unknown",
                stock["name"] if stock else "Unknown",
                booking["quantity"],
                booking["buying_price"],
                booking.get("selling_price") or "",
                booking["booking_date"],
                booking["status"],
                profit_loss
            ])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=pnl_report.xlsx"}
    )

@api_router.get("/reports/export/pdf")
async def export_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    check_permission(current_user, "view_reports")
    
    query = {}
    if start_date:
        query["booking_date"] = {"$gte": start_date}
    if end_date:
        if "booking_date" in query:
            query["booking_date"]["$lte"] = end_date
        else:
            query["booking_date"] = {"$lte": end_date}
    
    bookings = await db.bookings.find(query, {"_id": 0, "user_id": 0}).to_list(1000)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#064E3B'),
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Profit & Loss Report", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    data = [["Client", "Stock", "Qty", "Buy Price", "Sell Price", "Status", "P&L"]]
    
    if bookings:
        client_ids = list(set(b["client_id"] for b in bookings))
        stock_ids = list(set(b["stock_id"] for b in bookings))
        
        clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
        
        client_map = {c["id"]: c for c in clients}
        stock_map = {s["id"]: s for s in stocks}
        
        for booking in bookings:
            client = client_map.get(booking["client_id"])
            stock = stock_map.get(booking["stock_id"])
            
            profit_loss = ""
            if booking.get("selling_price") and booking["status"] == "closed":
                pl = (booking["selling_price"] - booking["buying_price"]) * booking["quantity"]
                profit_loss = f"₹{pl:,.2f}"
            
            data.append([
                client["name"] if client else "Unknown",
                stock["symbol"] if stock else "Unknown",
                str(booking["quantity"]),
                f"₹{booking['buying_price']:,.2f}",
                f"₹{booking.get('selling_price', 0):,.2f}" if booking.get('selling_price') else "-",
                booking["status"].upper(),
                profit_loss
            ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#064E3B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=pnl_report.pdf"}
    )

# Notification Routes
@api_router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Get user notifications"""
    query = {"user_id": current_user["id"]}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications

@api_router.get("/notifications/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    return {"count": count}

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark notification as read"""
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    result = await db.notifications.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}

# ============== Email Templates Routes (PE Desk Only) ==============
@api_router.get("/email-templates")
async def get_email_templates(current_user: dict = Depends(get_current_user)):
    """Get all email templates (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    
    # Add default templates if not in database
    from config import DEFAULT_EMAIL_TEMPLATES
    existing_keys = {t["key"] for t in templates}
    
    for key, default_data in DEFAULT_EMAIL_TEMPLATES.items():
        if key not in existing_keys:
            templates.append({
                "id": key,
                "key": key,
                **default_data,
                "is_active": True,
                "updated_at": None,
                "updated_by": None
            })
    
    return templates

@api_router.get("/email-templates/{template_key}")
async def get_email_template(template_key: str, current_user: dict = Depends(get_current_user)):
    """Get specific email template"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        from config import DEFAULT_EMAIL_TEMPLATES
        default = DEFAULT_EMAIL_TEMPLATES.get(template_key)
        if default:
            return {
                "id": template_key,
                "key": template_key,
                **default,
                "is_active": True,
                "updated_at": None,
                "updated_by": None
            }
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@api_router.put("/email-templates/{template_key}")
async def update_email_template(
    template_key: str,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update email template (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    # Check if template exists in database
    existing = await db.email_templates.find_one({"key": template_key})
    
    update_data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    if subject is not None:
        update_data["subject"] = subject
    if body is not None:
        update_data["body"] = body
    if is_active is not None:
        update_data["is_active"] = is_active
    
    if existing:
        await db.email_templates.update_one(
            {"key": template_key},
            {"$set": update_data}
        )
    else:
        # Create from default
        from config import DEFAULT_EMAIL_TEMPLATES
        default = DEFAULT_EMAIL_TEMPLATES.get(template_key)
        if not default:
            raise HTTPException(status_code=404, detail="Template not found")
        
        new_template = {
            "id": str(uuid.uuid4()),
            "key": template_key,
            **default,
            **update_data
        }
        await db.email_templates.insert_one(new_template)
    
    # Create audit log
    await create_audit_log(
        action="EMAIL_TEMPLATE_UPDATE",
        entity_type="email_template",
        entity_id=template_key,
        user_id=current_user["id"],
        user_name=current_user["name"],
        user_role=current_user.get("role", 5),
        details={"template_key": template_key, "updates": list(update_data.keys())}
    )
    
    return {"message": "Template updated successfully"}

@api_router.post("/email-templates/{template_key}/reset")
async def reset_email_template(template_key: str, current_user: dict = Depends(get_current_user)):
    """Reset email template to default (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    from config import DEFAULT_EMAIL_TEMPLATES
    default = DEFAULT_EMAIL_TEMPLATES.get(template_key)
    if not default:
        raise HTTPException(status_code=404, detail="Default template not found")
    
    await db.email_templates.delete_one({"key": template_key})
    
    return {"message": "Template reset to default"}

@api_router.post("/email-templates/{template_key}/preview")
async def preview_email_template(
    template_key: str,
    variables: Dict[str, str] = {},
    current_user: dict = Depends(get_current_user)
):
    """Preview email template with sample variables"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can manage email templates")
    
    template = await db.email_templates.find_one({"key": template_key}, {"_id": 0})
    
    if not template:
        from config import DEFAULT_EMAIL_TEMPLATES
        default = DEFAULT_EMAIL_TEMPLATES.get(template_key)
        if not default:
            raise HTTPException(status_code=404, detail="Template not found")
        template = default
    
    # Replace variables
    subject = template["subject"]
    body = template["body"]
    
    for key, value in variables.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
        body = body.replace(f"{{{{{key}}}}}", str(value))
    
    return {
        "subject": subject,
        "body": body,
        "variables": template.get("variables", [])
    }

# ============== Advanced Analytics Routes (PE Desk Only) ==============
@api_router.get("/analytics/summary")
async def get_analytics_summary(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive analytics summary (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Get all closed bookings
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    # Calculate totals
    total_revenue = sum(b.get("selling_price", 0) * b.get("quantity", 0) for b in bookings)
    total_cost = sum(b.get("buying_price", 0) * b.get("quantity", 0) for b in bookings)
    total_profit = total_revenue - total_cost
    
    # Get clients count
    clients_count = await db.clients.count_documents({"is_vendor": False, "is_active": True})
    
    avg_booking_value = total_revenue / len(bookings) if bookings else 0
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_profit": round(total_profit, 2),
        "total_bookings": len(bookings),
        "total_clients": clients_count,
        "avg_booking_value": round(avg_booking_value, 2),
        "profit_margin": round(profit_margin, 2)
    }

@api_router.get("/analytics/stock-performance")
async def get_stock_performance(
    days: int = 30,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get stock performance analytics (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    stock_stats = {}
    for booking in bookings:
        stock_id = booking.get("stock_id")
        if not stock_id:
            continue
        
        if stock_id not in stock_stats:
            stock_stats[stock_id] = {"total_qty": 0, "total_revenue": 0, "total_cost": 0}
        
        qty = booking.get("quantity", 0)
        stock_stats[stock_id]["total_qty"] += qty
        stock_stats[stock_id]["total_revenue"] += booking.get("selling_price", 0) * qty
        stock_stats[stock_id]["total_cost"] += booking.get("buying_price", 0) * qty
    
    # Get stock details
    stock_ids = list(stock_stats.keys())
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    result = []
    for stock_id, stats in stock_stats.items():
        stock = stock_map.get(stock_id, {})
        profit = stats["total_revenue"] - stats["total_cost"]
        margin = (profit / stats["total_revenue"] * 100) if stats["total_revenue"] > 0 else 0
        
        result.append({
            "stock_id": stock_id,
            "stock_symbol": stock.get("symbol", "Unknown"),
            "stock_name": stock.get("name", "Unknown"),
            "sector": stock.get("sector", "Unknown"),
            "total_quantity_sold": stats["total_qty"],
            "total_revenue": round(stats["total_revenue"], 2),
            "total_cost": round(stats["total_cost"], 2),
            "profit_loss": round(profit, 2),
            "profit_margin": round(margin, 2)
        })
    
    result.sort(key=lambda x: x["profit_loss"], reverse=True)
    return result[:limit]

@api_router.get("/analytics/employee-performance")
async def get_employee_performance(
    days: int = 30,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get employee performance analytics (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    emp_stats = {}
    for booking in bookings:
        user_id = booking.get("created_by")
        if not user_id:
            continue
        
        if user_id not in emp_stats:
            emp_stats[user_id] = {
                "total_bookings": 0,
                "total_value": 0,
                "total_profit": 0,
                "client_ids": set()
            }
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        emp_stats[user_id]["total_bookings"] += 1
        emp_stats[user_id]["total_value"] += revenue
        emp_stats[user_id]["total_profit"] += revenue - cost
        emp_stats[user_id]["client_ids"].add(booking.get("client_id"))
    
    # Get user details
    user_ids = list(emp_stats.keys())
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "hashed_password": 0}).to_list(1000)
    user_map = {u["id"]: u for u in users}
    
    result = []
    for user_id, stats in emp_stats.items():
        user = user_map.get(user_id, {})
        result.append({
            "user_id": user_id,
            "user_name": user.get("name", "Unknown"),
            "role": user.get("role", 5),
            "role_name": ROLES.get(user.get("role", 5), "Unknown"),
            "total_bookings": stats["total_bookings"],
            "total_value": round(stats["total_value"], 2),
            "total_profit": round(stats["total_profit"], 2),
            "clients_count": len(stats["client_ids"])
        })
    
    result.sort(key=lambda x: x["total_profit"], reverse=True)
    return result[:limit]

@api_router.get("/analytics/daily-trend")
async def get_daily_trend(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get daily booking trend (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    result = []
    
    for i in range(days, -1, -1):
        date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        date_start = f"{date}T00:00:00"
        date_end = f"{date}T23:59:59"
        
        # Get bookings for this day
        bookings = await db.bookings.find({
            "created_at": {"$gte": date_start, "$lte": date_end},
            "approval_status": "approved"
        }, {"_id": 0}).to_list(1000)
        
        # Get new clients for this day
        new_clients = await db.clients.count_documents({
            "created_at": {"$gte": date_start, "$lte": date_end},
            "is_vendor": False
        })
        
        bookings_value = sum(b.get("selling_price", 0) * b.get("quantity", 0) for b in bookings)
        profit_loss = sum(
            (b.get("selling_price", 0) - b.get("buying_price", 0)) * b.get("quantity", 0)
            for b in bookings if b.get("status") == "closed"
        )
        
        result.append({
            "date": date,
            "bookings_count": len(bookings),
            "bookings_value": round(bookings_value, 2),
            "profit_loss": round(profit_loss, 2),
            "new_clients": new_clients
        })
    
    return result

@api_router.get("/analytics/sector-distribution")
async def get_sector_distribution(current_user: dict = Depends(get_current_user)):
    """Get booking distribution by sector (PE Desk only)"""
    if current_user.get("role") != 1:
        raise HTTPException(status_code=403, detail="Only PE Desk can access advanced analytics")
    
    bookings = await db.bookings.find(
        {"status": "closed", "approval_status": "approved"},
        {"_id": 0}
    ).to_list(10000)
    
    # Get all stocks with sectors
    stock_ids = list(set(b.get("stock_id") for b in bookings if b.get("stock_id")))
    stocks = await db.stocks.find({"id": {"$in": stock_ids}}, {"_id": 0}).to_list(1000)
    stock_map = {s["id"]: s for s in stocks}
    
    sector_stats = {}
    for booking in bookings:
        stock = stock_map.get(booking.get("stock_id"), {})
        sector = stock.get("sector") or "Unknown"
        
        if sector not in sector_stats:
            sector_stats[sector] = {"bookings_count": 0, "total_value": 0, "total_profit": 0}
        
        qty = booking.get("quantity", 0)
        revenue = booking.get("selling_price", 0) * qty
        cost = booking.get("buying_price", 0) * qty
        
        sector_stats[sector]["bookings_count"] += 1
        sector_stats[sector]["total_value"] += revenue
        sector_stats[sector]["total_profit"] += revenue - cost
    
    result = [
        {
            "sector": sector,
            **stats,
            "total_value": round(stats["total_value"], 2),
            "total_profit": round(stats["total_profit"], 2)
        }
        for sector, stats in sector_stats.items()
    ]
    
    result.sort(key=lambda x: x["total_value"], reverse=True)
    return result

# WebSocket endpoint for real-time notifications
@app.websocket("/api/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for real-time notifications"""
    try:
        # Verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload["user_id"]
        
        await ws_manager.connect(websocket, user_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, user_id)
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
    except jwt.InvalidTokenError:
        await websocket.close(code=4002, reason="Invalid token")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await websocket.close(code=1011)

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
