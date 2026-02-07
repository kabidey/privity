"""
Fixed Income Router - Security Master

API endpoints for managing the Fixed Income Instrument database (Security Master).
Implements full RBAC using the existing permission service.
"""

import logging
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Depends, Query

from database import db
from utils.auth import get_current_user
from services.permission_service import require_permission, has_permission
from config import is_pe_level

from .models import (
    Instrument, InstrumentCreate, InstrumentUpdate,
    InstrumentMarketData, InstrumentType, CouponFrequency,
    DayCountConvention, CreditRating
)
from .calculations import (
    calculate_accrued_interest, calculate_ytm,
    calculate_dirty_price, price_from_yield
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixed-income/instruments", tags=["Fixed Income - Security Master"])


# ==================== HELPER FUNCTIONS ====================

def instrument_to_dict(instrument: dict) -> dict:
    """Convert MongoDB document to API response format"""
    # Handle ObjectId and convert Decimals to strings
    result = {k: v for k, v in instrument.items() if k != "_id"}
    
    # Convert Decimal128 to string for JSON serialization
    decimal_fields = [
        "face_value", "coupon_rate", "current_market_price",
        "last_traded_price", "accrued_interest", "dirty_price",
        "ytm", "call_price", "put_price"
    ]
    for field in decimal_fields:
        if field in result and result[field] is not None:
            result[field] = str(result[field])
    
    return result


# ==================== CRUD ENDPOINTS ====================

@router.post("", response_model=dict)
async def create_instrument(
    instrument: InstrumentCreate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.create", "create fixed income instrument"))
):
    """
    Create a new fixed income instrument in the Security Master.
    
    Requires: fixed_income.create permission (PE Desk, PE Manager)
    """
    # Check if ISIN already exists
    existing = await db.fi_instruments.find_one({"isin": instrument.isin})
    if existing:
        raise HTTPException(status_code=400, detail=f"Instrument with ISIN {instrument.isin} already exists")
    
    # Create instrument document
    import uuid
    instrument_dict = instrument.dict()
    instrument_dict["id"] = str(uuid.uuid4())
    instrument_dict["created_at"] = datetime.now()
    instrument_dict["updated_at"] = datetime.now()
    instrument_dict["created_by"] = current_user.get("id")
    instrument_dict["created_by_name"] = current_user.get("name")
    
    # Convert date objects to strings for MongoDB
    for field in ["issue_date", "maturity_date", "rating_date", "call_date", "put_date", "last_traded_date"]:
        if field in instrument_dict and instrument_dict[field] is not None:
            if isinstance(instrument_dict[field], date):
                instrument_dict[field] = instrument_dict[field].isoformat()
    
    # Store in MongoDB
    await db.fi_instruments.insert_one(instrument_dict)
    
    logger.info(f"Created fixed income instrument: {instrument.isin} by {current_user.get('name')}")
    
    return {"message": "Instrument created successfully", "id": instrument_dict["id"], "isin": instrument.isin}


@router.get("", response_model=dict)
async def list_instruments(
    instrument_type: Optional[InstrumentType] = None,
    issuer: Optional[str] = None,
    credit_rating: Optional[CreditRating] = None,
    min_coupon: Optional[float] = None,
    max_coupon: Optional[float] = None,
    maturity_from: Optional[date] = None,
    maturity_to: Optional[date] = None,
    is_active: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view fixed income instruments"))
):
    """
    List all fixed income instruments with filtering.
    
    Requires: fixed_income.view permission
    """
    # Build query
    query = {"is_active": is_active}
    
    if instrument_type:
        query["instrument_type"] = instrument_type.value
    
    if issuer:
        query["issuer_name"] = {"$regex": issuer, "$options": "i"}
    
    if credit_rating:
        query["credit_rating"] = credit_rating.value
    
    if min_coupon is not None:
        query["coupon_rate"] = {"$gte": Decimal(str(min_coupon))}
    
    if max_coupon is not None:
        if "coupon_rate" in query:
            query["coupon_rate"]["$lte"] = Decimal(str(max_coupon))
        else:
            query["coupon_rate"] = {"$lte": Decimal(str(max_coupon))}
    
    if maturity_from:
        query["maturity_date"] = {"$gte": maturity_from.isoformat()}
    
    if maturity_to:
        if "maturity_date" in query:
            query["maturity_date"]["$lte"] = maturity_to.isoformat()
        else:
            query["maturity_date"] = {"$lte": maturity_to.isoformat()}
    
    # Get total count
    total = await db.fi_instruments.count_documents(query)
    
    # Get instruments
    cursor = db.fi_instruments.find(query, {"_id": 0}).sort("issuer_name", 1).skip(skip).limit(limit)
    instruments = await cursor.to_list(length=limit)
    
    # Calculate live pricing for each instrument
    today = date.today()
    for inst in instruments:
        if inst.get("current_market_price"):
            try:
                # Parse dates
                issue_dt = date.fromisoformat(inst["issue_date"]) if isinstance(inst["issue_date"], str) else inst["issue_date"]
                maturity_dt = date.fromisoformat(inst["maturity_date"]) if isinstance(inst["maturity_date"], str) else inst["maturity_date"]
                
                face_value = Decimal(str(inst.get("face_value", 100)))
                coupon_rate = Decimal(str(inst.get("coupon_rate", 0)))
                cmp = Decimal(str(inst["current_market_price"]))
                freq = CouponFrequency(inst.get("coupon_frequency", "annual"))
                conv = DayCountConvention(inst.get("day_count_convention", "ACT/365"))
                
                # Calculate accrued interest
                accrued = calculate_accrued_interest(
                    face_value=face_value,
                    coupon_rate=coupon_rate,
                    settlement_date=today,
                    issue_date=issue_dt,
                    maturity_date=maturity_dt,
                    frequency=freq,
                    convention=conv
                )
                
                # Calculate YTM
                ytm = calculate_ytm(
                    clean_price=cmp,
                    face_value=face_value,
                    coupon_rate=coupon_rate,
                    settlement_date=today,
                    maturity_date=maturity_dt,
                    frequency=freq,
                    convention=conv
                )
                
                inst["accrued_interest"] = str(accrued)
                inst["dirty_price"] = str(cmp + accrued)
                inst["ytm"] = str(ytm)
            except Exception as e:
                logger.warning(f"Error calculating pricing for {inst.get('isin')}: {e}")
    
    return {
        "instruments": instruments,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{instrument_id}", response_model=dict)
async def get_instrument(
    instrument_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "view fixed income instrument"))
):
    """
    Get detailed information about a specific instrument including live pricing.
    """
    instrument = await db.fi_instruments.find_one(
        {"$or": [{"id": instrument_id}, {"isin": instrument_id}]},
        {"_id": 0}
    )
    
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # Calculate live pricing
    today = date.today()
    if instrument.get("current_market_price"):
        try:
            issue_dt = date.fromisoformat(instrument["issue_date"]) if isinstance(instrument["issue_date"], str) else instrument["issue_date"]
            maturity_dt = date.fromisoformat(instrument["maturity_date"]) if isinstance(instrument["maturity_date"], str) else instrument["maturity_date"]
            
            face_value = Decimal(str(instrument.get("face_value", 100)))
            coupon_rate = Decimal(str(instrument.get("coupon_rate", 0)))
            cmp = Decimal(str(instrument["current_market_price"]))
            freq = CouponFrequency(instrument.get("coupon_frequency", "annual"))
            conv = DayCountConvention(instrument.get("day_count_convention", "ACT/365"))
            
            accrued = calculate_accrued_interest(
                face_value=face_value,
                coupon_rate=coupon_rate,
                settlement_date=today,
                issue_date=issue_dt,
                maturity_date=maturity_dt,
                frequency=freq,
                convention=conv
            )
            
            ytm = calculate_ytm(
                clean_price=cmp,
                face_value=face_value,
                coupon_rate=coupon_rate,
                settlement_date=today,
                maturity_date=maturity_dt,
                frequency=freq,
                convention=conv
            )
            
            instrument["accrued_interest"] = str(accrued)
            instrument["dirty_price"] = str(cmp + accrued)
            instrument["ytm"] = str(ytm)
        except Exception as e:
            logger.warning(f"Error calculating pricing: {e}")
    
    return instrument


@router.put("/{instrument_id}", response_model=dict)
async def update_instrument(
    instrument_id: str,
    update: InstrumentUpdate,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.edit", "edit fixed income instrument"))
):
    """
    Update an existing instrument.
    
    Requires: fixed_income.edit permission (PE Desk, PE Manager)
    """
    # Check instrument exists
    existing = await db.fi_instruments.find_one(
        {"$or": [{"id": instrument_id}, {"isin": instrument_id}]}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # Build update
    update_dict = {k: v for k, v in update.dict().items() if v is not None}
    
    if not update_dict:
        return {"message": "No updates provided"}
    
    # Convert dates
    for field in ["rating_date", "call_date", "put_date"]:
        if field in update_dict and update_dict[field] is not None:
            if isinstance(update_dict[field], date):
                update_dict[field] = update_dict[field].isoformat()
    
    update_dict["updated_at"] = datetime.now()
    
    await db.fi_instruments.update_one(
        {"$or": [{"id": instrument_id}, {"isin": instrument_id}]},
        {"$set": update_dict}
    )
    
    logger.info(f"Updated instrument {instrument_id} by {current_user.get('name')}")
    
    return {"message": "Instrument updated successfully"}


@router.patch("/{instrument_id}/market-data", response_model=dict)
async def update_market_data(
    instrument_id: str,
    market_data: InstrumentMarketData,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.edit", "update market data"))
):
    """
    Update current market price for an instrument.
    
    This endpoint is optimized for bulk market data updates.
    """
    result = await db.fi_instruments.update_one(
        {"$or": [{"id": instrument_id}, {"isin": instrument_id}]},
        {"$set": {
            "current_market_price": str(market_data.current_market_price),
            "last_traded_price": str(market_data.last_traded_price) if market_data.last_traded_price else None,
            "last_traded_date": market_data.last_traded_date.isoformat() if market_data.last_traded_date else None,
            "updated_at": datetime.now()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    return {"message": "Market data updated"}


@router.delete("/{instrument_id}", response_model=dict)
async def delete_instrument(
    instrument_id: str,
    permanent: bool = False,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.delete", "delete fixed income instrument"))
):
    """
    Delete or deactivate an instrument.
    
    Requires: fixed_income.delete permission (PE Desk only)
    
    Args:
        permanent: If True, permanently delete. If False, just deactivate.
    """
    # Only PE Desk can permanently delete
    if permanent and not is_pe_level(current_user.get("role", 99)):
        raise HTTPException(status_code=403, detail="Only PE Desk can permanently delete instruments")
    
    if permanent:
        result = await db.fi_instruments.delete_one(
            {"$or": [{"id": instrument_id}, {"isin": instrument_id}]}
        )
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Instrument not found")
        message = "Instrument permanently deleted"
    else:
        result = await db.fi_instruments.update_one(
            {"$or": [{"id": instrument_id}, {"isin": instrument_id}]},
            {"$set": {"is_active": False, "updated_at": datetime.now()}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Instrument not found")
        message = "Instrument deactivated"
    
    logger.info(f"{message}: {instrument_id} by {current_user.get('name')}")
    
    return {"message": message}


# ==================== PRICING CALCULATOR ====================

@router.post("/calculate-pricing", response_model=dict)
async def calculate_pricing(
    isin: str,
    clean_price: float,
    settlement_date: date,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "calculate pricing"))
):
    """
    Calculate complete pricing for an instrument at given clean price.
    
    Returns: accrued interest, dirty price, YTM, duration
    """
    # Get instrument
    instrument = await db.fi_instruments.find_one({"isin": isin}, {"_id": 0})
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    try:
        issue_dt = date.fromisoformat(instrument["issue_date"]) if isinstance(instrument["issue_date"], str) else instrument["issue_date"]
        maturity_dt = date.fromisoformat(instrument["maturity_date"]) if isinstance(instrument["maturity_date"], str) else instrument["maturity_date"]
        
        face_value = Decimal(str(instrument.get("face_value", 100)))
        coupon_rate = Decimal(str(instrument.get("coupon_rate", 0)))
        clean_price_dec = Decimal(str(clean_price))
        freq = CouponFrequency(instrument.get("coupon_frequency", "annual"))
        conv = DayCountConvention(instrument.get("day_count_convention", "ACT/365"))
        
        # Calculate all pricing components
        accrued = calculate_accrued_interest(
            face_value=face_value,
            coupon_rate=coupon_rate,
            settlement_date=settlement_date,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            frequency=freq,
            convention=conv
        )
        
        dirty_price = clean_price_dec + accrued
        
        ytm = calculate_ytm(
            clean_price=clean_price_dec,
            face_value=face_value,
            coupon_rate=coupon_rate,
            settlement_date=settlement_date,
            maturity_date=maturity_dt,
            frequency=freq,
            convention=conv
        )
        
        from .calculations import calculate_duration, calculate_modified_duration
        
        duration = calculate_duration(
            clean_price=clean_price_dec,
            face_value=face_value,
            coupon_rate=coupon_rate,
            ytm=ytm,
            settlement_date=settlement_date,
            maturity_date=maturity_dt,
            frequency=freq,
            convention=conv
        )
        
        mod_duration = calculate_modified_duration(duration, ytm, freq)
        
        return {
            "isin": isin,
            "settlement_date": settlement_date.isoformat(),
            "clean_price": str(clean_price_dec),
            "accrued_interest": str(accrued),
            "dirty_price": str(dirty_price),
            "ytm": str(ytm),
            "duration": str(duration),
            "modified_duration": str(mod_duration)
        }
        
    except Exception as e:
        logger.error(f"Error calculating pricing: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


@router.post("/price-from-yield", response_model=dict)
async def get_price_from_yield(
    isin: str,
    target_ytm: float,
    settlement_date: date,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.view", "calculate price from yield"))
):
    """
    Calculate the clean price required to achieve a target YTM.
    
    Reverse calculation: input desired yield, get price.
    """
    # Get instrument
    instrument = await db.fi_instruments.find_one({"isin": isin}, {"_id": 0})
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    try:
        issue_dt = date.fromisoformat(instrument["issue_date"]) if isinstance(instrument["issue_date"], str) else instrument["issue_date"]
        maturity_dt = date.fromisoformat(instrument["maturity_date"]) if isinstance(instrument["maturity_date"], str) else instrument["maturity_date"]
        
        face_value = Decimal(str(instrument.get("face_value", 100)))
        coupon_rate = Decimal(str(instrument.get("coupon_rate", 0)))
        target_ytm_dec = Decimal(str(target_ytm))
        freq = CouponFrequency(instrument.get("coupon_frequency", "annual"))
        conv = DayCountConvention(instrument.get("day_count_convention", "ACT/365"))
        
        clean_price = price_from_yield(
            target_ytm=target_ytm_dec,
            face_value=face_value,
            coupon_rate=coupon_rate,
            settlement_date=settlement_date,
            maturity_date=maturity_dt,
            frequency=freq,
            convention=conv
        )
        
        # Also calculate accrued and dirty price
        accrued = calculate_accrued_interest(
            face_value=face_value,
            coupon_rate=coupon_rate,
            settlement_date=settlement_date,
            issue_date=issue_dt,
            maturity_date=maturity_dt,
            frequency=freq,
            convention=conv
        )
        
        return {
            "isin": isin,
            "target_ytm": str(target_ytm_dec),
            "settlement_date": settlement_date.isoformat(),
            "clean_price": str(clean_price),
            "accrued_interest": str(accrued),
            "dirty_price": str(clean_price + accrued)
        }
        
    except Exception as e:
        logger.error(f"Error calculating price from yield: {e}")
        raise HTTPException(status_code=500, detail=f"Calculation error: {str(e)}")


# ==================== BULK UPLOAD ====================

@router.post("/bulk-upload", response_model=dict)
async def bulk_upload_instruments(
    file: bytes,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.create", "bulk upload instruments"))
):
    """
    Bulk upload instruments from CSV.
    
    Expected CSV columns:
    - isin (required)
    - issuer_name (required)
    - instrument_type (default: NCD)
    - face_value (required)
    - issue_date (required, format: YYYY-MM-DD)
    - maturity_date (required, format: YYYY-MM-DD)
    - coupon_rate (required)
    - coupon_frequency (default: annual)
    - day_count_convention (default: ACT/365)
    - credit_rating (default: UNRATED)
    - rating_agency
    - current_market_price
    - lot_size (default: 1)
    """
    import csv
    import io
    import uuid
    
    try:
        # Parse CSV
        content = file.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        created = 0
        updated = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                isin = row.get('isin', '').strip().upper()
                if not isin:
                    errors.append(f"Row {row_num}: Missing ISIN")
                    continue
                
                # Check if exists
                existing = await db.fi_instruments.find_one({"isin": isin})
                
                instrument_data = {
                    "isin": isin,
                    "issuer_name": row.get('issuer_name', '').strip(),
                    "issuer_code": row.get('issuer_code', '').strip().upper() or None,
                    "instrument_type": row.get('instrument_type', 'NCD').strip().upper(),
                    "face_value": row.get('face_value', '1000').strip(),
                    "issue_date": row.get('issue_date', '').strip(),
                    "maturity_date": row.get('maturity_date', '').strip(),
                    "coupon_rate": row.get('coupon_rate', '0').strip(),
                    "coupon_frequency": row.get('coupon_frequency', 'annual').strip().lower(),
                    "day_count_convention": row.get('day_count_convention', 'ACT/365').strip(),
                    "credit_rating": row.get('credit_rating', 'UNRATED').strip().upper(),
                    "rating_agency": row.get('rating_agency', '').strip() or None,
                    "current_market_price": row.get('current_market_price', '').strip() or None,
                    "lot_size": int(row.get('lot_size', '1').strip() or 1),
                    "is_active": True,
                    "updated_at": datetime.now()
                }
                
                # Validate required fields
                if not instrument_data["issuer_name"]:
                    errors.append(f"Row {row_num}: Missing issuer_name")
                    continue
                if not instrument_data["issue_date"]:
                    errors.append(f"Row {row_num}: Missing issue_date")
                    continue
                if not instrument_data["maturity_date"]:
                    errors.append(f"Row {row_num}: Missing maturity_date")
                    continue
                
                if existing:
                    # Update
                    await db.fi_instruments.update_one(
                        {"isin": isin},
                        {"$set": instrument_data}
                    )
                    updated += 1
                else:
                    # Create
                    instrument_data["id"] = str(uuid.uuid4())
                    instrument_data["created_at"] = datetime.now()
                    instrument_data["created_by"] = current_user.get("id")
                    instrument_data["created_by_name"] = current_user.get("name")
                    await db.fi_instruments.insert_one(instrument_data)
                    created += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        logger.info(f"Bulk upload: {created} created, {updated} updated, {len(errors)} errors by {current_user.get('name')}")
        
        return {
            "message": "Bulk upload completed",
            "created": created,
            "updated": updated,
            "errors": errors[:10] if errors else []  # Return first 10 errors
        }
        
    except Exception as e:
        logger.error(f"Bulk upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


@router.get("/download-template")
async def download_template():
    """Download CSV template for bulk upload"""
    import io
    import csv
    from fastapi.responses import StreamingResponse
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        "isin", "issuer_name", "issuer_code", "instrument_type", "face_value",
        "issue_date", "maturity_date", "coupon_rate", "coupon_frequency",
        "day_count_convention", "credit_rating", "rating_agency",
        "current_market_price", "lot_size"
    ])
    
    # Example row
    writer.writerow([
        "INE123A01234", "Example Company Ltd", "EXMPL", "NCD", "1000",
        "2024-01-15", "2027-01-15", "9.50", "annual",
        "ACT/365", "AA+", "CRISIL",
        "1050.00", "1"
    ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fi_instruments_template.csv"}
    )


# ==================== BULK MARKET DATA UPDATE ====================

@router.post("/bulk-market-data", response_model=dict)
async def bulk_update_market_data(
    data: List[InstrumentMarketData],
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("fixed_income.edit", "bulk update market data"))
):
    """
    Bulk update market data for multiple instruments.
    Used for real-time market data integration.
    """
    updated = 0
    errors = []
    
    for item in data:
        try:
            result = await db.fi_instruments.update_one(
                {"isin": item.isin},
                {"$set": {
                    "current_market_price": str(item.current_market_price),
                    "last_traded_price": str(item.last_traded_price) if item.last_traded_price else None,
                    "last_traded_date": item.last_traded_date.isoformat() if item.last_traded_date else None,
                    "updated_at": datetime.now()
                }}
            )
            if result.matched_count > 0:
                updated += 1
            else:
                errors.append(f"ISIN {item.isin} not found")
        except Exception as e:
            errors.append(f"ISIN {item.isin}: {str(e)}")
    
    return {
        "message": "Bulk market data update completed",
        "updated": updated,
        "errors": errors
    }

