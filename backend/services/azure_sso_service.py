"""
Azure AD SSO Authentication Service
Handles Microsoft SSO authentication and token validation
"""
import os
import jwt
import requests
from datetime import datetime, timezone
from typing import Optional, Dict
from functools import lru_cache


class AzureADConfig:
    """Azure AD Configuration from environment variables"""
    def __init__(self):
        self.tenant_id = os.environ.get("AZURE_TENANT_ID", "")
        self.client_id = os.environ.get("AZURE_CLIENT_ID", "")
        self.client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
        
        # Derived URLs
        if self.tenant_id:
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        else:
            self.authority = ""
            self.jwks_uri = ""
            self.issuer = ""
    
    def is_configured(self) -> bool:
        """Check if Azure AD is properly configured"""
        return bool(self.tenant_id and self.client_id)


class AzureADValidator:
    """Validates Azure AD access tokens"""
    
    def __init__(self):
        self.config = AzureADConfig()
        self._jwks_cache = None
        self._jwks_cache_time = None
    
    def get_jwks(self) -> Dict:
        """Fetch and cache JWKS (JSON Web Key Set) from Azure AD"""
        import time
        current_time = time.time()
        
        # Cache JWKS for 24 hours
        if self._jwks_cache and self._jwks_cache_time:
            if current_time - self._jwks_cache_time < 86400:
                return self._jwks_cache
        
        try:
            response = requests.get(self.config.jwks_uri, timeout=10)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = current_time
            return self._jwks_cache
        except requests.RequestException as e:
            print(f"Failed to fetch JWKS: {e}")
            return {"keys": []}
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate Azure AD access token and return claims
        Returns None if validation fails
        """
        if not self.config.is_configured():
            return None
        
        try:
            # Get unverified header to find the key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                return None
            
            # Get JWKS and find matching key
            jwks = self.get_jwks()
            signing_key = None
            
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not signing_key:
                return None
            
            # Validate the token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
                options={"verify_exp": True}
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            print("Azure AD token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Azure AD token validation failed: {e}")
            return None
        except Exception as e:
            print(f"Azure AD token validation error: {e}")
            return None


class AzureSSOService:
    """Service for handling Azure AD SSO operations"""
    
    def __init__(self, db):
        self.db = db
        self.validator = AzureADValidator()
        self.config = AzureADConfig()
    
    def is_sso_enabled(self) -> bool:
        """Check if SSO is enabled and configured"""
        return self.config.is_configured()
    
    async def authenticate_sso_token(self, token: str) -> Optional[Dict]:
        """
        Authenticate user via Azure AD SSO token
        Creates or updates user in database
        Returns user document if successful
        """
        # Validate token
        claims = self.validator.validate_token(token)
        if not claims:
            return None
        
        # Extract user info from claims
        email = claims.get("preferred_username", "").lower() or claims.get("email", "").lower()
        name = claims.get("name", "")
        given_name = claims.get("given_name", "")
        family_name = claims.get("family_name", "")
        azure_oid = claims.get("oid")  # Azure Object ID
        
        if not email:
            return None
        
        # Construct full name if not provided
        if not name and (given_name or family_name):
            name = f"{given_name} {family_name}".strip()
        if not name:
            name = email.split("@")[0]
        
        # Check if user exists
        existing_user = await self.db.users.find_one({"email": email}, {"_id": 0})
        
        if existing_user:
            # Update existing user with SSO info
            await self.db.users.update_one(
                {"email": email},
                {
                    "$set": {
                        "azure_oid": azure_oid,
                        "auth_method": "azure_sso",
                        "last_login": datetime.now(timezone.utc).isoformat(),
                        "sso_last_login": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            existing_user["azure_oid"] = azure_oid
            existing_user["auth_method"] = "azure_sso"
            return existing_user
        else:
            # Create new SSO user with Employee role (4)
            import uuid
            user_id = str(uuid.uuid4())
            
            user_doc = {
                "id": user_id,
                "email": email,
                "name": name,
                "pan_number": None,  # SSO users don't need PAN initially
                "role": 4,  # Default to Employee
                "auth_method": "azure_sso",
                "azure_oid": azure_oid,
                "password": None,  # SSO users don't have local password
                "must_change_password": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login": datetime.now(timezone.utc).isoformat(),
                "sso_last_login": datetime.now(timezone.utc).isoformat()
            }
            
            await self.db.users.insert_one(user_doc)
            return user_doc
    
    def get_sso_config(self) -> Dict:
        """Get SSO configuration for frontend"""
        if not self.config.is_configured():
            return {
                "enabled": False,
                "message": "SSO is not configured. Please set AZURE_TENANT_ID and AZURE_CLIENT_ID."
            }
        
        return {
            "enabled": True,
            "tenant_id": self.config.tenant_id,
            "client_id": self.config.client_id,
            "authority": self.config.authority,
            "redirect_uri": os.environ.get("AZURE_REDIRECT_URI", ""),
            "scopes": [f"api://{self.config.client_id}/user_impersonation", "openid", "profile", "email"]
        }


# Singleton instances
azure_config = AzureADConfig()
azure_validator = AzureADValidator()
