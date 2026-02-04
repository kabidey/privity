"""
Pydantic models for the application
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any


# ============== Audit Log Models ==============
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


# ============== User Models ==============
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    pan_number: Optional[str] = None  # Required for non-superadmin users


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    pan_number: Optional[str] = None  # PAN number for conflict checks
    role: int
    role_name: str
    permissions: List[str] = []  # User's effective permissions from their role
    created_at: str
    agreement_accepted: Optional[bool] = False
    agreement_accepted_at: Optional[str] = None
    # Hierarchy fields
    hierarchy_level: Optional[int] = 1  # 1=Employee, 2=Manager, 3=Zonal Head, 4=Regional Manager, 5=Business Head
    hierarchy_level_name: Optional[str] = "Employee"
    reports_to: Optional[str] = None  # User ID of the manager
    reports_to_name: Optional[str] = None  # Manager's name for display


class TokenResponse(BaseModel):
    token: str
    user: User


# ============== Password Reset Models ==============
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetVerify(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# ============== Notification Model ==============
class Notification(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: str


# ============== Client Models ==============
class BankAccount(BaseModel):
    bank_name: str
    account_number: str
    ifsc_code: str
    branch_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    source: str = "manual"  # manual, cml_copy, cancelled_cheque


class ClientDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    doc_type: str  # pan_card, cml_copy, cancelled_cheque
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_id: Optional[str] = None  # GridFS file ID
    gridfs_id: Optional[str] = None  # Deprecated - use file_id
    upload_date: Optional[str] = None
    uploaded_at: Optional[str] = None
    uploaded_by: Optional[str] = None
    ocr_data: Optional[Dict[str, Any]] = None
    ocr_status: Optional[str] = None
    ocr_processed_at: Optional[str] = None


class ClientCreate(BaseModel):
    name: str
    email: Optional[str] = None  # Primary email (from CML)
    email_secondary: Optional[str] = None  # Secondary email (PE Desk can add)
    email_tertiary: Optional[str] = None  # Third email (PE Desk can add)
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: str
    dp_id: Optional[str] = None  # Optional for vendors, required for clients
    dp_type: str = "outside"  # "smifs" or "outside"
    trading_ucc: Optional[str] = None  # Required if dp_type is "smifs"
    address: Optional[str] = None
    pin_code: Optional[str] = None
    bank_accounts: List[BankAccount] = []
    is_vendor: bool = False
    is_proprietor: bool = False  # Flag for proprietorship entities
    has_name_mismatch: bool = False  # Flag if name mismatch was detected during creation


class Client(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    otc_ucc: str  # Unique OTC UCC code
    name: str
    email: Optional[str] = None  # Primary email (from CML)
    email_secondary: Optional[str] = None  # Secondary email
    email_tertiary: Optional[str] = None  # Third email
    phone: Optional[str] = None
    mobile: Optional[str] = None
    pan_number: str
    dp_id: Optional[str] = None  # Optional for vendors
    dp_type: str = "outside"  # "smifs" or "outside"
    trading_ucc: Optional[str] = None  # Required if dp_type is "smifs"
    address: Optional[str] = None
    pin_code: Optional[str] = None
    bank_accounts: List[BankAccount] = []
    is_vendor: bool = False
    is_active: bool = True
    approval_status: str = "approved"  # pending, approved, rejected
    # Suspension fields
    is_suspended: bool = False
    suspension_reason: Optional[str] = None
    suspended_by: Optional[str] = None
    suspended_by_name: Optional[str] = None
    suspended_at: Optional[str] = None
    documents: List[ClientDocument] = []
    created_at: str
    created_by: Optional[str] = None
    created_by_role: int = 5
    mapped_employee_id: Optional[str] = None
    mapped_employee_name: Optional[str] = None
    mapped_employee_email: Optional[str] = None  # Email for CC in client communications
    is_proprietor: bool = False  # Flag for proprietorship entities
    has_name_mismatch: bool = False  # Flag if name mismatch was detected during creation
    bank_proof_url: Optional[str] = None  # Bank proof document for proprietors with name mismatch
    bank_proof_uploaded_by: Optional[str] = None  # Who uploaded the bank proof
    bank_proof_uploaded_at: Optional[str] = None  # When the bank proof was uploaded
    # Clone tracking
    is_cloned: bool = False  # True if this was cloned from another client/vendor
    cloned_from_id: Optional[str] = None  # Original client/vendor ID
    cloned_from_type: Optional[str] = None  # "client" or "vendor"
    # Booking permission (computed field)
    can_book: bool = True  # Whether current user can create bookings for this client


# ============== Stock Models ==============
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


# ============== Corporate Actions Models ==============
class CorporateActionCreate(BaseModel):
    stock_id: str
    action_type: str  # stock_split, bonus, dividend, rights_issue, buyback
    ratio_from: Optional[int] = None  # Not required for dividend
    ratio_to: Optional[int] = None  # Not required for dividend
    dividend_amount: Optional[float] = None  # Amount per share for dividend
    dividend_type: Optional[str] = None  # interim, final, special
    new_face_value: Optional[float] = None
    record_date: str
    ex_date: Optional[str] = None  # Ex-dividend date
    payment_date: Optional[str] = None  # Dividend payment date
    notes: Optional[str] = None


class CorporateAction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    stock_id: str
    stock_symbol: Optional[str] = None  # Made optional for backwards compatibility
    stock_name: Optional[str] = None
    action_type: str
    ratio_from: Optional[int] = None
    ratio_to: Optional[int] = None
    dividend_amount: Optional[float] = None
    dividend_type: Optional[str] = None
    new_face_value: Optional[float] = None
    record_date: str
    ex_date: Optional[str] = None
    payment_date: Optional[str] = None
    status: str = "pending"  # pending, applied, notified
    applied_at: Optional[str] = None
    notified_clients: Optional[int] = 0
    notes: Optional[str] = None
    created_at: str
    created_by: str


# ============== Purchase Models ==============
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
    price_per_share: Optional[float] = None
    price_per_unit: Optional[float] = None
    total_amount: float
    purchase_date: Optional[str] = None
    purchase_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    created_by: str
    created_by_name: Optional[str] = None
    payments: Optional[List[dict]] = []
    total_paid: float = 0
    payment_status: str = "pending"
    status: Optional[str] = "pending"
    dp_status: Optional[str] = None
    dp_type: Optional[str] = None
    dp_receivable_at: Optional[str] = None
    dp_received_at: Optional[str] = None


# ============== Inventory Model ==============
class Inventory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    stock_id: str
    stock_symbol: str
    stock_name: str
    available_quantity: int  # Total available (not blocked)
    blocked_quantity: int = 0  # Blocked for approved bookings pending transfer
    weighted_avg_price: float  # Calculated only from non-blocked stock
    total_value: float
    landing_price: Optional[float] = None  # LP - Landing Price (set by PE Desk)
    lp_total_value: Optional[float] = None  # Total value based on LP (for PE Level view)


# ============== Payment Models ==============
class PaymentTranche(BaseModel):
    tranche_number: int  # 1 to 4
    amount: float
    payment_date: str
    recorded_by: str
    recorded_at: str
    notes: Optional[str] = None
    proof_url: Optional[str] = None


class PaymentTrancheCreate(BaseModel):
    amount: float
    payment_date: str
    notes: Optional[str] = None
    proof_url: Optional[str] = None


# ============== Booking Models ==============
class BookingCreate(BaseModel):
    client_id: str
    stock_id: str
    quantity: int
    buying_price: Optional[float] = None
    selling_price: Optional[float] = None
    booking_date: str
    status: str = "open"
    notes: Optional[str] = None
    booking_type: str = "client"  # "client", "team", or "own"
    insider_form_uploaded: bool = False
    # Referral Partner
    referral_partner_id: Optional[str] = None
    rp_revenue_share_percent: Optional[float] = None  # Revenue share percentage for RP
    # Employee Revenue Share (reduced by RP share)
    employee_revenue_share_percent: Optional[float] = None  # Employee's share after RP deduction
    base_employee_share_percent: float = 100.0  # Default employee share before RP deduction
    # BP Revenue Share Override (for Partners Desk / BP users)
    bp_revenue_share_override: Optional[float] = None  # Override percentage (must be <= BP's default)


class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    booking_number: Optional[str] = None
    client_id: str
    stock_id: str
    quantity: int
    buying_price: float
    selling_price: Optional[float] = None
    booking_date: str
    status: str
    approval_status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    created_by: str
    # Booking type
    booking_type: str = "client"  # "client", "team", or "own"
    insider_form_uploaded: bool = False
    insider_form_path: Optional[str] = None
    # Referral Partner
    referral_partner_id: Optional[str] = None
    rp_code: Optional[str] = None
    rp_name: Optional[str] = None
    rp_revenue_share_percent: Optional[float] = None
    # Employee Revenue Share (reduced by RP share when applicable)
    employee_revenue_share_percent: Optional[float] = None  # Employee's final share after RP deduction
    base_employee_share_percent: float = 100.0  # Default before any deductions
    employee_commission_amount: Optional[float] = None  # Calculated when stock transfer confirmed
    employee_commission_status: str = "pending"  # pending, calculated, paid
    # Client confirmation
    client_confirmation_status: str = "pending"
    client_confirmation_token: Optional[str] = None
    client_confirmed_at: Optional[str] = None
    client_denial_reason: Optional[str] = None
    # Loss booking approval
    is_loss_booking: bool = False
    loss_approval_status: str = "not_required"
    loss_approved_by: Optional[str] = None
    loss_approved_at: Optional[str] = None
    # Payment tracking
    payments: List[PaymentTranche] = []
    total_paid: float = 0
    payment_status: str = "pending"
    payment_complete: bool = False
    payment_completed_at: Optional[str] = None
    dp_status: Optional[str] = None
    dp_transfer_ready: bool = False
    dp_ready_at: Optional[str] = None
    # Void tracking
    is_voided: bool = False
    voided_at: Optional[str] = None
    voided_by: Optional[str] = None
    voided_by_name: Optional[str] = None
    void_reason: Optional[str] = None
    # Stock transfer tracking
    stock_transferred: bool = False
    stock_transferred_at: Optional[str] = None
    stock_transferred_by: Optional[str] = None


class BookingWithDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    booking_number: Optional[str] = None
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
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    # Booking type
    booking_type: str = "client"  # "client", "team", or "own"
    insider_form_uploaded: bool = False
    insider_form_path: Optional[str] = None
    # Referral Partner
    referral_partner_id: Optional[str] = None
    rp_code: Optional[str] = None
    rp_name: Optional[str] = None
    rp_revenue_share_percent: Optional[float] = None
    # Business Partner
    business_partner_id: Optional[str] = None
    bp_name: Optional[str] = None
    bp_revenue_share_percent: Optional[float] = None
    is_bp_booking: bool = False
    # Employee Revenue Share (reduced by RP share when applicable)
    employee_revenue_share_percent: Optional[float] = None  # Employee's final share after RP deduction
    base_employee_share_percent: float = 100.0  # Default before any deductions
    employee_commission_amount: Optional[float] = None  # Calculated when stock transfer confirmed
    employee_commission_status: str = "pending"  # pending, calculated, paid
    # Client confirmation
    client_confirmation_status: str = "pending"
    client_confirmed_at: Optional[str] = None
    client_denial_reason: Optional[str] = None
    # Loss booking approval
    is_loss_booking: bool = False
    loss_approval_status: str = "not_required"
    loss_approved_by: Optional[str] = None
    loss_approved_at: Optional[str] = None
    # Payment tracking
    payments: List[PaymentTranche] = []
    total_paid: float = 0
    payment_status: str = "pending"
    payment_complete: bool = False
    payment_completed_at: Optional[str] = None
    dp_status: Optional[str] = None
    dp_transfer_ready: bool = False
    dp_ready_at: Optional[str] = None
    # Void tracking
    is_voided: bool = False
    voided_at: Optional[str] = None
    voided_by: Optional[str] = None
    voided_by_name: Optional[str] = None
    void_reason: Optional[str] = None
    # Stock transfer tracking
    stock_transferred: bool = False
    stock_transferred_at: Optional[str] = None
    stock_transferred_by: Optional[str] = None


# ============== DP Transfer Report Model ==============
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


# ============== Dashboard Models ==============
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


# ============== Client Suspension Request ==============
class ClientSuspensionRequest(BaseModel):
    reason: str


# ============== Client Confirmation Request ==============
class ClientConfirmationRequest(BaseModel):
    reason: Optional[str] = None



# ============== Referral Partner Models ==============
class ReferralPartnerCreate(BaseModel):
    name: str
    email: EmailStr  # Required
    phone: str  # Required - 10 digit mobile number
    pan_number: str
    aadhar_number: str
    address: str  # Required
    # Bank Details (Required for payouts)
    bank_name: str
    bank_account_number: str
    bank_ifsc_code: str
    bank_branch: Optional[str] = None


class ReferralPartner(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    rp_code: str  # Unique code like RP-XXXX
    name: str
    email: Optional[str] = None  # Required for new RPs, but allow None for legacy data
    phone: Optional[str] = None  # Required for new RPs, but allow None for legacy data
    pan_number: str
    aadhar_number: str
    address: Optional[str] = None  # Required for new RPs, but allow None for legacy data
    # Bank Details
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_branch: Optional[str] = None
    # Documents (all mandatory for RP creation flow)
    pan_card_url: Optional[str] = None
    aadhar_card_url: Optional[str] = None
    cancelled_cheque_url: Optional[str] = None
    # Approval Status - Must be approved by PE Desk/PE Manager before use
    approval_status: str = "pending"  # pending, approved, rejected
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    # Status
    is_active: bool = True
    # Audit
    created_by: str
    created_by_name: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None



# ============== Email Template Models ==============
class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    is_active: Optional[bool] = None


class EmailTemplatePreview(BaseModel):
    variables: Dict[str, str]
