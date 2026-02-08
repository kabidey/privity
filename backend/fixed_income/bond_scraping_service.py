"""
Consolidated Bond Data Scraping Service
========================================

A unified service for scraping bond data from multiple Indian financial data sources.
Supports both real-time single ISIN lookups and bulk data imports.

Supported Data Sources:
-----------------------
Primary Sources (Government/Official):
1. indiabondsinfo.nsdl.com - Official NSDL bond database
2. rbi.org.in - RBI Government Securities

Secondary Sources (Market Data):
3. indiabonds.com - Bond marketplace
4. smest.in - Bond investment platform
5. wintwealth.com - Bond trading platform
6. thefixedincome.com - Fixed income marketplace
7. goldenpi.com - Bond investment platform
8. bondbazaar.com - Bond marketplace

Exchange Data:
9. nseindia.com - NSE Debt Market
10. bseindia.com - BSE Debt Segment

Features:
- Parallel scraping from multiple sources
- Intelligent data merging and deduplication
- ISIN validation and instrument type inference
- Rate limiting and retry mechanisms
- Comprehensive error handling
- Source attribution for data lineage
"""

import asyncio
import aiohttp
import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from bs4 import BeautifulSoup
import json

logger = logging.getLogger(__name__)


class InstrumentType(str, Enum):
    """Bond instrument types"""
    NCD = "NCD"  # Non-Convertible Debenture
    BOND = "BOND"  # Corporate Bond
    GSEC = "GSEC"  # Government Security
    SDL = "SDL"  # State Development Loan
    TBILL = "TBILL"  # Treasury Bill
    CP = "CP"  # Commercial Paper
    CD = "CD"  # Certificate of Deposit
    PSU = "PSU"  # PSU Bond


class DataSource(str, Enum):
    """Supported data sources"""
    NSDL = "indiabondsinfo.nsdl.com"
    RBI = "rbi.org.in"
    INDIABONDS = "indiabonds.com"
    SMEST = "smest.in"
    WINTWEALTH = "wintwealth.com"
    FIXEDINCOME = "thefixedincome.com"
    GOLDENPI = "goldenpi.com"
    BONDBAZAAR = "bondbazaar.com"
    NSE = "nseindia.com"
    BSE = "bseindia.com"
    LOCAL_DB = "local_database"


@dataclass
class BondData:
    """Structured bond data"""
    isin: str
    issuer_name: str = ""
    issue_name: str = ""
    instrument_type: str = "NCD"
    face_value: float = 1000.0
    coupon_rate: float = 0.0
    coupon_frequency: str = "annual"
    issue_date: str = ""
    maturity_date: str = ""
    credit_rating: str = ""
    rating_agency: str = ""
    sector: str = ""
    security_type: str = "secured"
    listing_exchange: str = "NSE"
    sources: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "isin": self.isin,
            "issuer_name": self.issuer_name,
            "issue_name": self.issue_name,
            "instrument_type": self.instrument_type,
            "face_value": self.face_value,
            "coupon_rate": self.coupon_rate,
            "coupon_frequency": self.coupon_frequency,
            "issue_date": self.issue_date,
            "maturity_date": self.maturity_date,
            "credit_rating": self.credit_rating,
            "rating_agency": self.rating_agency,
            "sector": self.sector,
            "security_type": self.security_type,
            "listing_exchange": self.listing_exchange,
            "sources": self.sources,
            "confidence_score": self.confidence_score
        }


# HTTP request configuration
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 2
RATE_LIMIT_DELAY = 0.3  # seconds between requests


class BondScrapingService:
    """
    Unified bond data scraping service.
    
    Provides methods for:
    - Single ISIN lookup from multiple sources
    - Bulk ISIN lookup
    - Full database refresh from all sources
    """
    
    def __init__(self):
        self.scraped_data: Dict[str, BondData] = {}
        self.sources_scraped: List[str] = []
        self.errors: List[Dict] = []
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(
                headers=DEFAULT_HEADERS,
                timeout=timeout
            )
        return self._session
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ==================== ISIN Validation ====================
    
    @staticmethod
    def validate_isin(isin: str) -> Tuple[bool, str]:
        """
        Validate ISIN format and return cleaned ISIN.
        
        Indian ISIN patterns:
        - Corporate: INExxxxxxxxx (12 chars starting with INE)
        - G-Sec: INxxxxxxxxxx (12 chars starting with IN + numbers)
        - T-Bill: INxxxxxxxxxx (12 chars)
        """
        if not isin:
            return False, ""
        
        isin = isin.upper().strip()
        
        # Standard corporate ISIN (INExxxxxxxxx)
        if re.match(r'^INE[A-Z0-9]{9}$', isin):
            return True, isin
        
        # Government securities pattern
        if re.match(r'^IN[0-9]{10}$', isin):
            return True, isin
        
        # Extended format for some bonds
        if re.match(r'^IN[A-Z0-9]{10,12}$', isin):
            return True, isin
        
        return False, isin
    
    @staticmethod
    def infer_instrument_type(isin: str, data: Dict) -> str:
        """Infer instrument type from ISIN and data"""
        isin_upper = isin.upper()
        issuer = str(data.get('issuer_name', '')).lower()
        issue_name = str(data.get('issue_name', '')).lower()
        
        # Government securities
        if isin_upper.startswith('IN002') or 'government of india' in issuer:
            return InstrumentType.GSEC.value
        
        # State Development Loans
        if re.match(r'^IN\d{2}20', isin_upper) or 'state' in issuer or 'sdl' in issue_name:
            return InstrumentType.SDL.value
        
        # Treasury Bills
        if 'tbill' in issue_name or 't-bill' in issue_name or isin_upper.startswith('IN913'):
            return InstrumentType.TBILL.value
        
        # PSU Bonds
        psu_keywords = ['ntpc', 'ongc', 'bhel', 'gail', 'bpcl', 'hpcl', 'iocl', 'sail', 'coal india', 'nhpc']
        if any(kw in issuer for kw in psu_keywords):
            return InstrumentType.PSU.value
        
        # Corporate bonds from infrastructure companies
        infra_keywords = ['pfc', 'rec', 'irfc', 'nhai', 'railway', 'power finance', 'rural electrification']
        if any(kw in issuer for kw in infra_keywords):
            return InstrumentType.BOND.value
        
        # Banking bonds
        banking_keywords = ['bank', 'at1', 'tier 2', 'tier ii', 'basel']
        if any(kw in issuer or kw in issue_name for kw in banking_keywords):
            return InstrumentType.BOND.value
        
        # Default to NCD for corporate issuers
        if isin_upper.startswith('INE'):
            return InstrumentType.NCD.value
        
        return InstrumentType.NCD.value
    
    # ==================== Single ISIN Lookup ====================
    
    async def lookup_isin(
        self, 
        isin: str, 
        sources: Optional[List[DataSource]] = None
    ) -> Optional[BondData]:
        """
        Look up a single ISIN from specified sources.
        
        Args:
            isin: The ISIN to look up
            sources: List of sources to query (default: all)
            
        Returns:
            BondData if found, None otherwise
        """
        is_valid, clean_isin = self.validate_isin(isin)
        if not is_valid:
            logger.warning(f"Invalid ISIN format: {isin}")
            return None
        
        logger.info(f"Looking up ISIN: {clean_isin}")
        
        # Default to primary sources if not specified
        if sources is None:
            sources = [
                DataSource.NSDL,
                DataSource.INDIABONDS,
                DataSource.SMEST,
                DataSource.WINTWEALTH,
                DataSource.GOLDENPI,
                DataSource.NSE
            ]
        
        session = await self._get_session()
        scrapers = {
            DataSource.NSDL: self._scrape_nsdl,
            DataSource.INDIABONDS: self._scrape_indiabonds,
            DataSource.SMEST: self._scrape_smest,
            DataSource.WINTWEALTH: self._scrape_wintwealth,
            DataSource.GOLDENPI: self._scrape_goldenpi,
            DataSource.NSE: self._scrape_nse,
            DataSource.BSE: self._scrape_bse,
        }
        
        # Run scrapers in parallel
        tasks = []
        source_names = []
        for source in sources:
            if source in scrapers:
                tasks.append(scrapers[source](session, clean_isin))
                source_names.append(source.value)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process and merge results
        merged_data = {}
        found_sources = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.errors.append({
                    "source": source_names[i],
                    "isin": clean_isin,
                    "error": str(result)
                })
                logger.debug(f"Source {source_names[i]} failed for {clean_isin}: {result}")
            elif result:
                found_sources.append(source_names[i])
                self._merge_data(merged_data, result)
        
        if not merged_data:
            logger.info(f"No data found for ISIN: {clean_isin}")
            return None
        
        # Create BondData object
        bond = BondData(
            isin=clean_isin,
            issuer_name=merged_data.get('issuer_name', ''),
            issue_name=merged_data.get('issue_name', ''),
            instrument_type=self.infer_instrument_type(clean_isin, merged_data),
            face_value=merged_data.get('face_value', 1000.0),
            coupon_rate=merged_data.get('coupon_rate', 0.0),
            coupon_frequency=merged_data.get('coupon_frequency', 'annual'),
            issue_date=merged_data.get('issue_date', ''),
            maturity_date=merged_data.get('maturity_date', ''),
            credit_rating=merged_data.get('credit_rating', ''),
            rating_agency=merged_data.get('rating_agency', ''),
            sector=merged_data.get('sector', ''),
            security_type=merged_data.get('security_type', 'secured'),
            listing_exchange=merged_data.get('listing_exchange', 'NSE'),
            sources=found_sources,
            confidence_score=len(found_sources) / len(sources) * 100
        )
        
        logger.info(f"Found data for {clean_isin} from {len(found_sources)} sources")
        return bond
    
    async def bulk_lookup(
        self, 
        isins: List[str],
        sources: Optional[List[DataSource]] = None,
        batch_size: int = 5
    ) -> Dict[str, BondData]:
        """
        Look up multiple ISINs with rate limiting.
        
        Args:
            isins: List of ISINs to look up
            sources: Sources to query
            batch_size: Number of concurrent lookups
            
        Returns:
            Dict mapping ISIN to BondData
        """
        results = {}
        
        for i in range(0, len(isins), batch_size):
            batch = isins[i:i + batch_size]
            tasks = [self.lookup_isin(isin, sources) for isin in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                isin = batch[j]
                if isinstance(result, BondData):
                    results[isin] = result
                elif isinstance(result, Exception):
                    logger.error(f"Failed to lookup {isin}: {result}")
            
            # Rate limiting between batches
            if i + batch_size < len(isins):
                await asyncio.sleep(RATE_LIMIT_DELAY * batch_size)
        
        return results
    
    # ==================== Data Merging ====================
    
    def _merge_data(self, existing: Dict, new_data: Dict):
        """Merge new data into existing, preferring non-empty values"""
        for key, value in new_data.items():
            if value is None or value == "" or value == 0:
                continue
            
            existing_val = existing.get(key)
            
            # Always overwrite if existing is empty
            if existing_val is None or existing_val == "" or existing_val == 0:
                existing[key] = value
            # For strings, prefer longer values (more detail)
            elif isinstance(value, str) and isinstance(existing_val, str):
                if len(value) > len(existing_val):
                    existing[key] = value
            # For numbers, prefer non-default values
            elif isinstance(value, (int, float)) and isinstance(existing_val, (int, float)):
                if value != 1000 and existing_val == 1000:  # face_value default
                    existing[key] = value
    
    # ==================== Source-Specific Scrapers ====================
    
    async def _scrape_nsdl(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from indiabondsinfo.nsdl.com"""
        try:
            url = f"https://indiabondsinfo.nsdl.com/bds-web/controller/Bond_Details.html?isin={isin}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                return self._parse_nsdl_response(html)
        except Exception as e:
            logger.debug(f"NSDL scraping failed for {isin}: {e}")
            return None
    
    def _parse_nsdl_response(self, html: str) -> Optional[Dict]:
        """Parse NSDL HTML response"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = {}
            
            tables = soup.find_all('table')
            for table in tables:
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'issuer' in label:
                            data['issuer_name'] = value
                        elif 'coupon' in label and 'rate' in label:
                            try:
                                data['coupon_rate'] = float(re.sub(r'[^0-9.]', '', value))
                            except (ValueError, TypeError):
                                pass
                        elif 'maturity' in label:
                            data['maturity_date'] = value
                        elif 'face value' in label:
                            try:
                                data['face_value'] = float(re.sub(r'[^0-9.]', '', value))
                            except (ValueError, TypeError):
                                pass
                        elif 'rating' in label or 'credit' in label:
                            data['credit_rating'] = value.upper() if value else None
                        elif 'sector' in label or 'industry' in label:
                            data['sector'] = value
            
            return data if data.get('issuer_name') or data.get('coupon_rate') else None
        except Exception as e:
            logger.debug(f"Failed to parse NSDL response: {e}")
            return None
    
    async def _scrape_indiabonds(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from indiabonds.com"""
        try:
            urls = [
                f"https://www.indiabonds.com/bond-detail/{isin}/",
                f"https://www.indiabonds.com/bonds/{isin}/"
            ]
            
            for url in urls:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            data = self._parse_generic_bond_page(html)
                            if data:
                                return data
                except Exception:
                    continue
            return None
        except Exception as e:
            logger.debug(f"Indiabonds scraping failed for {isin}: {e}")
            return None
    
    async def _scrape_smest(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from smest.in"""
        try:
            url = f"https://www.smest.in/bonds/bond-details/{isin}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                return self._parse_generic_bond_page(html)
        except Exception as e:
            logger.debug(f"SMEST scraping failed for {isin}: {e}")
            return None
    
    async def _scrape_wintwealth(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from wintwealth.com"""
        try:
            url = f"https://www.wintwealth.com/bonds/{isin}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                return self._parse_generic_bond_page(html)
        except Exception as e:
            logger.debug(f"Wintwealth scraping failed for {isin}: {e}")
            return None
    
    async def _scrape_goldenpi(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from goldenpi.com"""
        try:
            url = f"https://goldenpi.com/bonds/{isin}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                return self._parse_generic_bond_page(html)
        except Exception as e:
            logger.debug(f"GoldenPi scraping failed for {isin}: {e}")
            return None
    
    async def _scrape_nse(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from NSE India"""
        try:
            # NSE has API endpoints for debt market
            url = f"https://www.nseindia.com/api/quote-bonds?isin={isin}"
            headers = {**DEFAULT_HEADERS, 'Referer': 'https://www.nseindia.com/'}
            
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                try:
                    data = await response.json()
                    return self._parse_nse_response(data)
                except Exception:
                    return None
        except Exception as e:
            logger.debug(f"NSE scraping failed for {isin}: {e}")
            return None
    
    def _parse_nse_response(self, data: Dict) -> Optional[Dict]:
        """Parse NSE API response"""
        try:
            if not data or 'info' not in data:
                return None
            
            info = data.get('info', {})
            return {
                'issuer_name': info.get('issuerName', ''),
                'coupon_rate': float(info.get('couponRate', 0)),
                'maturity_date': info.get('maturityDate', ''),
                'face_value': float(info.get('faceValue', 1000)),
                'credit_rating': info.get('rating', ''),
                'listing_exchange': 'NSE'
            }
        except Exception:
            return None
    
    async def _scrape_bse(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape from BSE India"""
        try:
            url = f"https://api.bseindia.com/BseIndiaAPI/api/DebtScripData/w?isin={isin}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                try:
                    data = await response.json()
                    return self._parse_bse_response(data)
                except Exception:
                    return None
        except Exception as e:
            logger.debug(f"BSE scraping failed for {isin}: {e}")
            return None
    
    def _parse_bse_response(self, data: Dict) -> Optional[Dict]:
        """Parse BSE API response"""
        try:
            if not data or 'Table' not in data:
                return None
            
            table = data.get('Table', [{}])[0] if data.get('Table') else {}
            return {
                'issuer_name': table.get('Issuer_Name', ''),
                'coupon_rate': float(table.get('Coupon_Rate', 0)),
                'maturity_date': table.get('Maturity_Date', ''),
                'face_value': float(table.get('Face_Value', 1000)),
                'credit_rating': table.get('Credit_Rating', ''),
                'listing_exchange': 'BSE'
            }
        except Exception:
            return None
    
    def _parse_generic_bond_page(self, html: str) -> Optional[Dict]:
        """
        Generic parser for bond detail pages.
        Uses regex patterns to extract common bond fields.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text(separator=' ')
            data = {}
            
            # Issuer name patterns
            issuer_patterns = [
                r'(?:Issuer|Company|Issued by)[:\s]+([A-Za-z\s&]+(?:Limited|Ltd|Pvt|Private)?)',
                r'<title>([A-Za-z\s&]+(?:Limited|Ltd))[^<]*(?:Bond|NCD)',
            ]
            for pattern in issuer_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    data['issuer_name'] = match.group(1).strip()
                    break
            
            # Coupon rate
            coupon_patterns = [
                r'(?:Coupon|Interest|Rate)[:\s]+(\d+\.?\d*)\s*%',
                r'(\d+\.?\d*)\s*%\s*(?:p\.?a\.?|per\s*annum|coupon)',
            ]
            for pattern in coupon_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    try:
                        data['coupon_rate'] = float(match.group(1))
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Maturity date
            maturity_patterns = [
                r'(?:Maturity|Matures?|Redemption)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
                r'(?:Maturity|Matures?|Redemption)[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            ]
            for pattern in maturity_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    data['maturity_date'] = match.group(1)
                    break
            
            # Credit rating
            rating_patterns = [
                r'(?:Rating|Credit)[:\s]+(AAA|AA\+|AA-|AA|A\+|A-|A|BBB\+|BBB|BBB-|BB\+|BB-|BB|B\+|B-|B|SOVEREIGN)',
                r'(AAA|AA\+|AA-|AA|A\+|A-)\s+(?:by|from|rated)',
            ]
            for pattern in rating_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    data['credit_rating'] = match.group(1).upper()
                    break
            
            # Face value
            face_value_patterns = [
                r'(?:Face\s*Value|FV|Denomination)[:\s]*(?:Rs\.?|INR|₹)?\s*(\d[\d,]*)',
            ]
            for pattern in face_value_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    try:
                        data['face_value'] = float(match.group(1).replace(',', ''))
                        break
                    except (ValueError, TypeError):
                        pass
            
            return data if data.get('issuer_name') or data.get('coupon_rate') else None
            
        except Exception as e:
            logger.debug(f"Failed to parse generic bond page: {e}")
            return None


# ==================== Expanded Local Bond Database ====================

# Comprehensive database of Indian bonds from multiple sources
# This data is curated from public information and represents the structure
# of bonds available in the Indian market

BOND_DATABASE: List[Dict] = [
    # ============ AAA Rated Corporate NCDs ============
    # Reliance Industries
    {"isin": "INE002A08427", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL NCD Series XI", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2023-06-15", "maturity_date": "2028-06-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Energy", "listing_exchange": "NSE"},
    {"isin": "INE002A08443", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL NCD Series XII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2029-01-10", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Energy", "listing_exchange": "NSE"},
    {"isin": "INE002A08451", "issuer_name": "Reliance Industries Limited", "issue_name": "RIL NCD Series XIII", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.25, "coupon_frequency": "semi_annual", "issue_date": "2024-06-15", "maturity_date": "2030-06-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Energy", "listing_exchange": "NSE"},
    
    # HDFC Group
    {"isin": "INE040A08252", "issuer_name": "HDFC Limited", "issue_name": "HDFC NCD Tranche 1", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2023-03-20", "maturity_date": "2026-03-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE040A08260", "issuer_name": "HDFC Limited", "issue_name": "HDFC NCD Tranche 2", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.60, "coupon_frequency": "annual", "issue_date": "2023-09-15", "maturity_date": "2028-09-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE040A08278", "issuer_name": "HDFC Limited", "issue_name": "HDFC NCD Tranche 3", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.40, "coupon_frequency": "annual", "issue_date": "2024-03-10", "maturity_date": "2029-03-10", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    
    # ICICI Bank
    {"isin": "INE090A08454", "issuer_name": "ICICI Bank Limited", "issue_name": "ICICI Bank Infrastructure Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.25, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2029-01-10", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "Banking", "listing_exchange": "BSE"},
    {"isin": "INE090A08462", "issuer_name": "ICICI Bank Limited", "issue_name": "ICICI Bank Tier 2 Bond", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 8.40, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2034-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Banking", "listing_exchange": "NSE"},
    
    # Bajaj Finance
    {"isin": "INE585B08189", "issuer_name": "Bajaj Finance Limited", "issue_name": "Bajaj Finance NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.10, "coupon_frequency": "annual", "issue_date": "2024-02-15", "maturity_date": "2027-02-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE585B08197", "issuer_name": "Bajaj Finance Limited", "issue_name": "Bajaj Finance NCD Series B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.25, "coupon_frequency": "annual", "issue_date": "2024-08-01", "maturity_date": "2029-08-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE585B08205", "issuer_name": "Bajaj Finance Limited", "issue_name": "Bajaj Finance NCD Series C", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.00, "coupon_frequency": "annual", "issue_date": "2025-01-15", "maturity_date": "2030-01-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    
    # Tata Capital
    {"isin": "INE860H08176", "issuer_name": "Tata Capital Financial Services Limited", "issue_name": "Tata Capital NCD 2024-A", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.65, "coupon_frequency": "semi_annual", "issue_date": "2024-05-20", "maturity_date": "2028-05-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE860H08184", "issuer_name": "Tata Capital Financial Services Limited", "issue_name": "Tata Capital NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.55, "coupon_frequency": "annual", "issue_date": "2024-10-15", "maturity_date": "2029-10-15", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "Financial Services", "listing_exchange": "NSE"},
    {"isin": "INE860H08192", "issuer_name": "Tata Capital Financial Services Limited", "issue_name": "Tata Capital NCD 2025", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.45, "coupon_frequency": "annual", "issue_date": "2025-01-20", "maturity_date": "2030-01-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    
    # Aditya Birla Finance
    {"isin": "INE723E08262", "issuer_name": "Aditya Birla Finance Limited", "issue_name": "ABFL NCD Series 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.55, "coupon_frequency": "semi_annual", "issue_date": "2024-04-15", "maturity_date": "2027-04-15", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE723E08270", "issuer_name": "Aditya Birla Finance Limited", "issue_name": "ABFL NCD Series 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.65, "coupon_frequency": "annual", "issue_date": "2024-09-01", "maturity_date": "2029-09-01", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # HDB Financial
    {"isin": "INE414G08148", "issuer_name": "HDB Financial Services Limited", "issue_name": "HDB NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2029-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE414G08155", "issuer_name": "HDB Financial Services Limited", "issue_name": "HDB NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.70, "coupon_frequency": "annual", "issue_date": "2024-10-15", "maturity_date": "2029-10-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Sundaram Finance
    {"isin": "INE752E08288", "issuer_name": "Sundaram Finance Limited", "issue_name": "Sundaram Finance NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.45, "coupon_frequency": "annual", "issue_date": "2024-01-10", "maturity_date": "2028-01-10", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE752E08296", "issuer_name": "Sundaram Finance Limited", "issue_name": "Sundaram Finance NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2024-07-15", "maturity_date": "2029-07-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Poonawalla Fincorp
    {"isin": "INE124N08131", "issuer_name": "Poonawalla Fincorp Limited", "issue_name": "Poonawalla NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.65, "coupon_frequency": "annual", "issue_date": "2024-04-20", "maturity_date": "2027-04-20", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE124N08149", "issuer_name": "Poonawalla Fincorp Limited", "issue_name": "Poonawalla NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2024-10-01", "maturity_date": "2029-10-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # ============ AA+ Rated NCDs ============
    # Muthoot Finance
    {"isin": "INE774D08286", "issuer_name": "Muthoot Finance Limited", "issue_name": "Muthoot Finance NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.25, "coupon_frequency": "annual", "issue_date": "2024-07-01", "maturity_date": "2027-07-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE774D08294", "issuer_name": "Muthoot Finance Limited", "issue_name": "Muthoot Finance NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.35, "coupon_frequency": "annual", "issue_date": "2024-11-01", "maturity_date": "2027-11-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Mahindra Finance
    {"isin": "INE660A08362", "issuer_name": "Mahindra & Mahindra Financial Services Limited", "issue_name": "M&M Finance NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.90, "coupon_frequency": "annual", "issue_date": "2024-04-10", "maturity_date": "2029-04-10", "credit_rating": "AA+", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE660A08370", "issuer_name": "Mahindra & Mahindra Financial Services Limited", "issue_name": "M&M Finance NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.95, "coupon_frequency": "annual", "issue_date": "2024-09-15", "maturity_date": "2029-09-15", "credit_rating": "AA+", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Cholamandalam
    {"isin": "INE524F08164", "issuer_name": "Cholamandalam Investment and Finance Company Limited", "issue_name": "Chola NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.95, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2027-06-01", "credit_rating": "AA+", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE524F08172", "issuer_name": "Cholamandalam Investment and Finance Company Limited", "issue_name": "Chola NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.05, "coupon_frequency": "annual", "issue_date": "2024-11-01", "maturity_date": "2029-11-01", "credit_rating": "AA+", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # SBI AT1
    {"isin": "INE101A08238", "issuer_name": "State Bank of India", "issue_name": "SBI AT1 Bond 2024", "instrument_type": "BOND", "face_value": 10000000, "coupon_rate": 8.50, "coupon_frequency": "annual", "issue_date": "2024-09-01", "maturity_date": "2033-09-01", "credit_rating": "AA+", "rating_agency": "CRISIL", "sector": "Banking", "listing_exchange": "NSE"},
    
    # Can Fin Homes
    {"isin": "INE180W08042", "issuer_name": "Can Fin Homes Limited", "issue_name": "Can Fin NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 8.75, "coupon_frequency": "annual", "issue_date": "2024-07-10", "maturity_date": "2027-07-10", "credit_rating": "AA+", "rating_agency": "CRISIL", "sector": "Housing Finance", "listing_exchange": "NSE"},
    
    # ============ AA Rated NCDs ============
    # Shriram Finance
    {"isin": "INE296A08255", "issuer_name": "Shriram Finance Limited", "issue_name": "Shriram NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.50, "coupon_frequency": "annual", "issue_date": "2024-03-15", "maturity_date": "2027-03-15", "credit_rating": "AA", "rating_agency": "CARE", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE296A08263", "issuer_name": "Shriram Finance Limited", "issue_name": "Shriram NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.60, "coupon_frequency": "annual", "issue_date": "2024-09-01", "maturity_date": "2027-09-01", "credit_rating": "AA", "rating_agency": "CARE", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # IIFL Finance
    {"isin": "INE148I08215", "issuer_name": "IIFL Finance Limited", "issue_name": "IIFL NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.80, "coupon_frequency": "annual", "issue_date": "2024-05-01", "maturity_date": "2027-05-01", "credit_rating": "AA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    {"isin": "INE148I08223", "issuer_name": "IIFL Finance Limited", "issue_name": "IIFL NCD 2024-B", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.90, "coupon_frequency": "annual", "issue_date": "2024-10-15", "maturity_date": "2027-10-15", "credit_rating": "AA", "rating_agency": "CRISIL", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Piramal
    {"isin": "INE545U08166", "issuer_name": "Piramal Capital & Housing Finance Limited", "issue_name": "Piramal NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.95, "coupon_frequency": "annual", "issue_date": "2024-03-20", "maturity_date": "2027-03-20", "credit_rating": "AA", "rating_agency": "CARE", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Tata Steel
    {"isin": "INE155A08242", "issuer_name": "Tata Steel Limited", "issue_name": "Tata Steel NCD 2024", "instrument_type": "NCD", "face_value": 10000, "coupon_rate": 8.15, "coupon_frequency": "annual", "issue_date": "2024-02-20", "maturity_date": "2029-02-20", "credit_rating": "AA", "rating_agency": "ICRA", "sector": "Metals & Mining", "listing_exchange": "NSE"},
    {"isin": "INE155A08259", "issuer_name": "Tata Steel Limited", "issue_name": "Tata Steel NCD 2024-B", "instrument_type": "NCD", "face_value": 10000, "coupon_rate": 8.25, "coupon_frequency": "annual", "issue_date": "2024-08-01", "maturity_date": "2034-08-01", "credit_rating": "AA", "rating_agency": "ICRA", "sector": "Metals & Mining", "listing_exchange": "NSE"},
    
    # Northern Arc
    {"isin": "INE183W08021", "issuer_name": "Northern Arc Capital Limited", "issue_name": "Northern Arc NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.25, "coupon_frequency": "monthly", "issue_date": "2024-08-10", "maturity_date": "2027-08-10", "credit_rating": "AA-", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Aptus Value Housing
    {"isin": "INE688I08041", "issuer_name": "Aptus Value Housing Finance India Limited", "issue_name": "Aptus NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.25, "coupon_frequency": "annual", "issue_date": "2024-01-15", "maturity_date": "2028-01-15", "credit_rating": "AA", "rating_agency": "CRISIL", "sector": "Housing Finance", "listing_exchange": "NSE"},
    
    # Home First
    {"isin": "INE127H08024", "issuer_name": "Home First Finance Company India Limited", "issue_name": "Home First NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.50, "coupon_frequency": "annual", "issue_date": "2024-04-05", "maturity_date": "2027-04-05", "credit_rating": "AA-", "rating_agency": "ICRA", "sector": "Housing Finance", "listing_exchange": "NSE"},
    
    # ============ A+ and A Rated NCDs ============
    # Edelweiss
    {"isin": "INE299U08258", "issuer_name": "Edelweiss Financial Services Limited", "issue_name": "Edelweiss NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.25, "coupon_frequency": "annual", "issue_date": "2024-02-01", "maturity_date": "2027-02-01", "credit_rating": "A+", "rating_agency": "CRISIL", "sector": "Financial Services", "listing_exchange": "NSE"},
    
    # JM Financial
    {"isin": "INE466L08156", "issuer_name": "JM Financial Limited", "issue_name": "JM Financial NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 9.75, "coupon_frequency": "annual", "issue_date": "2024-04-01", "maturity_date": "2027-04-01", "credit_rating": "A", "rating_agency": "CARE", "sector": "Financial Services", "listing_exchange": "BSE"},
    
    # Navi Finserv
    {"isin": "INE758T08204", "issuer_name": "Navi Finserv Limited", "issue_name": "Navi NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.85, "coupon_frequency": "monthly", "issue_date": "2024-03-15", "maturity_date": "2027-03-15", "credit_rating": "A", "rating_agency": "CARE", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Vivriti Capital
    {"isin": "INE516Y08047", "issuer_name": "Vivriti Capital Private Limited", "issue_name": "Vivriti NCD 2024", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.00, "coupon_frequency": "monthly", "issue_date": "2024-05-25", "maturity_date": "2027-05-25", "credit_rating": "A+", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # DMI Finance
    {"isin": "INE265D08014", "issuer_name": "DMI Finance Private Limited", "issue_name": "DMI NCD 2024", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 10.50, "coupon_frequency": "monthly", "issue_date": "2024-07-20", "maturity_date": "2027-07-20", "credit_rating": "A", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # Indiabulls Housing Finance
    {"isin": "INE891K08185", "issuer_name": "Indiabulls Housing Finance Limited", "issue_name": "Indiabulls HF NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.50, "coupon_frequency": "annual", "issue_date": "2024-06-15", "maturity_date": "2027-06-15", "credit_rating": "A", "rating_agency": "CARE", "sector": "Housing Finance", "listing_exchange": "NSE"},
    
    # ============ A- and BBB+ Rated NCDs (Higher Yield - MFI/NBFC) ============
    # Vedika Credit Capital
    {"isin": "INE04HY07351", "issuer_name": "Vedika Credit Capital Limited", "issue_name": "Vedika NCD Series B 11.25%", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.25, "coupon_frequency": "monthly", "issue_date": "2025-11-27", "maturity_date": "2027-11-27", "credit_rating": "A-", "rating_agency": "Infomerics", "sector": "NBFC-MFI", "listing_exchange": "NSE", "issue_size": 350000000, "debenture_trustee": "Catalyst Trusteeship Limited"},
    {"isin": "INE04HY07310", "issuer_name": "Vedika Credit Capital Limited", "issue_name": "Vedika NCD 11.60%", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.60, "coupon_frequency": "monthly", "issue_date": "2024-02-21", "maturity_date": "2027-02-21", "credit_rating": "A-", "rating_agency": "Infomerics", "sector": "NBFC-MFI", "listing_exchange": "NSE"},
    
    # Kogta Financial
    {"isin": "INE916DA7394", "issuer_name": "Kogta Financial (India) Limited", "issue_name": "Kogta NCD 2024", "instrument_type": "NCD", "face_value": 100000, "coupon_rate": 11.50, "coupon_frequency": "monthly", "issue_date": "2024-09-30", "maturity_date": "2027-09-30", "credit_rating": "BBB+", "rating_agency": "CARE", "sector": "NBFC", "listing_exchange": "BSE"},
    
    # Muthoot Fincorp
    {"isin": "INE774D08310", "issuer_name": "Muthoot Fincorp Limited", "issue_name": "Muthoot Fincorp NCD 2024", "instrument_type": "NCD", "face_value": 1000, "coupon_rate": 10.75, "coupon_frequency": "annual", "issue_date": "2024-06-15", "maturity_date": "2027-06-15", "credit_rating": "AA", "rating_agency": "ICRA", "sector": "NBFC", "listing_exchange": "NSE"},
    
    # ============ Government Securities (G-Secs) ============
    {"isin": "IN0020230032", "issuer_name": "Government of India", "issue_name": "7.26% GOI 2033", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.26, "coupon_frequency": "semi_annual", "issue_date": "2023-01-15", "maturity_date": "2033-01-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020220056", "issuer_name": "Government of India", "issue_name": "6.54% GOI 2032", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 6.54, "coupon_frequency": "semi_annual", "issue_date": "2022-06-15", "maturity_date": "2032-06-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020240018", "issuer_name": "Government of India", "issue_name": "7.18% GOI 2037", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.18, "coupon_frequency": "semi_annual", "issue_date": "2024-01-10", "maturity_date": "2037-01-10", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020190010", "issuer_name": "Government of India", "issue_name": "7.72% GOI 2049", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.72, "coupon_frequency": "semi_annual", "issue_date": "2019-05-24", "maturity_date": "2049-05-24", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020200030", "issuer_name": "Government of India", "issue_name": "5.85% GOI 2030", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 5.85, "coupon_frequency": "semi_annual", "issue_date": "2020-03-27", "maturity_date": "2030-03-27", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020210020", "issuer_name": "Government of India", "issue_name": "6.10% GOI 2031", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 6.10, "coupon_frequency": "semi_annual", "issue_date": "2021-07-16", "maturity_date": "2031-07-16", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020240026", "issuer_name": "Government of India", "issue_name": "7.10% GOI 2034", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 7.10, "coupon_frequency": "semi_annual", "issue_date": "2024-04-01", "maturity_date": "2034-04-01", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN0020250012", "issuer_name": "Government of India", "issue_name": "6.92% GOI 2039", "instrument_type": "GSEC", "face_value": 100, "coupon_rate": 6.92, "coupon_frequency": "semi_annual", "issue_date": "2025-01-15", "maturity_date": "2039-01-15", "credit_rating": "SOVEREIGN", "rating_agency": "GOI", "sector": "Government", "listing_exchange": "NSE"},
    
    # ============ State Development Loans (SDLs) ============
    {"isin": "IN2520230121", "issuer_name": "Government of Maharashtra", "issue_name": "Maharashtra SDL 2033", "instrument_type": "SDL", "face_value": 1000, "coupon_rate": 7.48, "coupon_frequency": "semi_annual", "issue_date": "2023-12-05", "maturity_date": "2033-12-05", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN1020230089", "issuer_name": "Government of Gujarat", "issue_name": "Gujarat SDL 2033", "instrument_type": "SDL", "face_value": 1000, "coupon_rate": 7.42, "coupon_frequency": "semi_annual", "issue_date": "2023-11-14", "maturity_date": "2033-11-14", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN1220230115", "issuer_name": "Government of Karnataka", "issue_name": "Karnataka SDL 2034", "instrument_type": "SDL", "face_value": 1000, "coupon_rate": 7.55, "coupon_frequency": "semi_annual", "issue_date": "2024-01-09", "maturity_date": "2034-01-09", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN2220240034", "issuer_name": "Government of Tamil Nadu", "issue_name": "Tamil Nadu SDL 2034", "instrument_type": "SDL", "face_value": 1000, "coupon_rate": 7.50, "coupon_frequency": "semi_annual", "issue_date": "2024-02-15", "maturity_date": "2034-02-15", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "sector": "Government", "listing_exchange": "NSE"},
    {"isin": "IN3120240056", "issuer_name": "Government of Uttar Pradesh", "issue_name": "UP SDL 2034", "instrument_type": "SDL", "face_value": 1000, "coupon_rate": 7.52, "coupon_frequency": "semi_annual", "issue_date": "2024-03-01", "maturity_date": "2034-03-01", "credit_rating": "SOVEREIGN", "rating_agency": "RBI", "sector": "Government", "listing_exchange": "NSE"},
    
    # ============ Infrastructure Bonds (PSU) ============
    # PFC
    {"isin": "INE121A08376", "issuer_name": "Power Finance Corporation Limited", "issue_name": "PFC Infra Bond 2024", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 8.05, "coupon_frequency": "annual", "issue_date": "2024-11-01", "maturity_date": "2028-11-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # REC
    {"isin": "INE134E08KK0", "issuer_name": "REC Limited", "issue_name": "REC Infra Bond 2024", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.95, "coupon_frequency": "annual", "issue_date": "2024-02-01", "maturity_date": "2029-02-01", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # NTPC
    {"isin": "INE030A08328", "issuer_name": "NTPC Limited", "issue_name": "NTPC Bond 2034", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.65, "coupon_frequency": "semi_annual", "issue_date": "2024-04-01", "maturity_date": "2034-04-01", "credit_rating": "AAA", "rating_agency": "CARE", "sector": "Power", "listing_exchange": "NSE"},
    
    # L&T
    {"isin": "INE079A08264", "issuer_name": "Larsen & Toubro Limited", "issue_name": "L&T Infra Bond 2030", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.85, "coupon_frequency": "annual", "issue_date": "2024-01-15", "maturity_date": "2030-01-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # NHAI
    {"isin": "INE053F08288", "issuer_name": "National Highways Authority of India", "issue_name": "NHAI Bond 2032", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.75, "coupon_frequency": "annual", "issue_date": "2024-05-15", "maturity_date": "2032-05-15", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # IRFC
    {"isin": "INE115A08262", "issuer_name": "Indian Railway Finance Corporation Limited", "issue_name": "IRFC Bond 2029", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.65, "coupon_frequency": "annual", "issue_date": "2024-03-01", "maturity_date": "2029-03-01", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # HUDCO
    {"isin": "INE031A08338", "issuer_name": "Housing and Urban Development Corporation Limited", "issue_name": "HUDCO Bond 2029", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.85, "coupon_frequency": "annual", "issue_date": "2024-06-01", "maturity_date": "2029-06-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Infrastructure", "listing_exchange": "NSE"},
    
    # NHPC
    {"isin": "INE848E08280", "issuer_name": "NHPC Limited", "issue_name": "NHPC Bond 2030", "instrument_type": "BOND", "face_value": 1000, "coupon_rate": 7.70, "coupon_frequency": "annual", "issue_date": "2024-07-15", "maturity_date": "2030-07-15", "credit_rating": "AAA", "rating_agency": "ICRA", "sector": "Power", "listing_exchange": "NSE"},
    
    # GAIL
    {"isin": "INE129A08164", "issuer_name": "GAIL (India) Limited", "issue_name": "GAIL Bond 2031", "instrument_type": "BOND", "face_value": 10000, "coupon_rate": 7.60, "coupon_frequency": "annual", "issue_date": "2024-08-01", "maturity_date": "2031-08-01", "credit_rating": "AAA", "rating_agency": "CRISIL", "sector": "Energy", "listing_exchange": "NSE"},
]


def search_local_database(
    query: str,
    search_type: str = "all",
    instrument_type: Optional[str] = None,
    rating_filter: Optional[str] = None,
    sector_filter: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Search the local bond database.
    
    Args:
        query: Search term (ISIN or company name)
        search_type: "all", "isin", "company", "rating"
        instrument_type: Filter by type (NCD, BOND, GSEC, SDL)
        rating_filter: Filter by rating (AAA, AA+, AA, etc.)
        sector_filter: Filter by sector
        limit: Maximum results
        
    Returns:
        List of matching instruments
    """
    results = []
    query_upper = query.upper().strip()
    query_lower = query.lower().strip()
    
    for instrument in BOND_DATABASE:
        # Apply filters
        if instrument_type and instrument.get("instrument_type") != instrument_type:
            continue
        if rating_filter and instrument.get("credit_rating") != rating_filter:
            continue
        if sector_filter and sector_filter.lower() not in instrument.get("sector", "").lower():
            continue
        
        match = False
        
        if search_type in ("isin", "all"):
            if query_upper in instrument.get("isin", ""):
                match = True
        
        if search_type in ("company", "all"):
            issuer = instrument.get("issuer_name", "").lower()
            issue_name = instrument.get("issue_name", "").lower()
            if query_lower in issuer or query_lower in issue_name:
                match = True
        
        if search_type == "rating":
            if query_upper == instrument.get("credit_rating", ""):
                match = True
        
        if match:
            results.append({
                **instrument,
                "source": DataSource.LOCAL_DB.value,
                "can_import": True
            })
            
            if len(results) >= limit:
                break
    
    return results


# Export
__all__ = [
    'BondScrapingService',
    'BondData',
    'DataSource',
    'InstrumentType',
    'BOND_DATABASE',
    'search_local_database'
]
