"""
Fixed Income Data Models

Pydantic models and Enums for the Fixed Income Trading Portal.
Uses Decimal for all monetary calculations to ensure precision.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


# ==================== ENUMS ====================

class InstrumentType(str, Enum):
    """Types of fixed income instruments"""
    NCD = "NCD"  # Non-Convertible Debentures
    BOND = "BOND"
    GOVERNMENT_SECURITY = "GSEC"
    TREASURY_BILL = "TBILL"
    COMMERCIAL_PAPER = "CP"
    CERTIFICATE_OF_DEPOSIT = "CD"


class CouponFrequency(str, Enum):
    """Coupon payment frequency"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    ZERO_COUPON = "zero_coupon"  # No coupon payments


class DayCountConvention(str, Enum):
    """Day count conventions for interest calculation"""
    THIRTY_360 = "30/360"  # 30 days per month, 360 days per year
    ACTUAL_ACTUAL = "ACT/ACT"  # Actual days in period / actual days in year
    ACTUAL_360 = "ACT/360"  # Actual days / 360
    ACTUAL_365 = "ACT/365"  # Actual days / 365


class CreditRating(str, Enum):
    """Credit ratings for instruments"""
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB = "BB"
    B = "B"
    C = "C"
    D = "D"
    UNRATED = "UNRATED"


class OrderStatus(str, Enum):
    """Status of an order through its lifecycle"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    CLIENT_APPROVED = "client_approved"
    CLIENT_REJECTED = "client_rejected"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_RECEIVED = "payment_received"
    SETTLEMENT_INITIATED = "settlement_initiated"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Type of order"""
    PRIMARY = "primary"  # New issue allocation
    SECONDARY_BUY = "secondary_buy"
    SECONDARY_SELL = "secondary_sell"


class SettlementStatus(str, Enum):
    """Settlement tracking status"""
    DEAL_BOOKED = "deal_booked"
    CLIENT_APPROVED = "client_approved"
    PAYMENT_RECEIVED = "payment_received"
    SETTLEMENT_INITIATED = "settlement_initiated"
    DEAL_CLOSED = "deal_closed"
    FAILED = "failed"


# ==================== INSTRUMENT MODEL ====================

class InstrumentBase(BaseModel):
    """Base model for fixed income instruments"""
    # Static Data
    isin: str = Field(..., description="ISIN number - unique identifier")
    instrument_type: InstrumentType = Field(default=InstrumentType.NCD)
    issuer_name: str = Field(..., description="Name of the issuing company")
    issuer_code: Optional[str] = Field(None, description="Short code for issuer")
    
    face_value: Decimal = Field(..., ge=0, description="Face value per unit")
    issue_date: date = Field(..., description="Date of issue")
    maturity_date: date = Field(..., description="Date of maturity")
    
    coupon_rate: Decimal = Field(..., ge=0, le=100, description="Annual coupon rate in percentage")
    coupon_frequency: CouponFrequency = Field(default=CouponFrequency.ANNUAL)
    day_count_convention: DayCountConvention = Field(default=DayCountConvention.ACTUAL_365)
    
    # Dynamic Data
    credit_rating: CreditRating = Field(default=CreditRating.UNRATED)
    rating_agency: Optional[str] = Field(None, description="Rating agency name")
    rating_date: Optional[date] = Field(None)
    
    # Option details
    is_callable: bool = Field(default=False)
    call_date: Optional[date] = Field(None)
    call_price: Optional[Decimal] = Field(None)
    
    is_puttable: bool = Field(default=False)
    put_date: Optional[date] = Field(None)
    put_price: Optional[Decimal] = Field(None)
    
    # Listing
    listed_on: Optional[List[str]] = Field(default=None, description="Stock exchanges where listed")
    lot_size: int = Field(default=1, ge=1)
    
    # Status
    is_active: bool = Field(default=True)
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v),
            date: lambda v: v.isoformat()
        }


class InstrumentCreate(InstrumentBase):
    """Model for creating new instrument"""
    pass


class InstrumentUpdate(BaseModel):
    """Model for updating instrument"""
    credit_rating: Optional[CreditRating] = None
    rating_agency: Optional[str] = None
    rating_date: Optional[date] = None
    is_active: Optional[bool] = None
    call_date: Optional[date] = None
    call_price: Optional[Decimal] = None
    put_date: Optional[date] = None
    put_price: Optional[Decimal] = None


class Instrument(InstrumentBase):
    """Full instrument model with ID and metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Current market data
    current_market_price: Optional[Decimal] = Field(None, description="Current Market Price")
    last_traded_price: Optional[Decimal] = Field(None)
    last_traded_date: Optional[date] = Field(None)
    
    # Calculated fields (populated by service)
    accrued_interest: Optional[Decimal] = Field(None)
    dirty_price: Optional[Decimal] = Field(None)
    ytm: Optional[Decimal] = Field(None)
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None


class InstrumentMarketData(BaseModel):
    """Model for updating market data"""
    isin: str
    current_market_price: Decimal
    last_traded_price: Optional[Decimal] = None
    last_traded_date: Optional[date] = None


# ==================== CLIENT MODEL ====================

class FIClientBase(BaseModel):
    """Base model for Fixed Income client"""
    name: str = Field(..., min_length=2)
    pan_number: str = Field(..., pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]$')
    email: Optional[str] = None
    mobile: Optional[str] = None
    
    # Demat details
    dp_id: Optional[str] = None
    dp_name: Optional[str] = None
    client_id: Optional[str] = None
    
    # KYC
    kyc_verified: bool = Field(default=False)
    risk_profile: Optional[str] = Field(None, description="Conservative/Moderate/Aggressive")
    
    # Bank details for settlements
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    bank_ifsc: Optional[str] = None
    
    # Address
    address: Optional[str] = None


class FIClientCreate(FIClientBase):
    """Model for creating client"""
    pass


class FIClient(FIClientBase):
    """Full client model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    created_by: Optional[str] = None
    
    # Linked to main client system
    main_client_id: Optional[str] = Field(None, description="Reference to main clients collection")


# ==================== ORDER MODEL ====================

class FIOrderBase(BaseModel):
    """Base model for Fixed Income orders"""
    client_id: str
    instrument_id: str
    isin: str
    
    order_type: OrderType
    quantity: int = Field(..., gt=0)
    
    # Pricing
    clean_price: Decimal = Field(..., ge=0, description="Clean price per unit")
    accrued_interest: Decimal = Field(default=Decimal("0"), description="Calculated accrued interest")
    dirty_price: Decimal = Field(default=Decimal("0"), description="Clean + Accrued Interest")
    
    ytm: Optional[Decimal] = Field(None, description="Yield to Maturity at order price")
    
    # Settlement
    settlement_date: date
    
    # Notes
    notes: Optional[str] = None


class FIOrderCreate(FIOrderBase):
    """Model for creating order"""
    pass


class FIOrder(FIOrderBase):
    """Full order model with status tracking"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_number: str = Field(default="")
    
    status: OrderStatus = Field(default=OrderStatus.DRAFT)
    
    # Amounts (calculated)
    principal_amount: Decimal = Field(default=Decimal("0"))
    total_consideration: Decimal = Field(default=Decimal("0"))
    
    # Charges
    brokerage: Decimal = Field(default=Decimal("0"))
    stamp_duty: Decimal = Field(default=Decimal("0"))
    gst: Decimal = Field(default=Decimal("0"))
    other_charges: Decimal = Field(default=Decimal("0"))
    
    net_amount: Decimal = Field(default=Decimal("0"))
    
    # Approval workflow
    approved_by_client: bool = Field(default=False)
    client_approval_date: Optional[datetime] = None
    client_rejection_reason: Optional[str] = None
    
    # Payment tracking
    payment_received: bool = Field(default=False)
    payment_received_date: Optional[datetime] = None
    payment_reference: Optional[str] = None
    payment_amount: Optional[Decimal] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v),
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }


# ==================== DEAL SHEET MODEL ====================

class FIDealSheet(BaseModel):
    """Deal sheet sent to client for approval"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    
    # Client info
    client_id: str
    client_name: str
    client_pan: str
    
    # Instrument info
    instrument_id: str
    isin: str
    issuer_name: str
    instrument_type: InstrumentType
    coupon_rate: Decimal
    maturity_date: date
    credit_rating: CreditRating
    
    # Transaction details
    order_type: OrderType
    quantity: int
    clean_price: Decimal
    accrued_interest: Decimal
    dirty_price: Decimal
    ytm: Decimal
    
    # Amounts
    principal_amount: Decimal
    accrued_interest_amount: Decimal
    total_consideration: Decimal
    brokerage: Decimal
    stamp_duty: Decimal
    gst: Decimal
    net_amount: Decimal
    
    settlement_date: date
    
    # Cash flow preview (next 4 payments)
    cash_flow_preview: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Status
    status: str = Field(default="pending")
    sent_at: datetime = Field(default_factory=lambda: datetime.now())
    expires_at: datetime
    viewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Payment instructions
    bank_name: str
    bank_account: str
    bank_ifsc: str
    payment_reference: str


# ==================== TRANSACTION MODEL ====================

class FITransaction(BaseModel):
    """Completed transaction record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_number: str
    
    order_id: str
    client_id: str
    instrument_id: str
    isin: str
    
    transaction_type: OrderType
    transaction_date: date
    settlement_date: date
    
    quantity: int
    clean_price: Decimal
    accrued_interest: Decimal
    dirty_price: Decimal
    ytm: Decimal
    
    principal_amount: Decimal
    accrued_interest_amount: Decimal
    total_consideration: Decimal
    
    charges: Decimal
    net_amount: Decimal
    
    # Settlement
    settlement_status: SettlementStatus = Field(default=SettlementStatus.DEAL_BOOKED)
    
    # Cash flow tracking
    client_payment_received: Decimal = Field(default=Decimal("0"))
    counterparty_payment_made: Decimal = Field(default=Decimal("0"))
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    created_by: Optional[str] = None


# ==================== HOLDINGS MODEL ====================

class FIHolding(BaseModel):
    """Client holding in a fixed income instrument"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    instrument_id: str
    isin: str
    
    quantity: int
    average_cost: Decimal
    current_value: Decimal
    unrealized_pnl: Decimal
    
    # For MTM
    mark_to_market_price: Optional[Decimal] = None
    mtm_date: Optional[date] = None
    
    last_updated: datetime = Field(default_factory=lambda: datetime.now())


# ==================== CASH FLOW MODEL ====================

class CashFlowEntry(BaseModel):
    """Single cash flow entry"""
    date: date
    type: str  # "coupon" or "principal" or "both"
    amount: Decimal
    description: str
    is_projected: bool = True


class CashFlowSchedule(BaseModel):
    """Complete cash flow schedule for a holding"""
    client_id: str
    instrument_id: str
    isin: str
    issuer_name: str
    
    face_value_held: Decimal
    coupon_rate: Decimal
    
    cash_flows: List[CashFlowEntry]
    
    total_coupon_payments: Decimal
    total_principal: Decimal
    total_cash_flows: Decimal
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
