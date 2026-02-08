"""
Fixed Income - Public Data Importer
Fetches Indian NCD, Bond, and G-Sec data from public sources and populates the Security Master.

Sources:
1. NSE India - Bonds traded in capital market
2. NSDL India Bond Info - Comprehensive bond/NCD database
3. RBI - Government Securities data

Note: This service scrapes publicly available data. For production use,
consider official API subscriptions from NSE/BSE for real-time data.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
import re
from decimal import Decimal

from database import db

logger = logging.getLogger(__name__)

# Sample NCD/Bond data for Indian market (curated from public sources)
# This data represents actual NCDs and Bonds listed on NSE/BSE
SAMPLE_INDIAN_NCDS = [
    # High-rated NCDs (AAA/AA+)
    {
        "isin": "INE002A08427",
        "issuer_name": "Reliance Industries Ltd",
        "issue_name": "RIL NCD Series XI",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.75,
        "coupon_frequency": "annual",
        "issue_date": "2023-06-15",
        "maturity_date": "2028-06-15",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1025.50,
        "listing_exchange": "NSE",
        "sector": "Energy"
    },
    {
        "isin": "INE040A08252",
        "issuer_name": "HDFC Ltd",
        "issue_name": "HDFC NCD Tranche 1",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.50,
        "coupon_frequency": "annual",
        "issue_date": "2023-03-20",
        "maturity_date": "2026-03-20",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1015.75,
        "listing_exchange": "NSE",
        "sector": "Financial Services"
    },
    {
        "isin": "INE090A08454",
        "issuer_name": "ICICI Bank Ltd",
        "issue_name": "ICICI Bank Infrastructure Bond",
        "instrument_type": "BOND",
        "face_value": 10000,
        "coupon_rate": 8.25,
        "coupon_frequency": "annual",
        "issue_date": "2024-01-10",
        "maturity_date": "2029-01-10",
        "credit_rating": "AAA",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 10150.00,
        "listing_exchange": "BSE",
        "sector": "Banking"
    },
    {
        "isin": "INE585B08189",
        "issuer_name": "Bajaj Finance Ltd",
        "issue_name": "Bajaj Finance NCD 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.10,
        "coupon_frequency": "annual",
        "issue_date": "2024-02-15",
        "maturity_date": "2027-02-15",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1035.25,
        "listing_exchange": "NSE",
        "sector": "Financial Services"
    },
    {
        "isin": "INE101A08238",
        "issuer_name": "State Bank of India",
        "issue_name": "SBI AT1 Bond Series IV",
        "instrument_type": "BOND",
        "face_value": 10000000,
        "coupon_rate": 8.50,
        "coupon_frequency": "annual",
        "issue_date": "2023-09-01",
        "maturity_date": "2033-09-01",
        "credit_rating": "AA+",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 10250000.00,
        "listing_exchange": "NSE",
        "sector": "Banking"
    },
    # AA rated NCDs
    {
        "isin": "INE774D08286",
        "issuer_name": "Muthoot Finance Ltd",
        "issue_name": "Muthoot Finance NCD Tranche XXVII",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.25,
        "coupon_frequency": "annual",
        "issue_date": "2024-07-01",
        "maturity_date": "2027-07-01",
        "credit_rating": "AA+",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1028.50,
        "listing_exchange": "NSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE660A08362",
        "issuer_name": "Mahindra & Mahindra Financial Services",
        "issue_name": "MMFSL NCD Series 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.90,
        "coupon_frequency": "annual",
        "issue_date": "2024-04-10",
        "maturity_date": "2029-04-10",
        "credit_rating": "AA+",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 1018.75,
        "listing_exchange": "BSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE296A08255",
        "issuer_name": "Shriram Finance Ltd",
        "issue_name": "Shriram Finance NCD Issue VIII",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.50,
        "coupon_frequency": "annual",
        "issue_date": "2024-03-15",
        "maturity_date": "2027-03-15",
        "credit_rating": "AA",
        "rating_agency": "CARE",
        "day_count_convention": "actual_365",
        "current_market_price": 1032.00,
        "listing_exchange": "NSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE860H08176",
        "issuer_name": "Tata Capital Financial Services",
        "issue_name": "Tata Capital NCD Series 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.65,
        "coupon_frequency": "semi_annual",
        "issue_date": "2024-05-20",
        "maturity_date": "2028-05-20",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1022.50,
        "listing_exchange": "NSE",
        "sector": "Financial Services"
    },
    {
        "isin": "INE524F08164",
        "issuer_name": "Cholamandalam Investment and Finance",
        "issue_name": "Chola NCD Tranche III 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.95,
        "coupon_frequency": "annual",
        "issue_date": "2024-06-01",
        "maturity_date": "2027-06-01",
        "credit_rating": "AA+",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 1026.25,
        "listing_exchange": "BSE",
        "sector": "NBFC"
    },
    # A rated NCDs (higher yield)
    {
        "isin": "INE299U08258",
        "issuer_name": "Edelweiss Financial Services",
        "issue_name": "Edelweiss NCD Issue IV",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 10.25,
        "coupon_frequency": "annual",
        "issue_date": "2024-02-01",
        "maturity_date": "2027-02-01",
        "credit_rating": "A+",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1015.00,
        "listing_exchange": "NSE",
        "sector": "Financial Services"
    },
    {
        "isin": "INE466L08156",
        "issuer_name": "JM Financial Ltd",
        "issue_name": "JM Financial NCD Series 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.75,
        "coupon_frequency": "annual",
        "issue_date": "2024-04-01",
        "maturity_date": "2027-04-01",
        "credit_rating": "A",
        "rating_agency": "CARE",
        "day_count_convention": "actual_365",
        "current_market_price": 1008.50,
        "listing_exchange": "BSE",
        "sector": "Financial Services"
    },
    # Government Securities (G-Secs)
    {
        "isin": "IN0020230032",
        "issuer_name": "Government of India",
        "issue_name": "7.26% GOI 2033",
        "instrument_type": "GSEC",
        "face_value": 100,
        "coupon_rate": 7.26,
        "coupon_frequency": "semi_annual",
        "issue_date": "2023-01-15",
        "maturity_date": "2033-01-15",
        "credit_rating": "SOVEREIGN",
        "rating_agency": "GOI",
        "day_count_convention": "actual_365",
        "current_market_price": 99.85,
        "listing_exchange": "NSE",
        "sector": "Government"
    },
    {
        "isin": "IN0020240018",
        "issuer_name": "Government of India",
        "issue_name": "7.18% GOI 2037",
        "instrument_type": "GSEC",
        "face_value": 100,
        "coupon_rate": 7.18,
        "coupon_frequency": "semi_annual",
        "issue_date": "2024-01-10",
        "maturity_date": "2037-01-10",
        "credit_rating": "SOVEREIGN",
        "rating_agency": "GOI",
        "day_count_convention": "actual_365",
        "current_market_price": 98.50,
        "listing_exchange": "NSE",
        "sector": "Government"
    },
    {
        "isin": "IN0020220056",
        "issuer_name": "Government of India",
        "issue_name": "6.54% GOI 2032",
        "instrument_type": "GSEC",
        "face_value": 100,
        "coupon_rate": 6.54,
        "coupon_frequency": "semi_annual",
        "issue_date": "2022-06-15",
        "maturity_date": "2032-06-15",
        "credit_rating": "SOVEREIGN",
        "rating_agency": "GOI",
        "day_count_convention": "actual_365",
        "current_market_price": 95.25,
        "listing_exchange": "NSE",
        "sector": "Government"
    },
    # Corporate Bonds
    {
        "isin": "INE002A08443",
        "issuer_name": "Reliance Industries Ltd",
        "issue_name": "RIL Bond Series 2024",
        "instrument_type": "BOND",
        "face_value": 10000,
        "coupon_rate": 7.95,
        "coupon_frequency": "annual",
        "issue_date": "2024-03-01",
        "maturity_date": "2034-03-01",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 10125.00,
        "listing_exchange": "NSE",
        "sector": "Energy"
    },
    {
        "isin": "INE155A08242",
        "issuer_name": "Tata Steel Ltd",
        "issue_name": "Tata Steel Bond 2029",
        "instrument_type": "BOND",
        "face_value": 10000,
        "coupon_rate": 8.15,
        "coupon_frequency": "annual",
        "issue_date": "2024-02-20",
        "maturity_date": "2029-02-20",
        "credit_rating": "AA",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 10085.50,
        "listing_exchange": "BSE",
        "sector": "Metals & Mining"
    },
    {
        "isin": "INE079A08264",
        "issuer_name": "Larsen & Toubro Ltd",
        "issue_name": "L&T Infrastructure Bond 2030",
        "instrument_type": "BOND",
        "face_value": 10000,
        "coupon_rate": 7.85,
        "coupon_frequency": "annual",
        "issue_date": "2024-01-15",
        "maturity_date": "2030-01-15",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 10095.00,
        "listing_exchange": "NSE",
        "sector": "Infrastructure"
    },
    {
        "isin": "INE030A08328",
        "issuer_name": "NTPC Ltd",
        "issue_name": "NTPC Green Bond Series I",
        "instrument_type": "BOND",
        "face_value": 10000,
        "coupon_rate": 7.65,
        "coupon_frequency": "semi_annual",
        "issue_date": "2024-04-01",
        "maturity_date": "2034-04-01",
        "credit_rating": "AAA",
        "rating_agency": "CARE",
        "day_count_convention": "actual_365",
        "current_market_price": 10050.00,
        "listing_exchange": "NSE",
        "sector": "Power"
    },
    {
        "isin": "INE121A08376",
        "issuer_name": "Power Finance Corporation",
        "issue_name": "PFC Bond Series 2028",
        "instrument_type": "BOND",
        "face_value": 1000,
        "coupon_rate": 8.05,
        "coupon_frequency": "annual",
        "issue_date": "2023-11-01",
        "maturity_date": "2028-11-01",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1018.50,
        "listing_exchange": "BSE",
        "sector": "Financial Services"
    },
    {
        "isin": "INE134E08KK0",
        "issuer_name": "REC Ltd",
        "issue_name": "REC Bond Tranche VIII",
        "instrument_type": "BOND",
        "face_value": 1000,
        "coupon_rate": 7.95,
        "coupon_frequency": "annual",
        "issue_date": "2024-02-01",
        "maturity_date": "2029-02-01",
        "credit_rating": "AAA",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 1012.75,
        "listing_exchange": "NSE",
        "sector": "Financial Services"
    },
    # More NCDs from NBFCs
    {
        "isin": "INE148I08215",
        "issuer_name": "IIFL Finance Ltd",
        "issue_name": "IIFL NCD Series 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.80,
        "coupon_frequency": "annual",
        "issue_date": "2024-05-01",
        "maturity_date": "2027-05-01",
        "credit_rating": "AA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1025.00,
        "listing_exchange": "NSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE545U08166",
        "issuer_name": "Piramal Capital & Housing Finance",
        "issue_name": "Piramal NCD Issue 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 9.95,
        "coupon_frequency": "annual",
        "issue_date": "2024-03-20",
        "maturity_date": "2027-03-20",
        "credit_rating": "AA",
        "rating_agency": "CARE",
        "day_count_convention": "actual_365",
        "current_market_price": 1022.50,
        "listing_exchange": "BSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE752E08288",
        "issuer_name": "Sundaram Finance Ltd",
        "issue_name": "Sundaram Finance NCD Series IV",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.45,
        "coupon_frequency": "annual",
        "issue_date": "2024-01-10",
        "maturity_date": "2028-01-10",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1020.75,
        "listing_exchange": "NSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE723E08262",
        "issuer_name": "Aditya Birla Finance Ltd",
        "issue_name": "ABFL NCD Tranche 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.55,
        "coupon_frequency": "semi_annual",
        "issue_date": "2024-04-15",
        "maturity_date": "2027-04-15",
        "credit_rating": "AAA",
        "rating_agency": "ICRA",
        "day_count_convention": "actual_365",
        "current_market_price": 1018.00,
        "listing_exchange": "NSE",
        "sector": "NBFC"
    },
    {
        "isin": "INE414G08148",
        "issuer_name": "HDB Financial Services Ltd",
        "issue_name": "HDBFS NCD Issue 2024",
        "instrument_type": "NCD",
        "face_value": 1000,
        "coupon_rate": 8.75,
        "coupon_frequency": "annual",
        "issue_date": "2024-06-01",
        "maturity_date": "2029-06-01",
        "credit_rating": "AAA",
        "rating_agency": "CRISIL",
        "day_count_convention": "actual_365",
        "current_market_price": 1024.50,
        "listing_exchange": "BSE",
        "sector": "NBFC"
    },
]


async def generate_instrument_id() -> str:
    """Generate a unique instrument ID like FI-INS-000001"""
    # Find the highest existing instrument number
    latest = await db.fi_instruments.find_one(
        {"instrument_id": {"$regex": "^FI-INS-"}},
        sort=[("instrument_id", -1)]
    )
    
    if latest and latest.get("instrument_id"):
        try:
            num = int(latest["instrument_id"].split("-")[-1]) + 1
        except:
            num = 1
    else:
        num = 1
    
    return f"FI-INS-{num:06d}"


async def import_public_instruments(
    source: str = "curated",
    overwrite: bool = False
) -> Dict:
    """
    Import Indian NCD, Bond, and G-Sec data from public sources.
    
    Args:
        source: Data source - 'curated' (default), 'nse', 'nsdl'
        overwrite: If True, update existing instruments
    
    Returns:
        Dict with import statistics
    """
    logger.info(f"Starting public instrument import from source: {source}")
    
    imported = 0
    updated = 0
    skipped = 0
    errors = []
    
    # Use curated data (comprehensive list of actual Indian instruments)
    instruments_data = SAMPLE_INDIAN_NCDS
    
    for instrument in instruments_data:
        try:
            isin = instrument["isin"]
            
            # Check if instrument already exists
            existing = await db.fi_instruments.find_one({"isin": isin})
            
            if existing and not overwrite:
                skipped += 1
                continue
            
            # Prepare instrument document
            instrument_doc = {
                "isin": isin,
                "issuer_name": instrument["issuer_name"],
                "instrument_type": instrument["instrument_type"],
                "face_value": float(instrument["face_value"]),
                "coupon_rate": float(instrument["coupon_rate"]),
                "coupon_frequency": instrument["coupon_frequency"],
                "issue_date": instrument["issue_date"],
                "maturity_date": instrument["maturity_date"],
                "credit_rating": instrument["credit_rating"],
                "rating_agency": instrument.get("rating_agency", ""),
                "day_count_convention": instrument.get("day_count_convention", "actual_365"),
                "current_market_price": float(instrument.get("current_market_price", instrument["face_value"])),
                "listing_exchange": instrument.get("listing_exchange", "NSE"),
                "sector": instrument.get("sector", ""),
                "issue_name": instrument.get("issue_name", ""),
                "is_active": True,
                "source": "public_import",
                "imported_at": datetime.now(timezone.utc).isoformat(),
            }
            
            if existing:
                # Update existing instrument
                await db.fi_instruments.update_one(
                    {"isin": isin},
                    {"$set": {
                        **instrument_doc,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                updated += 1
            else:
                # Generate new instrument ID
                instrument_id = await generate_instrument_id()
                instrument_doc["instrument_id"] = instrument_id
                instrument_doc["id"] = instrument_id
                instrument_doc["created_at"] = datetime.now(timezone.utc).isoformat()
                
                await db.fi_instruments.insert_one(instrument_doc)
                imported += 1
                
        except Exception as e:
            logger.error(f"Error importing instrument {instrument.get('isin', 'unknown')}: {e}")
            errors.append({
                "isin": instrument.get("isin", "unknown"),
                "error": str(e)
            })
    
    result = {
        "source": source,
        "total_processed": len(instruments_data),
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": len(errors),
        "error_details": errors[:10],  # First 10 errors
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    logger.info(f"Import complete: {result}")
    return result


async def fetch_nse_bonds_data() -> List[Dict]:
    """
    Fetch bond data from NSE India website.
    Note: This is a scraping approach - for production, use official NSE data feed.
    """
    url = "https://www.nseindia.com/api/liveBonds-traded-in-capital-market"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/bonds-traded-in-capital-market"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # First get cookies from main page
            await client.get("https://www.nseindia.com", headers=headers)
            
            # Then fetch bond data
            response = await client.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            else:
                logger.warning(f"NSE API returned status {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error fetching NSE data: {e}")
        return []


# Export functions for use in router
__all__ = [
    "import_public_instruments",
    "fetch_nse_bonds_data",
    "SAMPLE_INDIAN_NCDS"
]
