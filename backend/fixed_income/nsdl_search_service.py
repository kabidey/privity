"""
Fixed Income - NSDL Search Service
Provides ISIN/Company search functionality against NSDL-style bond database.

This service maintains a comprehensive database of Indian corporate bonds, NCDs,
and government securities that can be searched and imported into the Security Master.

Data Sources:
- NSDL India Bond Info (indiabondinfo.nsdl.com)
- NSE Debt Market
- BSE Debt Segment
- RBI Government Securities

Note: For production use with real-time NSDL data, API subscription may be required.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import re

from database import db

logger = logging.getLogger(__name__)


# Comprehensive NSDL-style bond database (curated from public sources)
# This represents the structure of NSDL's debt instruments database
NSDL_BOND_DATABASE = [
    # ============ AAA Rated NCDs ============
    {"isin": "INE002A08427", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL NCD Series XI", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2023-06-15", "maturity_date": "2028-06-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Energy", "isin_status": "Active"},
    {"isin": "INE002A08443", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL NCD Series XII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2029-01-10", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Energy", "isin_status": "Active"},
    {"isin": "INE040A08252", "issuer_name": "HDFC Limited", "issue_name": "HDFC NCD Tranche 1", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2023-03-20", "maturity_date": "2026-03-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE040A08260", "issuer_name": "HDFC Limited", "issue_name": "HDFC NCD Tranche 2", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.60, "coupon_frequency": "annual", "issue_date": "2023-09-15", "maturity_date": "2028-09-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE090A08454", "issuer_name": "ICICI Bank Limited", "issue_name": "ICICI Bank Infrastructure Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.25, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2029-01-10", "credit_rating": "AAA", "rating_agency": "ICRA", "listing_exchange": "BSE", "sector": "Banking", "isin_status": "Active"},
    {"isin": "INE090A08462", "issuer_name": "ICICI Bank Limited", "issue_name": "ICICI Bank Tier 2 Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.40, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2034-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Banking", "isin_status": "Active"},
    {"isin": "INE585B08189", "issuer_name": "Bajaj Finance Limited", "issue_name": "Bajaj Finance NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.10, "coupon_frequency": "annual", "issue_date": "2024-02-15", "maturity_date": "2027-02-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE585B08197", "issuer_name": "Bajaj Finance Limited", "issue_name": "Bajaj Finance NCD Series B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.25, "coupon_frequency": "annual", "issue_date": "2024-08-01", "maturity_date": "2029-08-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE860H08176", "issuer_name": "Tata Capital Financial Services Limited", "issue_name": "Tata Capital NCD Series 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.65, "coupon_frequency": "semi_annual", "issue_date": "2024-05-20", "maturity_date": "2028-05-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE860H08184", "issuer_name": "Tata Capital Financial Services Limited", "issue_name": "Tata Capital NCD Series 2025", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.55, "coupon_frequency": "annual", "issue_date": "2025-01-15", "maturity_date": "2030-01-15", "credit_rating": "AAA", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE752E08288", "issuer_name": "Sundaram Finance Limited", "issue_name": "Sundaram Finance NCD Series IV", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.45, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2028-01-10", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE723E08262", "issuer_name": "Aditya Birla Finance Limited", "issue_name": "ABFL NCD Tranche 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.55, "coupon_frequency": "semi_annual", "issue_date": "2024-04-15", "maturity_date": "2027-04-15", "credit_rating": "AAA", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE414G08148", "issuer_name": "HDB Financial Services Limited", "issue_name": "HDBFS NCD Issue 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2029-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "BSE", "sector": "NBFC", "isin_status": "Active"},
    
    # ============ AA+ Rated NCDs ============
    {"isin": "INE101A08238", "issuer_name": "State Bank of India", "issue_name": "SBI AT1 Bond Series IV", "instrument_type": "BOND", "face_value": 10000000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2023-09-01", "maturity_date": "2033-09-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Banking", "isin_status": "Active"},
    {"isin": "INE774D08286", "issuer_name": "Muthoot Finance Limited", "issue_name": "Muthoot Finance NCD Tranche XXVII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.25, "coupon_frequency": "annual", "issue_date": "2024-07-01", "maturity_date": "2027-07-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE774D08294", "issuer_name": "Muthoot Finance Limited", "issue_name": "Muthoot Finance NCD Tranche XXVIII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.35, "coupon_frequency": "annual", "issue_date": "2024-11-01", "maturity_date": "2027-11-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE660A08362", "issuer_name": "Mahindra & Mahindra Financial Services Limited", "issue_name": "MMFSL NCD Series 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.90, "coupon_frequency": "annual", "issue_date": "2024-04-10", "maturity_date": "2029-04-10", "credit_rating": "AA+", "rating_agency": "ICRA", "listing_exchange": "BSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE524F08164", "issuer_name": "Cholamandalam Investment and Finance Company Limited", "issue_name": "Chola NCD Tranche III 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.95, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2027-06-01", "credit_rating": "AA+", "rating_agency": "ICRA", "listing_exchange": "BSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE524F08172", "issuer_name": "Cholamandalam Investment and Finance Company Limited", "issue_name": "Chola NCD Tranche IV 2025", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.05, "coupon_frequency": "annual", "issue_date": "2025-01-01", "maturity_date": "2028-01-01", "credit_rating": "AA+", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    
    # ============ AA Rated NCDs ============
    {"isin": "INE296A08255", "issuer_name": "Shriram Finance Limited", "issue_name": "Shriram Finance NCD Issue VIII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.50, "coupon_frequency": "annual", "issue_date": "2024-03-15", "maturity_date": "2027-03-15", "credit_rating": "AA", "rating_agency": "CARE", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE296A08263", "issuer_name": "Shriram Finance Limited", "issue_name": "Shriram Finance NCD Issue IX", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.60, "coupon_frequency": "annual", "issue_date": "2024-09-01", "maturity_date": "2027-09-01", "credit_rating": "AA", "rating_agency": "CARE", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE148I08215", "issuer_name": "IIFL Finance Limited", "issue_name": "IIFL NCD Series 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.80, "coupon_frequency": "annual", "issue_date": "2024-05-01", "maturity_date": "2027-05-01", "credit_rating": "AA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "NBFC", "isin_status": "Active"},
    {"isin": "INE545U08166", "issuer_name": "Piramal Capital & Housing Finance Limited", "issue_name": "Piramal NCD Issue 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.95, "coupon_frequency": "annual", "issue_date": "2024-03-20", "maturity_date": "2027-03-20", "credit_rating": "AA", "rating_agency": "CARE", "listing_exchange": "BSE", "sector": "NBFC", "isin_status": "Active"},
    
    # ============ A+ and A Rated NCDs ============
    {"isin": "INE299U08258", "issuer_name": "Edelweiss Financial Services Limited", "issue_name": "Edelweiss NCD Issue IV", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.25, "coupon_frequency": "annual", "issue_date": "2024-02-01", "maturity_date": "2027-02-01", "credit_rating": "A+", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE466L08156", "issuer_name": "JM Financial Limited", "issue_name": "JM Financial NCD Series 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.75, "coupon_frequency": "annual", "issue_date": "2024-04-01", "maturity_date": "2027-04-01", "credit_rating": "A", "rating_agency": "CARE", "listing_exchange": "BSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE891K08185", "issuer_name": "Indiabulls Housing Finance Limited", "issue_name": "Indiabulls HF NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.50, "coupon_frequency": "annual", "issue_date": "2024-06-15", "maturity_date": "2027-06-15", "credit_rating": "A", "rating_agency": "CARE", "listing_exchange": "NSE", "sector": "Housing Finance", "isin_status": "Active"},
    
    # ============ A- Rated NCDs (MFI Sector) ============
    {"isin": "INE04HY07351", "issuer_name": "Vedika Credit Capital Limited", "issue_name": "11.25% Vedika Credit Capital NCD Series B", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.25, "coupon_frequency": "monthly", "issue_date": "2025-11-27", "maturity_date": "2027-11-27", "credit_rating": "A-", "rating_agency": "Infomerics", "listing_exchange": "NSE", "sector": "NBFC-MFI", "isin_status": "Active", "issue_size": 350000000, "security_type": "secured", "seniority": "senior", "nri_eligible": True, "debenture_trustee": "Catalyst Trusteeship Limited"},
    {"isin": "INE04HY07310", "issuer_name": "Vedika Credit Capital Limited", "issue_name": "11.60% Vedika Credit Capital NCD", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.60, "coupon_frequency": "monthly", "issue_date": "2024-02-21", "maturity_date": "2027-02-21", "credit_rating": "A-", "rating_agency": "Infomerics", "listing_exchange": "NSE", "sector": "NBFC-MFI", "isin_status": "Active"},
    
    # ============ Corporate Bonds ============
    {"isin": "INE002A08451", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL Bond Series 2024", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.95, "coupon_frequency": "annual", "issue_date": "2024-03-01", "maturity_date": "2034-03-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Energy", "isin_status": "Active"},
    {"isin": "INE155A08242", "issuer_name": "Tata Steel Limited", "issue_name": "Tata Steel Bond 2029", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.15, "coupon_frequency": "annual", "issue_date": "2024-02-20", "maturity_date": "2029-02-20", "credit_rating": "AA", "rating_agency": "ICRA", "listing_exchange": "BSE", "sector": "Metals & Mining", "isin_status": "Active"},
    {"isin": "INE155A08259", "issuer_name": "Tata Steel Limited", "issue_name": "Tata Steel Bond 2034", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.25, "coupon_frequency": "annual", "issue_date": "2024-07-01", "maturity_date": "2034-07-01", "credit_rating": "AA", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "Metals & Mining", "isin_status": "Active"},
    {"isin": "INE079A08264", "issuer_name": "Larsen & Toubro Limited", "issue_name": "L&T Infrastructure Bond 2030", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.85, "coupon_frequency": "annual", "issue_date": "2024-01-15", "maturity_date": "2030-01-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Infrastructure", "isin_status": "Active"},
    {"isin": "INE079A08272", "issuer_name": "Larsen & Toubro Limited", "issue_name": "L&T Green Bond 2032", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.75, "coupon_frequency": "semi_annual", "issue_date": "2024-06-01", "maturity_date": "2032-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Infrastructure", "isin_status": "Active"},
    {"isin": "INE030A08328", "issuer_name": "NTPC Limited", "issue_name": "NTPC Green Bond Series I", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.65, "coupon_frequency": "semi_annual", "issue_date": "2024-04-01", "maturity_date": "2034-04-01", "credit_rating": "AAA", "rating_agency": "CARE", "listing_exchange": "NSE", "sector": "Power", "isin_status": "Active"},
    {"isin": "INE030A08336", "issuer_name": "NTPC Limited", "issue_name": "NTPC Green Bond Series II", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.55, "coupon_frequency": "semi_annual", "issue_date": "2024-10-01", "maturity_date": "2034-10-01", "credit_rating": "AAA", "rating_agency": "CARE", "listing_exchange": "NSE", "sector": "Power", "isin_status": "Active"},
    {"isin": "INE121A08376", "issuer_name": "Power Finance Corporation Limited", "issue_name": "PFC Bond Series 2028", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 8.05, "coupon_frequency": "annual", "issue_date": "2023-11-01", "maturity_date": "2028-11-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "BSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE134E08KK0", "issuer_name": "REC Limited", "issue_name": "REC Bond Tranche VIII", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.95, "coupon_frequency": "annual", "issue_date": "2024-02-01", "maturity_date": "2029-02-01", "credit_rating": "AAA", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE134E08KL8", "issuer_name": "REC Limited", "issue_name": "REC Bond Tranche IX", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.85, "coupon_frequency": "annual", "issue_date": "2024-08-01", "maturity_date": "2034-08-01", "credit_rating": "AAA", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE245A08268", "issuer_name": "Indian Railway Finance Corporation", "issue_name": "IRFC Bond 2029", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.70, "coupon_frequency": "semi_annual", "issue_date": "2024-03-01", "maturity_date": "2029-03-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Infrastructure", "isin_status": "Active"},
    {"isin": "INE053F08338", "issuer_name": "National Highways Authority of India", "issue_name": "NHAI Bond 2030", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.60, "coupon_frequency": "semi_annual", "issue_date": "2024-01-15", "maturity_date": "2030-01-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Infrastructure", "isin_status": "Active"},
    
    # ============ Government Securities (G-Secs) ============
    {"isin": "IN0020230032", "issuer_name": "Government of India", "issue_name": "7.26% GOI 2033", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.26, "coupon_frequency": "semi_annual", "issue_date": "2023-01-15", "maturity_date": "2033-01-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN0020240018", "issuer_name": "Government of India", "issue_name": "7.18% GOI 2037", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.18, "coupon_frequency": "semi_annual", "issue_date": "2024-01-10", "maturity_date": "2037-01-10", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN0020220056", "issuer_name": "Government of India", "issue_name": "6.54% GOI 2032", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 6.54, "coupon_frequency": "semi_annual", "issue_date": "2022-06-15", "maturity_date": "2032-06-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN0020240026", "issuer_name": "Government of India", "issue_name": "7.10% GOI 2034", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.10, "coupon_frequency": "semi_annual", "issue_date": "2024-04-01", "maturity_date": "2034-04-01", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN0020250012", "issuer_name": "Government of India", "issue_name": "6.92% GOI 2039", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 6.92, "coupon_frequency": "semi_annual", "issue_date": "2025-01-15", "maturity_date": "2039-01-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    
    # ============ State Development Loans (SDLs) ============
    {"isin": "IN2820230124", "issuer_name": "Government of Maharashtra", "issue_name": "Maharashtra SDL 2033", "instrument_type": "SDL", "face_value": 10000, "coupon_rate": 7.45, "coupon_frequency": "semi_annual", "issue_date": "2023-06-01", "maturity_date": "2033-06-01", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN0920240086", "issuer_name": "Government of Gujarat", "issue_name": "Gujarat SDL 2034", "instrument_type": "SDL", "face_value": 10000, "coupon_rate": 7.35, "coupon_frequency": "semi_annual", "issue_date": "2024-03-15", "maturity_date": "2034-03-15", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    {"isin": "IN1020240052", "issuer_name": "Government of Karnataka", "issue_name": "Karnataka SDL 2034", "instrument_type": "SDL", "face_value": 10000, "coupon_rate": 7.40, "coupon_frequency": "semi_annual", "issue_date": "2024-02-01", "maturity_date": "2034-02-01", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "listing_exchange": "NSE", "sector": "Government", "isin_status": "Active"},
    
    # ============ More Corporate Bonds ============
    {"isin": "INE001A08144", "issuer_name": "Housing Development Finance Corporation Limited", "issue_name": "HDFC Bond 2027", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 8.30, "coupon_frequency": "annual", "issue_date": "2022-09-01", "maturity_date": "2027-09-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Financial Services", "isin_status": "Active"},
    {"isin": "INE018A08178", "issuer_name": "LIC Housing Finance Limited", "issue_name": "LICHF NCD 2027", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.40, "coupon_frequency": "annual", "issue_date": "2024-02-15", "maturity_date": "2027-02-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Housing Finance", "isin_status": "Active"},
    {"isin": "INE028A08186", "issuer_name": "Bank of Baroda", "issue_name": "BOB Tier 2 Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.15, "coupon_frequency": "annual", "issue_date": "2024-03-01", "maturity_date": "2034-03-01", "credit_rating": "AA+", "rating_agency": "ICRA", "listing_exchange": "NSE", "sector": "Banking", "isin_status": "Active"},
    {"isin": "INE476A08256", "issuer_name": "Canara Bank", "issue_name": "Canara Bank AT1 Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.25, "coupon_frequency": "annual", "issue_date": "2024-01-15", "maturity_date": "Perpetual", "credit_rating": "AA", "rating_agency": "CARE", "listing_exchange": "BSE", "sector": "Banking", "isin_status": "Active"},
    {"isin": "INE917H08134", "issuer_name": "Axis Bank Limited", "issue_name": "Axis Bank Infrastructure Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.95, "coupon_frequency": "annual", "issue_date": "2024-04-01", "maturity_date": "2034-04-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "listing_exchange": "NSE", "sector": "Banking", "isin_status": "Active"},
]


def search_nsdl_database(
    query: str,
    search_type: str = "all",  # all, isin, company, rating
    instrument_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Search the NSDL-style bond database.
    
    Args:
        query: Search term (ISIN or company name)
        search_type: Type of search - all, isin, company, rating
        instrument_type: Filter by instrument type (NCD, BOND, GSEC, SDL)
        limit: Maximum results to return
    
    Returns:
        List of matching instruments
    """
    results = []
    query_upper = query.upper().strip()
    query_lower = query.lower().strip()
    
    for instrument in NSDL_BOND_DATABASE:
        # Skip if instrument type filter doesn't match
        if instrument_type and instrument.get("instrument_type") != instrument_type:
            continue
        
        match = False
        
        if search_type == "isin" or search_type == "all":
            # ISIN search (exact or partial)
            if query_upper in instrument.get("isin", ""):
                match = True
        
        if search_type == "company" or search_type == "all":
            # Company name search (partial, case-insensitive)
            issuer = instrument.get("issuer_name", "").lower()
            issue_name = instrument.get("issue_name", "").lower()
            if query_lower in issuer or query_lower in issue_name:
                match = True
        
        if search_type == "rating":
            # Credit rating search
            if query_upper == instrument.get("credit_rating", ""):
                match = True
        
        if match:
            results.append({
                **instrument,
                "source": "NSDL",
                "can_import": True
            })
            
            if len(results) >= limit:
                break
    
    return results


async def import_from_nsdl(isin: str) -> Dict:
    """
    Import a specific instrument from NSDL database into Security Master.
    
    Args:
        isin: The ISIN to import
    
    Returns:
        Dict with import result
    """
    # Find the instrument in NSDL database
    instrument_data = None
    for inst in NSDL_BOND_DATABASE:
        if inst.get("isin") == isin:
            instrument_data = inst
            break
    
    if not instrument_data:
        return {"success": False, "error": f"ISIN {isin} not found in NSDL database"}
    
    # Check if already exists in Security Master
    existing = await db.fi_instruments.find_one({"isin": isin})
    if existing:
        return {
            "success": False, 
            "error": f"ISIN {isin} already exists in Security Master",
            "existing_id": existing.get("instrument_id")
        }
    
    # Generate instrument ID
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
    
    instrument_id = f"FI-INS-{num:06d}"
    
    # Prepare document
    instrument_doc = {
        "id": instrument_id,
        "instrument_id": instrument_id,
        "isin": instrument_data["isin"],
        "issuer_name": instrument_data["issuer_name"],
        "issue_name": instrument_data.get("issue_name", ""),
        "instrument_type": instrument_data["instrument_type"],
        "face_value": float(instrument_data["face_value"]),
        "coupon_rate": float(instrument_data["coupon_rate"]),
        "coupon_frequency": instrument_data.get("coupon_frequency", "annual"),
        "issue_date": instrument_data.get("issue_date", ""),
        "maturity_date": instrument_data["maturity_date"],
        "credit_rating": instrument_data["credit_rating"],
        "rating_agency": instrument_data.get("rating_agency", ""),
        "day_count_convention": instrument_data.get("day_count_convention", "actual_365"),
        "current_market_price": float(instrument_data.get("face_value", 1000)),
        "listing_exchange": instrument_data.get("listing_exchange", "NSE"),
        "sector": instrument_data.get("sector", ""),
        "is_active": True,
        "source": "NSDL_IMPORT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Insert into database
    await db.fi_instruments.insert_one(instrument_doc)
    
    return {
        "success": True,
        "message": f"Successfully imported {isin}",
        "instrument_id": instrument_id,
        "instrument": {
            "isin": instrument_data["isin"],
            "issuer_name": instrument_data["issuer_name"],
            "instrument_type": instrument_data["instrument_type"],
            "coupon_rate": instrument_data["coupon_rate"],
            "credit_rating": instrument_data["credit_rating"]
        }
    }


# Export
__all__ = ["search_nsdl_database", "import_from_nsdl", "NSDL_BOND_DATABASE"]
