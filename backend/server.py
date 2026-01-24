from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
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

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

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
    2: ["view_all", "manage_users", "manage_clients", "manage_stocks", "manage_bookings", "manage_purchases", "manage_vendors", "view_reports", "approve_clients"],  # Zonal Manager
    3: ["view_all", "manage_clients", "manage_bookings", "manage_purchases", "manage_vendors", "view_reports", "approve_clients"],  # Manager
    4: ["view_own", "create_bookings", "view_clients", "create_clients"],  # Employee - no vendor access, can only see own clients
    5: ["view_own"]  # Viewer - read only
}

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: int = 5  # Default to Viewer

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

class Stock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    symbol: str
    name: str
    exchange: Optional[str] = None
    created_at: str

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
    notes: Optional[str] = None
    created_at: str
    created_by: str

class BookingWithDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    client_name: str
    stock_id: str
    stock_symbol: str
    stock_name: str
    quantity: int
    buying_price: float
    selling_price: Optional[float] = None
    booking_date: str
    status: str
    notes: Optional[str] = None
    profit_loss: Optional[float] = None
    created_at: str
    created_by: str
    created_by_name: str

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

async def send_email(to_email: str, subject: str, body: str):
    """Send email via MS Exchange"""
    if not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logging.warning("Email credentials not configured")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logging.info(f"Email sent to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")

async def process_document_ocr(file_path: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """Process document OCR using AI vision model"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        
        # Read and encode the file
        file_ext = file_path.lower().split('.')[-1]
        
        # For PDF, we'd need to convert to image first - for now handle images
        if file_ext == 'pdf':
            # Return basic info for PDF - full OCR would need pdf2image
            return {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "doc_type": doc_type,
                "status": "pdf_uploaded",
                "extracted_data": {"note": "PDF uploaded - manual verification required"}
            }
        
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
1. DP ID (Depository Participant ID)
2. Client ID
3. Client Name
4. PAN Number
5. Email Address
6. Mobile Number
7. Address (full address)
8. Pin Code
9. Bank Name
10. Bank Account Number
11. IFSC Code
12. Branch Name

Return ONLY a JSON object with keys: dp_id, client_id, client_name, pan_number, email, mobile, address, pin_code, bank_name, account_number, ifsc_code, branch_name
If any field is not visible, use null."""
        else:
            prompt = "Extract all text and relevant information from this document. Return as JSON."

        # Use AI for OCR
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4()}",
            system_message="You are an OCR specialist. Extract information from documents accurately. Always respond with valid JSON only, no markdown."
        ).with_model("openai", "gpt-4o")
        
        image_content = ImageContent(image_base64=image_base64)
        user_message = UserMessage(text=prompt, image_contents=[image_content])
        
        response = await chat.send_message(user_message)
        
        # Parse the response as JSON
        import json
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else cleaned
                cleaned = cleaned.rsplit('```', 1)[0] if '```' in cleaned else cleaned
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            extracted_data = json.loads(cleaned)
        except json.JSONDecodeError:
            extracted_data = {"raw_text": response}
        
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
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(user_data.password)
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hashed_pw,
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, user_data.email)
    user_response = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        role_name=ROLES.get(user_data.role, "Unknown"),
        created_at=user_doc["created_at"]
    )
    
    return TokenResponse(token=token, user=user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
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
    check_permission(current_user, "manage_clients")
    
    # Verify client exists
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

# Stock Routes
@api_router.post("/stocks", response_model=Stock)
async def create_stock(stock_data: StockCreate, current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_stocks")
    
    stock_id = str(uuid.uuid4())
    stock_doc = {
        "id": stock_id,
        **stock_data.model_dump(),
        "user_id": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.stocks.insert_one(stock_doc)
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
    check_permission(current_user, "manage_stocks")
    
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
    check_permission(current_user, "manage_stocks")
    
    result = await db.stocks.delete_one({"id": stock_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not found")
    return {"message": "Stock deleted successfully"}

@api_router.post("/stocks/bulk-upload")
async def bulk_upload_stocks(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    check_permission(current_user, "manage_stocks")
    
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
    check_permission(current_user, "manage_bookings")
    
    # Verify client exists
    client = await db.clients.find_one({"id": booking_data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
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
    
    # Use weighted average as buying price if not provided
    buying_price = booking_data.buying_price if booking_data.buying_price else inventory["weighted_avg_price"]
    
    booking_id = str(uuid.uuid4())
    booking_doc = {
        "id": booking_id,
        "client_id": booking_data.client_id,
        "stock_id": booking_data.stock_id,
        "quantity": booking_data.quantity,
        "buying_price": buying_price,
        "selling_price": booking_data.selling_price,
        "booking_date": booking_data.booking_date,
        "status": booking_data.status,
        "notes": booking_data.notes,
        "user_id": current_user["id"],
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bookings.insert_one(booking_doc)
    
    # Update inventory
    await update_inventory(booking_data.stock_id)
    
    # Send email notification to client
    if client.get("email"):
        await send_email(
            client["email"],
            "Booking Confirmation",
            f"<p>Dear {client['name']},</p><p>Your booking for {booking_data.quantity} units of {stock['symbol']} has been created.</p>"
        )
    
    return Booking(**{k: v for k, v in booking_doc.items() if k != "user_id"})

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
