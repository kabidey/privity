"""
Bot & Attack Protection Middleware
Blocks search engine crawlers, bots, and various attack patterns
"""
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

# ============== Blocked Threats Database ==============
class ThreatDatabase:
    """
    In-memory database for tracking blocked threats
    Syncs with MongoDB periodically
    """
    def __init__(self):
        self.blocked_requests: List[dict] = []
        self.blocked_ips: Dict[str, dict] = {}
        self.threat_counts: Dict[str, int] = defaultdict(int)
        self.last_sync: float = 0
        self.sync_interval: int = 60  # Sync to DB every 60 seconds
        
    async def record_blocked_request(
        self,
        ip_address: str,
        threat_type: str,
        user_agent: str,
        path: str,
        details: str = "",
        auto_block: bool = True
    ):
        """Record a blocked request"""
        record = {
            "ip_address": ip_address,
            "threat_type": threat_type,
            "user_agent": user_agent[:500] if user_agent else "Unknown",
            "path": path[:500] if path else "/",
            "details": details[:1000] if details else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "blocked": True
        }
        
        self.blocked_requests.append(record)
        self.threat_counts[threat_type] += 1
        
        # Auto-block IP after multiple violations
        if auto_block:
            if ip_address not in self.blocked_ips:
                self.blocked_ips[ip_address] = {"count": 0, "first_seen": time.time()}
            self.blocked_ips[ip_address]["count"] += 1
            self.blocked_ips[ip_address]["last_seen"] = time.time()
            self.blocked_ips[ip_address]["last_threat"] = threat_type
        
        # Log to console
        logger.warning(f"THREAT BLOCKED: {threat_type} from {ip_address} - {path}")
        
        # Sync to database periodically
        if time.time() - self.last_sync > self.sync_interval:
            await self._sync_to_database()
    
    async def _sync_to_database(self):
        """Sync blocked requests to MongoDB"""
        try:
            from database import db
            
            if self.blocked_requests:
                # Insert all pending records
                await db.blocked_threats.insert_many(self.blocked_requests)
                self.blocked_requests = []
            
            self.last_sync = time.time()
        except Exception as e:
            logger.error(f"Failed to sync threats to database: {e}")
    
    def is_ip_blocked(self, ip_address: str, threshold: int = 5) -> bool:
        """Check if IP should be blocked based on violation count"""
        if ip_address in self.blocked_ips:
            info = self.blocked_ips[ip_address]
            # Block if exceeded threshold within last hour
            if info["count"] >= threshold and (time.time() - info["first_seen"]) < 3600:
                return True
        return False
    
    def get_stats(self) -> dict:
        """Get threat statistics"""
        return {
            "total_blocked": sum(self.threat_counts.values()),
            "by_type": dict(self.threat_counts),
            "blocked_ips_count": len(self.blocked_ips),
            "recent_threats": self.blocked_requests[-100:]  # Last 100
        }

# Global threat database
threat_db = ThreatDatabase()


# ============== Bot & Crawler Detection ==============
class BotDetector:
    """
    Detect and block search engine bots, crawlers, and scrapers
    """
    
    # Known bot user agents (case-insensitive patterns)
    BOT_USER_AGENTS = [
        # Search Engine Bots
        r"googlebot", r"bingbot", r"slurp", r"duckduckbot", r"baiduspider",
        r"yandexbot", r"sogou", r"exabot", r"facebot", r"ia_archiver",
        r"msnbot", r"teoma", r"gigabot", r"scrubby", r"robozilla",
        
        # Social Media Crawlers
        r"facebookexternalhit", r"twitterbot", r"linkedinbot", r"pinterest",
        r"whatsapp", r"telegrambot", r"slackbot", r"discordbot",
        
        # SEO & Analytics Tools
        r"semrush", r"ahrefs", r"majestic", r"moz\.com", r"dotbot",
        r"rogerbot", r"seokicks", r"blexbot", r"linkdex", r"lipperhey",
        
        # Web Scrapers & Crawlers
        r"scrapy", r"nutch", r"wget", r"curl", r"python-requests",
        r"python-urllib", r"go-http-client", r"java", r"perl",
        r"libwww", r"lwp-", r"httpclient", r"okhttp", r"axios",
        
        # Vulnerability Scanners
        r"nikto", r"nmap", r"masscan", r"sqlmap", r"wpscan",
        r"burpsuite", r"zaproxy", r"acunetix", r"nessus", r"qualys",
        r"openvas", r"w3af", r"arachni", r"skipfish", r"grabber",
        
        # Generic Bots
        r"bot", r"crawler", r"spider", r"scraper", r"fetcher",
        r"archiver", r"indexer", r"mediapartners",
        
        # Note: Headless browsers (puppeteer, playwright, selenium) are NOT blocked
        # to allow legitimate automated testing. Security scanners are blocked above.
    ]
    
    # Patterns to monitor but not block (for awareness in dashboard)
    MONITORED_USER_AGENTS = [
        r"headless", r"phantom", r"puppeteer", r"playwright", r"selenium",
        r"webdriver", r"chromedriver", r"geckodriver",
    ]
    
    # Known bot IPs (common cloud/hosting providers used by bots)
    BOT_IP_RANGES = [
        # These are example patterns - real implementation would use proper CIDR matching
        r"^66\.249\.",  # Google
        r"^157\.55\.",  # Bing
        r"^207\.46\.",  # MSN
        r"^40\.77\.",   # Bing
    ]
    
    @classmethod
    def is_bot(cls, user_agent: str) -> Tuple[bool, str]:
        """
        Check if user agent indicates a bot
        Returns (is_bot, bot_type)
        """
        if not user_agent:
            return True, "empty_user_agent"
        
        ua_lower = user_agent.lower()
        
        for pattern in cls.BOT_USER_AGENTS:
            if re.search(pattern, ua_lower):
                # Determine bot category
                if any(x in pattern for x in ["googlebot", "bingbot", "yandex", "baidu"]):
                    return True, "search_engine_crawler"
                elif any(x in pattern for x in ["facebook", "twitter", "linkedin", "whatsapp"]):
                    return True, "social_media_crawler"
                elif any(x in pattern for x in ["semrush", "ahrefs", "moz", "majestic"]):
                    return True, "seo_tool"
                elif any(x in pattern for x in ["nikto", "nmap", "sqlmap", "burp", "acunetix"]):
                    return True, "security_scanner"
                elif any(x in pattern for x in ["scrapy", "wget", "curl", "python", "java"]):
                    return True, "web_scraper"
                elif any(x in pattern for x in ["headless", "phantom", "puppeteer", "selenium"]):
                    return True, "headless_browser"
                else:
                    return True, "generic_bot"
        
        return False, ""
    
    @classmethod
    def is_suspicious_user_agent(cls, user_agent: str) -> Tuple[bool, str]:
        """Check for suspicious user agent patterns"""
        if not user_agent:
            return True, "Missing user agent"
        
        if len(user_agent) < 10:
            return True, "User agent too short"
        
        if len(user_agent) > 1000:
            return True, "User agent too long"
        
        # Check for common attack patterns in UA
        attack_patterns = [
            (r"<script", "XSS attempt in user agent"),
            (r"\.\./", "Path traversal in user agent"),
            (r"etc/passwd", "Path traversal in user agent"),
            (r"cmd\.exe", "Command injection in user agent"),
            (r"/bin/", "Command injection in user agent"),
        ]
        
        for pattern, reason in attack_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True, reason
        
        return False, ""


# ============== Attack Detection ==============
class AttackDetector:
    """
    Detect various types of attacks
    """
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e/",
        r"%2e%2e\\",
        r"\.\.%2f",
        r"\.\.%5c",
        r"/etc/passwd",
        r"/etc/shadow",
        r"/proc/self",
        r"c:\\windows",
        r"c:/windows",
        r"\\\\",
    ]
    
    # Directory enumeration patterns
    DIRECTORY_ENUM_PATTERNS = [
        r"/\.git",
        r"/\.svn",
        r"/\.hg",
        r"/\.env",
        r"/\.htaccess",
        r"/\.htpasswd",
        r"/wp-admin",
        r"/wp-content",
        r"/wp-includes",
        r"/administrator",
        r"/phpmyadmin",
        r"/phpinfo",
        r"/server-status",
        r"/server-info",
        r"/.well-known",
        r"/robots\.txt",
        r"/sitemap\.xml",
        r"/crossdomain\.xml",
        r"/clientaccesspolicy\.xml",
        r"/\.DS_Store",
        r"/Thumbs\.db",
        r"/web\.config",
        r"/config\.php",
        r"/config\.yml",
        r"/database\.yml",
        r"/settings\.py",
        r"/local_settings\.py",
        r"\.bak$",
        r"\.backup$",
        r"\.old$",
        r"\.orig$",
        r"\.sql$",
        r"\.tar$",
        r"\.gz$",
        r"\.zip$",
        r"\.rar$",
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r";\s*ls",
        r";\s*cat",
        r";\s*wget",
        r";\s*curl",
        r";\s*nc\s",
        r";\s*bash",
        r";\s*sh\s",
        r"\|\s*ls",
        r"\|\s*cat",
        r"`.*`",
        r"\$\(.*\)",
        r"&&\s*",
        r"\|\|\s*",
    ]
    
    # LFI/RFI patterns
    FILE_INCLUSION_PATTERNS = [
        r"php://",
        r"file://",
        r"data://",
        r"expect://",
        r"input://",
        r"zip://",
        r"phar://",
        r"dict://",
        r"gopher://",
        r"ftp://.*\.php",
        r"http://.*\.php",
        r"https://.*\.php",
    ]
    
    # SSRF patterns
    SSRF_PATTERNS = [
        r"127\.0\.0\.1",
        r"localhost",
        r"0\.0\.0\.0",
        r"::1",
        r"169\.254\.",  # AWS metadata
        r"metadata\.google",
        r"instance-data",
    ]
    
    @classmethod
    def detect_path_traversal(cls, path: str) -> Tuple[bool, str]:
        """Detect path traversal attack"""
        path_lower = path.lower()
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path_lower, re.IGNORECASE):
                return True, f"Path traversal detected: {pattern}"
        return False, ""
    
    @classmethod
    def detect_directory_enumeration(cls, path: str) -> Tuple[bool, str]:
        """Detect directory/file enumeration attempt"""
        path_lower = path.lower()
        for pattern in cls.DIRECTORY_ENUM_PATTERNS:
            if re.search(pattern, path_lower, re.IGNORECASE):
                return True, f"Directory enumeration: {pattern}"
        return False, ""
    
    @classmethod
    def detect_command_injection(cls, value: str) -> Tuple[bool, str]:
        """Detect command injection attempt"""
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True, "Command injection detected"
        return False, ""
    
    @classmethod
    def detect_file_inclusion(cls, value: str) -> Tuple[bool, str]:
        """Detect LFI/RFI attack"""
        for pattern in cls.FILE_INCLUSION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True, f"File inclusion attempt: {pattern}"
        return False, ""
    
    @classmethod
    def detect_ssrf(cls, value: str) -> Tuple[bool, str]:
        """Detect SSRF attempt"""
        for pattern in cls.SSRF_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True, "SSRF attempt detected"
        return False, ""


# ============== Bot Protection Middleware ==============
class BotProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to block bots, crawlers, and various attacks
    """
    
    # Paths that are allowed without bot check (like health checks)
    ALLOWED_PATHS = [
        "/api/health",
        "/api/ping",
        "/api/demo/init",  # Demo mode initialization needs to work from frontend
        "/api/demo/cleanup",  # Demo mode cleanup
        "/api/demo/status",  # Demo status check
        "/api/demo/verify-isolation",  # Demo isolation verification
        "/api/auth/login",  # Allow login from curl/scripts
        "/api/auth/register",  # Allow registration
        "/api/whatsapp/webhook",  # Wati.io webhook endpoint - external service callback
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Skip protection for allowed paths
        if any(path.startswith(p) for p in self.ALLOWED_PATHS):
            return await call_next(request)
        
        # Skip bot detection for authenticated requests (have valid Authorization header)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer ") and len(auth_header) > 20:
            # Authenticated request - still check for attacks but skip bot detection
            # This allows curl/script access for authenticated API calls
            pass
        else:
            # Check if IP is already blocked from previous violations
            if threat_db.is_ip_blocked(client_ip):
                return self._blocked_response("IP blocked due to repeated violations")
            
            # 1. Check for bots/crawlers (only for unauthenticated requests)
            is_bot, bot_type = BotDetector.is_bot(user_agent)
            if is_bot:
                await threat_db.record_blocked_request(
                    ip_address=client_ip,
                    threat_type=bot_type,
                    user_agent=user_agent,
                    path=path,
                    details=f"Bot detected: {bot_type}"
                )
                return self._blocked_response("Access denied")
            
            # 2. Check for suspicious user agent
            is_suspicious, reason = BotDetector.is_suspicious_user_agent(user_agent)
            if is_suspicious:
                await threat_db.record_blocked_request(
                    ip_address=client_ip,
                    threat_type="suspicious_user_agent",
                    user_agent=user_agent,
                    path=path,
                    details=reason
                )
                return self._blocked_response("Access denied")
        
        # 3. Check for path traversal
        is_attack, details = AttackDetector.detect_path_traversal(path)
        if is_attack:
            await threat_db.record_blocked_request(
                ip_address=client_ip,
                threat_type="path_traversal",
                user_agent=user_agent,
                path=path,
                details=details
            )
            return self._blocked_response("Invalid request")
        
        # 4. Check for directory enumeration
        is_attack, details = AttackDetector.detect_directory_enumeration(path)
        if is_attack:
            await threat_db.record_blocked_request(
                ip_address=client_ip,
                threat_type="directory_enumeration",
                user_agent=user_agent,
                path=path,
                details=details
            )
            return self._blocked_response("Not found", status_code=404)
        
        # 5. Check query parameters for attacks
        full_url = str(request.url)
        
        # Command injection in URL
        is_attack, details = AttackDetector.detect_command_injection(full_url)
        if is_attack:
            await threat_db.record_blocked_request(
                ip_address=client_ip,
                threat_type="command_injection",
                user_agent=user_agent,
                path=path,
                details=details
            )
            return self._blocked_response("Invalid request")
        
        # File inclusion in URL
        is_attack, details = AttackDetector.detect_file_inclusion(full_url)
        if is_attack:
            await threat_db.record_blocked_request(
                ip_address=client_ip,
                threat_type="file_inclusion",
                user_agent=user_agent,
                path=path,
                details=details
            )
            return self._blocked_response("Invalid request")
        
        # SSRF in URL - only check query parameters, not the host
        # The host is under our control, SSRF check is for query params that might contain URLs
        query_string = str(request.query_params) if request.query_params else ""
        is_attack, details = AttackDetector.detect_ssrf(query_string)
        if is_attack:
            await threat_db.record_blocked_request(
                ip_address=client_ip,
                threat_type="ssrf_attempt",
                user_agent=user_agent,
                path=path,
                details=details
            )
            return self._blocked_response("Invalid request")
        
        # Request passed all checks
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _blocked_response(self, message: str, status_code: int = 403) -> Response:
        """Return a blocked response"""
        return JSONResponse(
            status_code=status_code,
            content={"detail": message}
        )


# ============== Robots.txt Handler ==============
ROBOTS_TXT_CONTENT = """# Robots.txt - All crawlers blocked
User-agent: *
Disallow: /

# Block all known bots explicitly
User-agent: Googlebot
Disallow: /

User-agent: Bingbot
Disallow: /

User-agent: Slurp
Disallow: /

User-agent: DuckDuckBot
Disallow: /

User-agent: Baiduspider
Disallow: /

User-agent: YandexBot
Disallow: /

User-agent: facebookexternalhit
Disallow: /

User-agent: Twitterbot
Disallow: /

User-agent: LinkedInBot
Disallow: /

User-agent: AhrefsBot
Disallow: /

User-agent: SemrushBot
Disallow: /

User-agent: MJ12bot
Disallow: /

User-agent: DotBot
Disallow: /

# No sitemap
# Sitemap: none
"""


# ============== API Endpoints for Threat Dashboard ==============
async def get_threat_statistics():
    """Get comprehensive threat statistics for dashboard"""
    from database import db
    
    try:
        # Get stats from memory
        memory_stats = threat_db.get_stats()
        
        # Get stats from database
        pipeline = [
            {
                "$group": {
                    "_id": "$threat_type",
                    "count": {"$sum": 1},
                    "last_seen": {"$max": "$timestamp"}
                }
            },
            {"$sort": {"count": -1}}
        ]
        
        db_stats = await db.blocked_threats.aggregate(pipeline).to_list(100)
        
        # Get recent blocked requests from DB
        recent = await db.blocked_threats.find().sort("timestamp", -1).limit(100).to_list(100)
        
        # Get blocked IPs
        blocked_ips_pipeline = [
            {
                "$group": {
                    "_id": "$ip_address",
                    "count": {"$sum": 1},
                    "threats": {"$addToSet": "$threat_type"},
                    "last_seen": {"$max": "$timestamp"}
                }
            },
            {"$match": {"count": {"$gte": 3}}},
            {"$sort": {"count": -1}},
            {"$limit": 50}
        ]
        
        blocked_ips = await db.blocked_threats.aggregate(blocked_ips_pipeline).to_list(50)
        
        # Get hourly trend (last 24 hours)
        from datetime import timedelta
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        hourly_pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": twenty_four_hours_ago.isoformat()}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d %H:00",
                            "date": {"$dateFromString": {"dateString": "$timestamp"}}
                        }
                    },
                    "count": {"$sum": 1}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        hourly_trend = await db.blocked_threats.aggregate(hourly_pipeline).to_list(24)
        
        # Get total counts
        total_blocked = await db.blocked_threats.count_documents({})
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        blocked_today = await db.blocked_threats.count_documents({
            "timestamp": {"$gte": today_start.isoformat()}
        })
        
        return {
            "total_blocked": total_blocked,
            "blocked_today": blocked_today,
            "by_threat_type": {stat["_id"]: stat["count"] for stat in db_stats},
            "recent_threats": [
                {
                    "ip_address": r.get("ip_address", "Unknown"),
                    "threat_type": r.get("threat_type", "Unknown"),
                    "path": r.get("path", "/")[:100],
                    "timestamp": r.get("timestamp", ""),
                    "details": r.get("details", "")[:200]
                }
                for r in recent
            ],
            "blocked_ips": [
                {
                    "ip_address": ip["_id"],
                    "violation_count": ip["count"],
                    "threat_types": ip["threats"],
                    "last_seen": ip["last_seen"]
                }
                for ip in blocked_ips
            ],
            "hourly_trend": [
                {"hour": h["_id"], "count": h["count"]}
                for h in hourly_trend
            ],
            "memory_stats": memory_stats
        }
    except Exception as e:
        logger.error(f"Failed to get threat statistics: {e}")
        return {
            "total_blocked": 0,
            "blocked_today": 0,
            "by_threat_type": {},
            "recent_threats": [],
            "blocked_ips": [],
            "hourly_trend": [],
            "memory_stats": threat_db.get_stats(),
            "error": str(e)
        }


# ============== Export ==============
__all__ = [
    'ThreatDatabase',
    'threat_db',
    'BotDetector',
    'AttackDetector',
    'BotProtectionMiddleware',
    'ROBOTS_TXT_CONTENT',
    'get_threat_statistics'
]
