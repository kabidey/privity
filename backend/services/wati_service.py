"""
Wati.io WhatsApp Business API Service
"""
import httpx
import logging

logger = logging.getLogger(__name__)


class WatiService:
    """Wati.io WhatsApp Business API Service - v3 API"""
    
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def send_session_message(self, phone_number: str, message: str) -> dict:
        """Send a message within active WhatsApp session (24-hour window)"""
        # Remove non-digits and ensure proper format
        phone = ''.join(filter(str.isdigit, phone_number))
        if not phone.startswith('91'):
            phone = '91' + phone
        
        # v3 API endpoint for sending session messages
        url = f"{self.endpoint}/api/ext/v3/conversations/{phone}/messages"
        payload = {"text": message}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return {"result": True, **response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Wati session message error: {e.response.status_code} - {e.response.text}")
            # Try v1 API as fallback
            return await self._send_session_message_v1(phone, message)
        except httpx.HTTPError as e:
            logger.error(f"Wati session message error: {str(e)}")
            raise Exception(f"Failed to send message: {str(e)}")
    
    async def _send_session_message_v1(self, phone: str, message: str) -> dict:
        """Fallback to v1 API for session messages"""
        url = f"{self.endpoint}/api/v1/sendSessionMessage/{phone}"
        payload = {"messageText": message}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return {"result": True, **response.json()}
        except httpx.HTTPError as e:
            logger.error(f"Wati v1 session message error: {str(e)}")
            raise Exception(f"Failed to send message (v1): {str(e)}")
    
    async def send_template_message(self, phone_number: str, template_name: str, 
                                    parameters: list = None, broadcast_name: str = None) -> dict:
        """Send a template message (for outside 24-hour window)"""
        phone = ''.join(filter(str.isdigit, phone_number))
        if not phone.startswith('91'):
            phone = '91' + phone
        
        # v3 API endpoint for template messages
        url = f"{self.endpoint}/api/ext/v3/whatsappNumbers/{phone}/template-message"
        payload = {
            "template_name": template_name,
            "broadcast_name": broadcast_name or "API_Message"
        }
        
        if parameters:
            payload["parameters"] = [{"name": f"body_{i+1}", "value": p} for i, p in enumerate(parameters)]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, json=payload, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return {"result": True, **response.json()}
        except httpx.HTTPStatusError as e:
            logger.error(f"Wati template message error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to send template: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Wati template message error: {str(e)}")
            raise Exception(f"Failed to send template: {str(e)}")
    
    async def get_templates(self) -> list:
        """Get available message templates"""
        url = f"{self.endpoint}/api/ext/v3/messageTemplates"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                return data.get("messageTemplates", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to get templates: {str(e)}")
            return []
    
    async def get_conversation(self, phone_number: str) -> dict:
        """Get conversation history for a phone number"""
        phone = ''.join(filter(str.isdigit, phone_number))
        if not phone.startswith('91'):
            phone = '91' + phone
        
        url = f"{self.endpoint}/api/ext/v3/conversations/{phone}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get conversation: {str(e)}")
            return {}
