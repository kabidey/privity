"""
Fixed Income Trading & Management Portal

A comprehensive module for NCD (Non-Convertible Debentures) and Bond trading,
featuring:
- Security Master (Database of Instruments)
- Pricing & Calculation Engine
- Order Management System (OMS)
- Post-Trade & Settlement
- Reporting & Analytics

All calculations use Decimal precision for financial accuracy.
"""

from .models import (
    Instrument,
    InstrumentType,
    CouponFrequency,
    DayCountConvention,
    FIClient,
    FIOrder,
    OrderStatus,
    OrderType,
    FITransaction,
    FIDealSheet
)

from .calculations import (
    calculate_accrued_interest,
    calculate_ytm,
    price_from_yield,
    calculate_dirty_price,
    generate_cash_flow_schedule,
    calculate_duration,
    calculate_modified_duration
)

__version__ = "1.0.0"
__all__ = [
    "Instrument",
    "InstrumentType", 
    "CouponFrequency",
    "DayCountConvention",
    "FIClient",
    "FIOrder",
    "OrderStatus",
    "OrderType",
    "FITransaction",
    "FIDealSheet",
    "calculate_accrued_interest",
    "calculate_ytm",
    "price_from_yield",
    "calculate_dirty_price",
    "generate_cash_flow_schedule",
    "calculate_duration",
    "calculate_modified_duration"
]
