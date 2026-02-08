"""
Fixed Income Trading & Management Portal

A comprehensive module for NCD (Non-Convertible Debentures) and Bond trading,
featuring:
- Security Master (Database of Instruments)
- Pricing & Calculation Engine
- Order Management System (OMS)
- Post-Trade & Settlement
- Reporting & Analytics
- Multi-Source Bond Data Scraping

Data Sources Supported:
- Official: indiabondsinfo.nsdl.com, rbi.org.in
- Marketplace: indiabonds.com, smest.in, wintwealth.com, goldenpi.com
- Exchange: nseindia.com, bseindia.com

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

from .bond_scraping_service import (
    BondScrapingService,
    BondData,
    DataSource,
    BOND_DATABASE,
    search_local_database
)

__version__ = "1.1.0"
__all__ = [
    # Models
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
    # Calculations
    "calculate_accrued_interest",
    "calculate_ytm",
    "price_from_yield",
    "calculate_dirty_price",
    "generate_cash_flow_schedule",
    "calculate_duration",
    "calculate_modified_duration",
    # Scraping Service
    "BondScrapingService",
    "BondData",
    "DataSource",
    "BOND_DATABASE",
    "search_local_database"
]
