"""
IP Geolocation Service
Detects login location and identifies unusual login patterns
Uses ip-api.com (free, no API key required)
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class IPGeolocationService:
    """
    Service for IP geolocation and unusual location detection
    """
    
    API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,proxy,hosting"
    
    # Cache for IP lookups to reduce API calls
    _cache: Dict[str, dict] = {}
    _cache_expiry: Dict[str, float] = {}
    CACHE_DURATION = 86400  # 24 hours
    
    # Rate limiting (ip-api allows 45 requests/minute for free tier)
    _request_times: List[float] = []
    MAX_REQUESTS_PER_MINUTE = 40  # Stay under limit
    
    @classmethod
    async def _rate_limit_check(cls):
        """Check and enforce rate limiting"""
        import time
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        cls._request_times = [t for t in cls._request_times if t > minute_ago]
        
        if len(cls._request_times) >= cls.MAX_REQUESTS_PER_MINUTE:
            # Wait until we can make another request
            wait_time = 60 - (now - cls._request_times[0])
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        cls._request_times.append(now)
    
    @classmethod
    async def get_location(cls, ip_address: str) -> Optional[dict]:
        """
        Get geolocation data for an IP address
        Returns dict with location info or None if lookup fails
        """
        import time
        
        # Skip private/local IPs
        if cls._is_private_ip(ip_address):
            return {
                "ip": ip_address,
                "country": "Local",
                "countryCode": "LO",
                "city": "Local Network",
                "region": "Private",
                "lat": 0,
                "lon": 0,
                "isp": "Private Network",
                "is_private": True
            }
        
        # Check cache
        if ip_address in cls._cache:
            if time.time() < cls._cache_expiry.get(ip_address, 0):
                return cls._cache[ip_address]
        
        # Rate limit check
        await cls._rate_limit_check()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = cls.API_URL.format(ip=ip_address)
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("status") == "success":
                            result = {
                                "ip": ip_address,
                                "country": data.get("country", "Unknown"),
                                "countryCode": data.get("countryCode", "XX"),
                                "region": data.get("regionName", "Unknown"),
                                "city": data.get("city", "Unknown"),
                                "zip": data.get("zip", ""),
                                "lat": data.get("lat", 0),
                                "lon": data.get("lon", 0),
                                "timezone": data.get("timezone", ""),
                                "isp": data.get("isp", "Unknown"),
                                "org": data.get("org", ""),
                                "is_proxy": data.get("proxy", False),
                                "is_hosting": data.get("hosting", False),
                                "is_private": False
                            }
                            
                            # Cache the result
                            cls._cache[ip_address] = result
                            cls._cache_expiry[ip_address] = time.time() + cls.CACHE_DURATION
                            
                            return result
                        else:
                            logger.warning(f"IP lookup failed for {ip_address}: {data.get('message')}")
                            return None
                    else:
                        logger.error(f"IP API returned status {response.status}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout looking up IP {ip_address}")
            return None
        except Exception as e:
            logger.error(f"Error looking up IP {ip_address}: {e}")
            return None
    
    @classmethod
    def _is_private_ip(cls, ip: str) -> bool:
        """Check if IP is private/local"""
        if not ip or ip == "unknown":
            return True
        
        # Check common private ranges
        private_prefixes = [
            "10.", "172.16.", "172.17.", "172.18.", "172.19.",
            "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
            "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
            "172.30.", "172.31.", "192.168.", "127.", "0.", "localhost"
        ]
        
        for prefix in private_prefixes:
            if ip.startswith(prefix):
                return True
        
        return False
    
    @classmethod
    def calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in kilometers
        Using Haversine formula
        """
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class UnusualLoginDetector:
    """
    Detects unusual login patterns based on location history
    """
    
    # Distance threshold for "unusual" location (in km)
    UNUSUAL_DISTANCE_THRESHOLD = 500  # 500 km
    
    # Time threshold - if login from far location within this time, flag as suspicious
    IMPOSSIBLE_TRAVEL_TIME_HOURS = 2  # 2 hours
    
    # Minimum logins needed to establish a pattern
    MIN_HISTORY_FOR_DETECTION = 3
    
    @classmethod
    async def check_login_location(
        cls,
        user_id: str,
        user_email: str,
        ip_address: str,
        user_agent: str
    ) -> dict:
        """
        Check if login location is unusual for this user
        Returns dict with analysis results
        """
        from database import db
        
        # Get location for current IP
        current_location = await IPGeolocationService.get_location(ip_address)
        
        if not current_location:
            return {
                "status": "unknown",
                "message": "Could not determine location",
                "location": None,
                "is_unusual": False,
                "alerts": []
            }
        
        # Get user's login history
        login_history = await db.login_locations.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50).to_list(50)
        
        alerts = []
        is_unusual = False
        risk_level = "low"
        
        # Check 1: Is this a VPN/Proxy/Hosting IP?
        if current_location.get("is_proxy"):
            alerts.append({
                "type": "proxy_detected",
                "severity": "medium",
                "message": "Login from proxy/VPN detected"
            })
            risk_level = "medium"
        
        if current_location.get("is_hosting"):
            alerts.append({
                "type": "hosting_ip",
                "severity": "high",
                "message": "Login from hosting/datacenter IP - potential automated attack"
            })
            risk_level = "high"
            is_unusual = True
        
        # Check 2: Is this a new country?
        if login_history:
            known_countries = set(h.get("country") for h in login_history if h.get("country"))
            current_country = current_location.get("country")
            
            if current_country and current_country not in known_countries and current_country != "Local":
                alerts.append({
                    "type": "new_country",
                    "severity": "high",
                    "message": f"First login from {current_country}"
                })
                is_unusual = True
                risk_level = "high"
        
        # Check 3: Impossible travel detection
        if login_history and len(login_history) >= 1:
            last_login = login_history[0]
            last_lat = last_login.get("lat", 0)
            last_lon = last_login.get("lon", 0)
            last_time = last_login.get("timestamp")
            
            if last_time and last_lat and last_lon:
                # Parse last login time
                try:
                    if isinstance(last_time, str):
                        last_datetime = datetime.fromisoformat(last_time.replace("Z", "+00:00"))
                    else:
                        last_datetime = last_time
                    
                    time_diff = datetime.now(timezone.utc) - last_datetime
                    hours_diff = time_diff.total_seconds() / 3600
                    
                    # Calculate distance
                    current_lat = current_location.get("lat", 0)
                    current_lon = current_location.get("lon", 0)
                    
                    if current_lat and current_lon and not current_location.get("is_private"):
                        distance = IPGeolocationService.calculate_distance(
                            last_lat, last_lon, current_lat, current_lon
                        )
                        
                        # Check for impossible travel (e.g., 1000km in 1 hour = impossible)
                        if hours_diff > 0:
                            required_speed = distance / hours_diff  # km/h
                            
                            # If would require > 800 km/h (faster than commercial flight)
                            if required_speed > 800 and distance > 100:
                                alerts.append({
                                    "type": "impossible_travel",
                                    "severity": "critical",
                                    "message": f"Impossible travel detected: {distance:.0f}km in {hours_diff:.1f}h ({required_speed:.0f}km/h required)",
                                    "last_location": f"{last_login.get('city')}, {last_login.get('country')}",
                                    "current_location": f"{current_location.get('city')}, {current_location.get('country')}",
                                    "distance_km": round(distance),
                                    "time_hours": round(hours_diff, 1)
                                })
                                is_unusual = True
                                risk_level = "critical"
                        
                        # Check for unusual distance even with enough time
                        if distance > cls.UNUSUAL_DISTANCE_THRESHOLD:
                            if not any(a["type"] == "impossible_travel" for a in alerts):
                                alerts.append({
                                    "type": "distant_location",
                                    "severity": "medium",
                                    "message": f"Login from {distance:.0f}km away from last location",
                                    "distance_km": round(distance)
                                })
                                if risk_level == "low":
                                    risk_level = "medium"
                
                except Exception as e:
                    logger.error(f"Error in time comparison: {e}")
        
        # Check 4: New city in same country
        if login_history and len(login_history) >= cls.MIN_HISTORY_FOR_DETECTION:
            known_cities = set(h.get("city") for h in login_history if h.get("city"))
            current_city = current_location.get("city")
            
            if current_city and current_city not in known_cities and current_city != "Local Network":
                # Only flag if we have enough history
                alerts.append({
                    "type": "new_city",
                    "severity": "low",
                    "message": f"First login from {current_city}"
                })
        
        # Store this login location
        login_record = {
            "user_id": user_id,
            "user_email": user_email,
            "ip_address": ip_address,
            "country": current_location.get("country"),
            "countryCode": current_location.get("countryCode"),
            "region": current_location.get("region"),
            "city": current_location.get("city"),
            "lat": current_location.get("lat"),
            "lon": current_location.get("lon"),
            "isp": current_location.get("isp"),
            "is_proxy": current_location.get("is_proxy", False),
            "is_hosting": current_location.get("is_hosting", False),
            "user_agent": user_agent[:500] if user_agent else None,
            "is_unusual": is_unusual,
            "risk_level": risk_level,
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await db.login_locations.insert_one(login_record)
        except Exception as e:
            logger.error(f"Failed to store login location: {e}")
        
        return {
            "status": "checked",
            "location": {
                "country": current_location.get("country"),
                "city": current_location.get("city"),
                "region": current_location.get("region"),
                "isp": current_location.get("isp")
            },
            "is_unusual": is_unusual,
            "risk_level": risk_level,
            "alerts": alerts,
            "is_proxy": current_location.get("is_proxy", False),
            "is_hosting": current_location.get("is_hosting", False)
        }
    
    @classmethod
    async def get_user_login_locations(cls, user_id: str, limit: int = 20) -> List[dict]:
        """Get recent login locations for a user"""
        from database import db
        
        locations = await db.login_locations.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return locations
    
    @classmethod
    async def get_unusual_logins(cls, hours: int = 24) -> List[dict]:
        """Get all unusual logins in the last N hours"""
        from database import db
        
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        unusual = await db.login_locations.find(
            {
                "is_unusual": True,
                "timestamp": {"$gte": cutoff}
            },
            {"_id": 0}
        ).sort("timestamp", -1).to_list(100)
        
        return unusual


# Export
__all__ = ['IPGeolocationService', 'UnusualLoginDetector']
