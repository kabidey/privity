"""
Pydantic models for the application
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any

# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: int = 4

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

# Bank Account Model
class BankAccount(BaseModel):
    bank_name: str
    account_number: str
    ifsc_code: str
    branch_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    source: str = "manual"

# Client Models
class ClientDocument(BaseModel):
    doc_type: str
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
    otc_ucc: str
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
    is_active: bool = True
    approval_status: str = "approved"
    documents: List[ClientDocument] = []
    created_at: str
    created_by: str
    created_by_role: int = 5
    mapped_employee_id: Optional[str] = None
    mapped_employee_name: Optional[str] = None

# Stock Models
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
    action_type: str
    ratio_from: int
    ratio_to: int
    record_date: str
    new_face_value: Optional[float] = None
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
    record_date: str
    new_face_value: Optional[float] = None
    notes: Optional[str] = None
    applied: bool = False
    created_at: str
    created_by: str

# Purchase Models
class PurchaseCreate(BaseModel):
    vendor_id: str
    stock_id: str
    quantity: int
    price_per_unit: float
    purchase_date: Optional[str] = None

class Purchase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    vendor_id: str
    vendor_name: str
    stock_id: str
    stock_symbol: str
    quantity: int
    price_per_unit: float
    total_value: float
    purchase_date: str
    created_at: str

# Booking Models
class BookingCreate(BaseModel):
    client_id: str
    stock_id: str
    quantity: int
    price_per_unit: float
    status: str = "pending"

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    client_id: str
    client_name: str
    stock_id: str
    stock_symbol: str
    quantity: int
    price_per_unit: float
    total_value: float
    status: str
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
    price_per_unit: float
    total_value: float
    status: str
    created_at: str
    closed_at: Optional[str] = None
    created_by: str
    created_by_name: str
    buy_price: float
    profit_loss: float
    profit_loss_percent: float
    approval_status: str = "approved"

# Inventory Models
class Inventory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    stock_id: str
    stock_symbol: str
    stock_name: str
    total_quantity: int
    available_quantity: int
    booked_quantity: int
    weighted_avg_price: float
    total_value: float

# Audit Log Model
class AuditLog(BaseModel):
    id: str
    action: str
    action_description: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = None
    user_id: str
    user_name: str
    user_role: int
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    timestamp: str

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

# Client Portfolio Models
class ClientHolding(BaseModel):
    stock_id: str
    stock_symbol: str
    stock_name: str
    quantity: int
    avg_buy_price: float
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float

class ClientPortfolio(BaseModel):
    client_id: str
    client_name: str
    total_invested: float
    total_current_value: float
    total_profit_loss: float
    total_profit_loss_percent: float
    holdings: List[ClientHolding]
