"""
Live NSDL Lookup Service
Real-time web scraping for bond data when ISIN is not found in local database.

This service attempts to fetch bond data from multiple sources:
1. indiabondsinfo.nsdl.com - Official NSDL database
2. indiabonds.com - Bond marketplace
3. smest.in - Bond investment platform

Features:
- Parallel scraping from all 3 sources
- Data merging and validation
- Auto-import to SecurityMaster on successful lookup
- Rate limiting and error handling
"""
import asyncio
import aiohttp
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from bs4 import BeautifulSoup

from database import db

logger = logging.getLogger(__name__)

# Common headers for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Request timeout in seconds
REQUEST_TIMEOUT = 10


class LiveBondLookup:
    """Live bond data lookup service"""
    
    def __init__(self):
        self.scraped_data: Dict[str, Any] = {}
        self.sources_tried: List[str] = []
        self.errors: List[str] = []
    
    async def lookup_isin(self, isin: str) -> Optional[Dict]:
        """
        Perform live lookup for a specific ISIN from all sources.
        
        Args:
            isin: The ISIN to look up (e.g., "INE002A08427")
            
        Returns:
            Dict with bond data if found, None otherwise
        """
        logger.info(f"Starting live lookup for ISIN: {isin}")
        
        # Validate ISIN format (Indian ISINs start with IN)
        if not self._validate_isin(isin):
            logger.warning(f"Invalid ISIN format: {isin}")
            return None
        
        # Try all sources in parallel
        async with aiohttp.ClientSession(headers=HEADERS, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
            tasks = [
                self._scrape_nsdl_indiabondsinfo(session, isin),
                self._scrape_indiabonds(session, isin),
                self._scrape_smest(session, isin)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                source_names = ["indiabondsinfo.nsdl.com", "indiabonds.com", "smest.in"]
                if isinstance(result, Exception):
                    self.errors.append(f"{source_names[i]}: {str(result)}")
                    logger.warning(f"Scraping {source_names[i]} failed: {result}")
                elif result:
                    self._merge_data(result, source_names[i])
        
        # Return merged data if we found anything
        if self.scraped_data:
            self.scraped_data["isin"] = isin
            self.scraped_data["sources_found"] = self.sources_tried
            logger.info(f"Found data for {isin} from sources: {self.sources_tried}")
            return self.scraped_data
        
        logger.info(f"No data found for ISIN: {isin}")
        return None
    
    def _validate_isin(self, isin: str) -> bool:
        """Validate ISIN format"""
        # Indian ISIN format: INExxxxxx or INxxxxxxxxxxx
        if not isin:
            return False
        isin = isin.upper().strip()
        # Standard Indian ISIN pattern
        if re.match(r'^IN[A-Z0-9]{10}$', isin):
            return True
        # G-Sec pattern (shorter)
        if re.match(r'^IN[0-9]{10,12}$', isin):
            return True
        return False
    
    def _merge_data(self, new_data: Dict, source: str):
        """Merge new data with existing scraped data"""
        self.sources_tried.append(source)
        
        for key, value in new_data.items():
            if value is not None and value != "" and value != 0:
                # Keep existing value if more complete
                existing = self.scraped_data.get(key)
                if existing is None or existing == "" or existing == 0:
                    self.scraped_data[key] = value
                elif isinstance(value, str) and isinstance(existing, str):
                    # Keep longer/more detailed string
                    if len(str(value)) > len(str(existing)):
                        self.scraped_data[key] = value
    
    async def _scrape_nsdl_indiabondsinfo(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape bond data from indiabondsinfo.nsdl.com"""
        try:
            # NSDL India Bonds Info URL format
            url = f"https://indiabondsinfo.nsdl.com/bds-web/controller/Bond_Details.html?issuer_code=&sec_code=&isin={isin}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.debug(f"NSDL returned status {response.status} for {isin}")
                    return None
                
                html = await response.text()
                return self._parse_nsdl_html(html, isin)
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping NSDL for {isin}")
            return None
        except Exception as e:
            logger.warning(f"Error scraping NSDL for {isin}: {e}")
            return None
    
    def _parse_nsdl_html(self, html: str, isin: str) -> Optional[Dict]:
        """Parse NSDL HTML response to extract bond data"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for bond details table
            data = {}
            
            # Find key-value pairs in tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        # Map common fields
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
                        elif 'frequency' in label:
                            freq_lower = value.lower()
                            if 'month' in freq_lower:
                                data['coupon_frequency'] = 'monthly'
                            elif 'quarter' in freq_lower:
                                data['coupon_frequency'] = 'quarterly'
                            elif 'semi' in freq_lower or 'half' in freq_lower:
                                data['coupon_frequency'] = 'semi_annual'
                            else:
                                data['coupon_frequency'] = 'annual'
                        elif 'sector' in label or 'industry' in label:
                            data['sector'] = value
            
            # Check if we found meaningful data
            if data.get('issuer_name') or data.get('coupon_rate'):
                data['instrument_type'] = self._infer_instrument_type(isin, data)
                return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing NSDL HTML: {e}")
            return None
    
    async def _scrape_indiabonds(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape bond data from indiabonds.com"""
        try:
            # Try the bond directory URL
            url = f"https://www.indiabonds.com/bond-detail/{isin}/"
            
            async with session.get(url) as response:
                if response.status != 200:
                    # Try alternative URL format
                    url = f"https://www.indiabonds.com/bonds/{isin}/"
                    async with session.get(url) as response2:
                        if response2.status != 200:
                            return None
                        html = await response2.text()
                else:
                    html = await response.text()
                
                return self._parse_indiabonds_html(html, isin)
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping indiabonds for {isin}")
            return None
        except Exception as e:
            logger.warning(f"Error scraping indiabonds for {isin}: {e}")
            return None
    
    def _parse_indiabonds_html(self, html: str, isin: str) -> Optional[Dict]:
        """Parse indiabonds.com HTML response"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {}
            
            # Look for bond info sections
            # Common class names on bond detail pages
            info_sections = soup.find_all(['div', 'section'], class_=re.compile(r'bond|detail|info', re.I))
            
            for section in info_sections:
                text = section.get_text()
                
                # Extract issuer
                issuer_match = re.search(r'(?:Issuer|Company)[:\s]+([A-Za-z\s&]+(?:Limited|Ltd|Pvt))', text, re.I)
                if issuer_match:
                    data['issuer_name'] = issuer_match.group(1).strip()
                
                # Extract coupon rate
                coupon_match = re.search(r'(?:Coupon|Interest)[:\s]+(\d+\.?\d*)\s*%', text, re.I)
                if coupon_match:
                    data['coupon_rate'] = float(coupon_match.group(1))
                
                # Extract maturity
                maturity_match = re.search(r'(?:Maturity|Matures?)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})', text, re.I)
                if maturity_match:
                    data['maturity_date'] = maturity_match.group(1)
                
                # Extract rating
                rating_match = re.search(r'(?:Rating|Credit)[:\s]+(AAA|AA\+|AA-|AA|A\+|A-|A|BBB\+|BBB|BBB-|Sovereign)', text, re.I)
                if rating_match:
                    data['credit_rating'] = rating_match.group(1).upper()
            
            # Check for meaningful data
            if data.get('issuer_name') or data.get('coupon_rate'):
                data['instrument_type'] = self._infer_instrument_type(isin, data)
                return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing indiabonds HTML: {e}")
            return None
    
    async def _scrape_smest(self, session: aiohttp.ClientSession, isin: str) -> Optional[Dict]:
        """Scrape bond data from smest.in"""
        try:
            # SMEST bond detail URL
            url = f"https://www.smest.in/bonds/bond-details/{isin}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                return self._parse_smest_html(html, isin)
                
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping smest for {isin}")
            return None
        except Exception as e:
            logger.warning(f"Error scraping smest for {isin}: {e}")
            return None
    
    def _parse_smest_html(self, html: str, isin: str) -> Optional[Dict]:
        """Parse smest.in HTML response"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {}
            
            # SMEST usually has structured bond info - use soup directly
            text = soup.get_text()
            
            # Extract key fields using regex
            issuer_match = re.search(r'(?:Issuer|Company)[:\s]+([A-Za-z\s&]+(?:Limited|Ltd|Pvt)?)', text, re.I)
            if issuer_match:
                data['issuer_name'] = issuer_match.group(1).strip()
            
            coupon_match = re.search(r'(\d+\.?\d*)\s*%\s*(?:p\.a\.|per\s*annum|coupon)?', text, re.I)
            if coupon_match:
                data['coupon_rate'] = float(coupon_match.group(1))
            
            face_match = re.search(r'(?:Face\s*Value|FV)[:\s]*(?:Rs\.?|INR)?\s*(\d[\d,]*)', text, re.I)
            if face_match:
                data['face_value'] = float(face_match.group(1).replace(',', ''))
            
            # Check for meaningful data
            if data.get('issuer_name') or data.get('coupon_rate'):
                data['instrument_type'] = self._infer_instrument_type(isin, data)
                return data
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing smest HTML: {e}")
            return None
    
    def _infer_instrument_type(self, isin: str, data: Dict) -> str:
        """Infer instrument type from ISIN and data"""
        isin_upper = isin.upper()
        
        # G-Sec pattern (Government securities)
        if isin_upper.startswith('IN002') or 'government' in str(data.get('issuer_name', '')).lower():
            return 'GSEC'
        
        # SDL pattern (State Development Loans)
        if re.match(r'^IN\d{2}20', isin_upper):
            return 'SDL'
        
        # Corporate ISIN starting with INE
        if isin_upper.startswith('INE'):
            # Check if issuer name suggests NCD vs Bond
            issuer = str(data.get('issuer_name', '')).lower()
            if 'ncd' in str(data.get('issue_name', '')).lower():
                return 'NCD'
            elif any(kw in issuer for kw in ['bank', 'pfc', 'rec', 'ntpc', 'railway', 'nhai']):
                return 'BOND'
            else:
                return 'NCD'  # Default to NCD for corporate
        
        return 'NCD'


async def live_lookup_and_import(isin: str) -> Dict:
    """
    Perform live lookup for an ISIN and import to database if found.
    
    This is the main entry point for the live lookup feature.
    
    Args:
        isin: The ISIN to look up
        
    Returns:
        Dict with lookup result and imported instrument details
    """
    lookup = LiveBondLookup()
    result = await lookup.lookup_isin(isin)
    
    if not result:
        return {
            "success": False,
            "message": f"No data found for ISIN {isin} from any source",
            "sources_tried": lookup.sources_tried,
            "errors": lookup.errors
        }
    
    # Check if already exists
    existing = await db.fi_instruments.find_one({"isin": isin})
    if existing:
        return {
            "success": True,
            "message": f"ISIN {isin} already exists in database",
            "instrument": {
                "isin": isin,
                "issuer_name": existing.get("issuer_name"),
                "instrument_type": existing.get("instrument_type"),
                "coupon_rate": existing.get("coupon_rate"),
                "credit_rating": existing.get("credit_rating")
            },
            "already_existed": True
        }
    
    # Generate instrument ID
    latest = await db.fi_instruments.find_one(
        {"id": {"$regex": "^FI-"}},
        sort=[("id", -1)]
    )
    
    num = 1
    if latest and latest.get("id"):
        try:
            num = int(latest["id"].split("-")[-1]) + 1
        except (ValueError, TypeError, IndexError):
            num = 1
    
    instrument_id = f"FI-{num:06d}"
    
    # Prepare document for insertion
    instrument_doc = {
        "id": instrument_id,
        "isin": isin,
        "issuer_name": result.get("issuer_name", "Unknown Issuer"),
        "issue_name": result.get("issue_name", ""),
        "instrument_type": result.get("instrument_type", "NCD"),
        "face_value": result.get("face_value", 1000),
        "coupon_rate": result.get("coupon_rate", 0),
        "coupon_frequency": result.get("coupon_frequency", "annual"),
        "issue_date": result.get("issue_date", ""),
        "maturity_date": result.get("maturity_date", ""),
        "credit_rating": result.get("credit_rating", ""),
        "rating_agency": result.get("rating_agency", ""),
        "day_count_convention": result.get("day_count_convention", "ACT/365"),
        "current_market_price": result.get("face_value", 1000),
        "listing_exchange": result.get("listing_exchange", "NSE"),
        "sector": result.get("sector", ""),
        "is_active": True,
        "source": "LIVE_LOOKUP",
        "source_details": result.get("sources_found", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Insert into database
    try:
        await db.fi_instruments.insert_one(instrument_doc)
        logger.info(f"Successfully imported {isin} via live lookup from {result.get('sources_found', [])}")
        
        return {
            "success": True,
            "message": f"Successfully found and imported {isin}",
            "instrument": {
                "id": instrument_id,
                "isin": isin,
                "issuer_name": instrument_doc["issuer_name"],
                "instrument_type": instrument_doc["instrument_type"],
                "coupon_rate": instrument_doc["coupon_rate"],
                "credit_rating": instrument_doc["credit_rating"],
                "maturity_date": instrument_doc["maturity_date"]
            },
            "sources_found": result.get("sources_found", []),
            "newly_imported": True
        }
    except Exception as e:
        logger.error(f"Failed to insert {isin} into database: {e}")
        return {
            "success": False,
            "message": f"Found data but failed to save: {str(e)}",
            "data_found": result
        }


# Export
__all__ = ['LiveBondLookup', 'live_lookup_and_import']
