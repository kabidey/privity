"""
OCR service for document processing
"""
import logging
import uuid
import base64
import io
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import aiofiles

from config import EMERGENT_LLM_KEY


async def process_document_ocr(file_path: str, doc_type: str) -> Optional[Dict[str, Any]]:
    """Process document OCR using AI vision model"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        from pdf2image import convert_from_path
        from PIL import Image
        import io
        
        # Read and encode the file
        file_ext = file_path.lower().split('.')[-1]
        
        # For PDF, convert first page to image
        if file_ext == 'pdf':
            try:
                # Convert PDF to images (first page only for speed)
                images = convert_from_path(file_path, first_page=1, last_page=1, dpi=150)
                if not images:
                    return {
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                        "doc_type": doc_type,
                        "status": "error",
                        "error": "Could not convert PDF to image",
                        "extracted_data": {}
                    }
                # Convert PIL image to base64
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='PNG')
                image_bytes = img_byte_arr.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                logging.info(f"Converted PDF to image for OCR processing")
            except Exception as pdf_err:
                logging.error(f"PDF conversion failed: {pdf_err}")
                return {
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "doc_type": doc_type,
                    "status": "error",
                    "error": f"PDF conversion failed: {str(pdf_err)}",
                    "extracted_data": {}
                }
        else:
            # Read image and convert to base64
            async with aiofiles.open(file_path, 'rb') as f:
                image_bytes = await f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine prompt based on document type
        if doc_type == "pan_card":
            prompt = """Extract the following information from this PAN card image:
1. PAN Number (10 character alphanumeric)
2. Full Name
3. Father's Name
4. Date of Birth

Return ONLY a JSON object with keys: pan_number, name, father_name, date_of_birth
If any field is not visible, use null."""

        elif doc_type == "cancelled_cheque":
            prompt = """Extract the following information from this cancelled cheque image:
1. Account Number
2. IFSC Code
3. Bank Name
4. Branch Name
5. Account Holder Name

Return ONLY a JSON object with keys: account_number, ifsc_code, bank_name, branch_name, account_holder_name
If any field is not visible, use null."""

        elif doc_type == "cml_copy":
            prompt = """Extract the following information from this CML (Client Master List) copy:

IMPORTANT FIELD IDENTIFICATION:
- DP ID: This is the Depository Participant ID. Look for fields labeled "DP ID", "DP Id", "Depository Participant ID". It can be in formats like:
  * Numeric only: 12024200
  * With prefix: IN301629
  * Combined: IN301629-10242225
  
- Client ID: This is the client-specific ID assigned by the DP. Look for fields labeled "Client ID", "Client Id", "CL ID". It's usually an 8-digit number like: 01126561

- BO ID: This is the Beneficiary Owner ID. It may look like: DLK7801. DO NOT confuse this with DP ID.

Fields to extract:
1. DP ID - The Depository Participant ID (NOT the BO ID)
2. Client ID - The client-specific number (usually 8 digits)
3. Full DP Client ID - Combination of DP ID + Client ID (e.g., 12024200-01126561)
4. Client Name - IMPORTANT: This is the PRIMARY ACCOUNT HOLDER'S NAME (look for "First Holder Name", "Name", "Client Name"). Do NOT use "Father's Name" or "Guardian Name".
5. PAN Number - 10 character alphanumeric (e.g., ARSPN7228G)
6. Email Address
7. Mobile Number
8. Address (full address including city, state)
9. Pin Code
10. Bank Name
11. Bank Account Number
12. IFSC Code
13. Branch Name

CRITICAL RULES:
- For dp_id: Extract ONLY the Depository Participant ID, NOT the BO ID
- For client_id: Extract the client-specific ID (usually 8 digits starting with 0)
- For client_name: Use PRIMARY ACCOUNT HOLDER'S name, NOT father's/guardian's name

Return ONLY a JSON object with keys: dp_id, client_id, full_dp_client_id, client_name, pan_number, email, mobile, address, pin_code, bank_name, account_number, ifsc_code, branch_name
If any field is not visible, use null. For full_dp_client_id, combine dp_id and client_id with a hyphen if they appear separately."""
        else:
            prompt = "Extract all text and relevant information from this document. Return as JSON."

        # Use AI for OCR
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4()}",
            system_message="You are an OCR specialist. Extract information from documents accurately. IMPORTANT: Always respond with ONLY valid JSON, no explanations, no markdown code blocks, just the raw JSON object."
        ).with_model("openai", "gpt-4o")
        
        # Create ImageContent for vision processing
        image_content = ImageContent(image_base64=image_base64)
        user_message = UserMessage(text=prompt, file_contents=[image_content])
        
        response = await chat.send_message(user_message)
        
        # Parse the response as JSON
        import json
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            # Remove markdown code blocks
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line if it's closing ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned = '\n'.join(lines).strip()
            # Handle case where it starts with 'json' without backticks
            if cleaned.startswith('json'):
                cleaned = cleaned[4:].strip()
            
            # Try to find JSON object in the response
            if not cleaned.startswith('{'):
                # Look for JSON object in the text
                start_idx = cleaned.find('{')
                end_idx = cleaned.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
            
            extracted_data = json.loads(cleaned)
            logging.info(f"OCR extracted data: {extracted_data}")
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse OCR JSON response: {e}. Raw: {response[:200]}")
            extracted_data = {"raw_text": response, "parse_error": str(e)}
        
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "processed",
            "extracted_data": extracted_data
        }
        
    except Exception as e:
        logging.error(f"OCR processing failed: {str(e)}")
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "error",
            "error": str(e),
            "extracted_data": {}
        }
