"""
OCR service for document processing
Enhanced with robust extraction and validation
"""
import logging
import uuid
import base64
import io
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import aiofiles

from config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)


def validate_pan_number(pan: str) -> bool:
    """Validate PAN number format: AAAAA0000A"""
    if not pan or len(pan) != 10:
        return False
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    return bool(re.match(pattern, pan.upper()))


def validate_ifsc_code(ifsc: str) -> bool:
    """Validate IFSC code format: AAAA0NNNNNN"""
    if not ifsc or len(ifsc) != 11:
        return False
    pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
    return bool(re.match(pattern, ifsc.upper()))


def clean_account_number(account_no: str) -> str:
    """Clean account number - remove spaces and special characters"""
    if not account_no:
        return None
    return re.sub(r'[^0-9]', '', str(account_no))


def clean_mobile_number(mobile: str) -> str:
    """Clean mobile number - extract 10 digits"""
    if not mobile:
        return None
    digits = re.sub(r'[^0-9]', '', str(mobile))
    # If starts with 91, remove it
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    # Return only if 10 digits
    return digits if len(digits) == 10 else None


def normalize_name(name: str) -> str:
    """Normalize name - remove titles and clean up"""
    if not name:
        return None
    # Remove common titles
    titles = ['MR', 'MRS', 'MS', 'DR', 'SHRI', 'SMT', 'KUMARI', 'MASTER', 'MISS']
    name = name.upper().strip()
    for title in titles:
        if name.startswith(title + ' '):
            name = name[len(title):].strip()
        if name.startswith(title + '.'):
            name = name[len(title)+1:].strip()
    return name.title()


async def convert_file_to_base64(file_path: str) -> tuple:
    """Convert file to base64, handling PDF conversion"""
    file_ext = file_path.lower().split('.')[-1]
    
    if file_ext == 'pdf':
        try:
            from pdf2image import convert_from_path
            # Convert PDF to images with higher DPI for better OCR
            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
            if not images:
                return None, "Could not convert PDF to image"
            
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG', optimize=True)
            image_bytes = img_byte_arr.getvalue()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info("Converted PDF to image for OCR processing")
            return image_base64, None
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return None, f"PDF conversion failed: {str(e)}"
    else:
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                image_bytes = await f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            return image_base64, None
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"


def get_pan_card_prompt() -> str:
    """Get optimized prompt for PAN card OCR - Enhanced for better accuracy"""
    return """You are an expert OCR specialist analyzing an Indian PAN Card. Extract information with EXTREME precision.

DOCUMENT LAYOUT REFERENCE (Indian PAN Card):
- TOP: "INCOME TAX DEPARTMENT" / "आयकर विभाग" and "GOVT. OF INDIA"
- LEFT SIDE: Contains text fields in vertical arrangement
- RIGHT SIDE: Photograph of cardholder
- BOTTOM: PAN number in LARGE FONT

REQUIRED FIELDS TO EXTRACT:

1. **PAN Number** (CRITICAL):
   - Located at BOTTOM of card in LARGE, BOLD characters
   - Format: EXACTLY 10 characters - 5 LETTERS + 4 DIGITS + 1 LETTER
   - Example: BLOPS6942P, AABPM1234Q
   - The first 5 chars are ALWAYS letters (A-Z)
   - The next 4 chars are ALWAYS digits (0-9)
   - The last char is ALWAYS a letter (A-Z)

2. **Name**:
   - The cardholder's name (NOT the father's name)
   - Usually appears AFTER "Name" label
   - In CAPITAL LETTERS
   - May have title like MR/MRS - extract without title

3. **Father's Name**:
   - Usually on line ABOVE the cardholder's name
   - Labeled as "Father's Name" or "पिता का नाम"
   - Extract without any title (MR/MRS/SHRI etc.)

4. **Date of Birth**:
   - Format: DD/MM/YYYY
   - Labeled as "Date of Birth" / "जन्म तिथि"

CRITICAL RULES:
- PAN format MUST be 5 letters + 4 digits + 1 letter (total 10 chars)
- If you see something like "BLOPS6942P" - that's the PAN
- The cardholder name is BELOW father's name
- Remove any titles (MR, MRS, SHRI, SMT) from names
- Return null for fields you cannot clearly read

Return ONLY this JSON structure:
{
    "pan_number": "BLOPS6942P",
    "name": "BENOY SEN",
    "father_name": "SUPRABHAT SEN",
    "date_of_birth": "30/08/1968"
}

NO explanations, NO markdown code blocks, ONLY the raw JSON object."""


def get_cancelled_cheque_prompt() -> str:
    """Get optimized prompt for cancelled cheque OCR"""
    return """You are analyzing a Bank Cheque/Cancelled Cheque image. Extract the following information:

REQUIRED FIELDS:
1. Account Number: The bank account number (usually printed at bottom or in account details section)
2. IFSC Code: 11-character code (format: AAAA0NNNNNN, e.g., HDFC0004283)
3. Bank Name: The name of the bank (e.g., HDFC BANK, SBI, ICICI)
4. Branch Name/Address: The branch details
5. Account Holder Name: Name(s) printed on the cheque

WHERE TO LOOK:
- Account Number: Usually printed in the bottom portion OR in "A/c No" field
- IFSC Code: Look for "RTGS/NEFT IFSC" or "IFSC" text
- Bank Name: Usually prominently displayed at top or as logo
- Branch: Look for complete branch address
- Account Holder Name: Usually printed below or near "Pay" field

IMPORTANT:
- Extract the COMPLETE account number (may be 10-16 digits)
- IFSC is always 11 characters
- If there are joint account holders (like "NAME1 / NAME2"), include both names

Return ONLY a JSON object with these exact keys:
{
    "account_number": "50100439991690",
    "ifsc_code": "HDFC0004283",
    "bank_name": "HDFC BANK",
    "branch_name": "1/2 CENTRAL PARK, PREMISES NO. 98, RAJA S C MALLICK ROAD, KOLKATA-700032",
    "account_holder_name": "JNANASHREE SARMA / SUPRABHAT SEN"
}

NO explanations, NO markdown, ONLY the JSON object."""


def get_cml_copy_prompt() -> str:
    """Get optimized prompt for CML document OCR"""
    return """You are analyzing a CML (Client Master List) document from an Indian Depository. Extract ALL information carefully.

DOCUMENT TYPES:
1. CDSL CML: Has "CDSL" logo, DP ID like "12010600", Client ID like "05604331"
2. NSDL CML: Has "NSDL" logo, DP ID like "IN301629", Client ID like "10242225"

FIELD LOCATIONS AND EXTRACTION RULES:

1. DP ID: Look for "DP ID" or "DP Id" field
   - CDSL format: 8 digits (e.g., 12010600)
   - NSDL format: "IN" + 6 chars (e.g., IN301629)

2. Client ID: Look for "Client ID", "Client Id", "CL ID" field
   - Usually 8 digits

3. Client Name (CRITICAL):
   - Look for "First Holder Name" or "Name" field
   - This is the PRIMARY account holder, NOT the father's name
   - May include title like "MR", "MRS" - extract without title
   - Example: If you see "MR SUPRABHAT SEN", extract as "SUPRABHAT SEN"

4. PAN Number: Look for "PAN" field
   - 10 characters: 5 letters + 4 digits + 1 letter
   - Example: BLOPS6942P

5. Date of Birth: Look for "DOB" or "Date of Birth"
   - Format: DD/MM/YYYY

6. Email: Look for "Email" or "E-mail" field
   - May be partially masked with #

7. Mobile: Look for "Mobile", "SMS Mobile", "Phone" field
   - 10 digit number, may be partially masked

8. Address: Combine "Correspondence Address" or "Address" fields
   - Include city, state, PIN

9. PIN Code: 6 digit postal code

10. BANK DETAILS (VERY IMPORTANT):
    - CML may have MULTIPLE bank accounts
    - Extract the PRIMARY/DEFAULT bank account details
    - Look for "Bank A/C No", "Account No" field
    - Bank Name: May be identified by IFSC code (HDFC, SBI, etc.)
    - IFSC: Look for "IFSC" or "IFSC Code" - 11 characters
    
    IMPORTANT: The bank account in CML may differ from cancelled cheque!
    Extract exactly what's shown in the CML document.

Return ONLY a JSON object:
{
    "cml_type": "CDSL or NSDL",
    "dp_id": "12010600",
    "client_id": "05604331",
    "bo_id": "1201060005604331",
    "full_dp_client_id": "12010600-05604331",
    "client_name": "SUPRABHAT SEN",
    "pan_number": "BLOPS6942P",
    "date_of_birth": "30/08/1968",
    "email": "68SUPSEN@GMAIL.COM",
    "mobile": "9836205656",
    "address": "A/15 BAGHAJATIN REGENT ESTATE, KOLKATA, WEST BENGAL",
    "pin_code": "700092",
    "bank_name": "HDFC BANK",
    "account_number": "04781050009281",
    "ifsc_code": "HDFC0000478",
    "branch_name": null
}

NO explanations, NO markdown, ONLY the JSON object."""


async def process_document_ocr(file_path: str, doc_type: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
    """
    Process document OCR using AI vision model
    
    Args:
        file_path: Path to the document file
        doc_type: Type of document (pan_card, cancelled_cheque, cml_copy)
        retry_count: Number of retry attempts for better accuracy
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        
        # Convert file to base64
        image_base64, error = await convert_file_to_base64(file_path)
        if error:
            return {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "doc_type": doc_type,
                "status": "error",
                "error": error,
                "extracted_data": {},
                "confidence": 0
            }
        
        # Get appropriate prompt based on document type
        if doc_type == "pan_card":
            prompt = get_pan_card_prompt()
        elif doc_type == "cancelled_cheque":
            prompt = get_cancelled_cheque_prompt()
        elif doc_type == "cml_copy":
            prompt = get_cml_copy_prompt()
        else:
            prompt = "Extract all text and relevant information from this document. Return as JSON."
        
        # Use AI for OCR with higher quality model
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4()}",
            system_message="You are an expert OCR specialist for Indian financial documents. Extract information with extreme accuracy. CRITICAL: Always respond with ONLY valid JSON, no explanations, no markdown code blocks, just the raw JSON object."
        ).with_model("openai", "gpt-4o")
        
        # Create ImageContent for vision processing
        image_content = ImageContent(image_base64=image_base64)
        user_message = UserMessage(text=prompt, file_contents=[image_content])
        
        response = await chat.send_message(user_message)
        
        # Parse the response as JSON
        import json
        extracted_data = {}
        confidence = 0
        
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned = '\n'.join(lines).strip()
            
            # Handle case where it starts with 'json' without backticks
            if cleaned.lower().startswith('json'):
                cleaned = cleaned[4:].strip()
            
            # Find JSON object in the response
            if not cleaned.startswith('{'):
                start_idx = cleaned.find('{')
                end_idx = cleaned.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned = cleaned[start_idx:end_idx+1]
            
            extracted_data = json.loads(cleaned)
            logger.info(f"OCR extracted data for {doc_type}: {extracted_data}")
            
            # Post-processing and validation based on document type
            if doc_type == "pan_card":
                extracted_data, confidence = post_process_pan_card(extracted_data)
            elif doc_type == "cancelled_cheque":
                extracted_data, confidence = post_process_cancelled_cheque(extracted_data)
            elif doc_type == "cml_copy":
                extracted_data, confidence = post_process_cml(extracted_data)
            else:
                confidence = 70
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse OCR JSON response: {e}. Raw: {response[:500]}")
            extracted_data = {"raw_text": response, "parse_error": str(e)}
            confidence = 0
        
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "processed",
            "extracted_data": extracted_data,
            "confidence": confidence,
            "retry_count": retry_count
        }
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        return {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "doc_type": doc_type,
            "status": "error",
            "error": str(e),
            "extracted_data": {},
            "confidence": 0
        }


def post_process_pan_card(data: Dict[str, Any]) -> tuple:
    """Post-process and validate PAN card OCR data"""
    confidence = 100
    
    # Validate and clean PAN number
    pan = data.get('pan_number', '')
    if pan:
        pan = pan.upper().strip().replace(' ', '')
        if validate_pan_number(pan):
            data['pan_number'] = pan
        else:
            confidence -= 30
            logger.warning(f"Invalid PAN format: {pan}")
    else:
        confidence -= 30
    
    # Clean name
    name = data.get('name', '')
    if name:
        data['name'] = normalize_name(name)
    else:
        confidence -= 20
    
    # Clean father's name
    father = data.get('father_name', '')
    if father:
        data['father_name'] = normalize_name(father)
    else:
        confidence -= 10
    
    # Validate date format
    dob = data.get('date_of_birth', '')
    if dob:
        # Normalize date format to DD/MM/YYYY
        dob = dob.strip()
        # Handle various formats
        if re.match(r'\d{2}[-/]\d{2}[-/]\d{4}', dob):
            data['date_of_birth'] = dob.replace('-', '/')
        else:
            confidence -= 10
    else:
        confidence -= 10
    
    return data, max(0, confidence)


def post_process_cancelled_cheque(data: Dict[str, Any]) -> tuple:
    """Post-process and validate cancelled cheque OCR data"""
    confidence = 100
    
    # Clean and validate account number
    acc_no = data.get('account_number', '')
    if acc_no:
        cleaned = clean_account_number(acc_no)
        if cleaned and len(cleaned) >= 9:
            data['account_number'] = cleaned
        else:
            confidence -= 25
    else:
        confidence -= 25
    
    # Validate IFSC code
    ifsc = data.get('ifsc_code', '')
    if ifsc:
        ifsc = ifsc.upper().strip().replace(' ', '')
        if validate_ifsc_code(ifsc):
            data['ifsc_code'] = ifsc
            # Extract bank name from IFSC if not provided
            if not data.get('bank_name'):
                bank_codes = {
                    'HDFC': 'HDFC Bank',
                    'ICIC': 'ICICI Bank',
                    'SBIN': 'State Bank of India',
                    'UTIB': 'Axis Bank',
                    'KKBK': 'Kotak Mahindra Bank',
                    'PUNB': 'Punjab National Bank',
                    'BARB': 'Bank of Baroda',
                    'CNRB': 'Canara Bank',
                    'UBIN': 'Union Bank of India',
                    'IDIB': 'Indian Bank'
                }
                bank_prefix = ifsc[:4]
                data['bank_name'] = bank_codes.get(bank_prefix, data.get('bank_name'))
        else:
            confidence -= 25
    else:
        confidence -= 25
    
    # Clean account holder name
    holder = data.get('account_holder_name', '')
    if holder:
        # Don't normalize - keep as is since it may have multiple names
        data['account_holder_name'] = holder.strip()
    else:
        confidence -= 15
    
    # Bank name
    if not data.get('bank_name'):
        confidence -= 10
    
    return data, max(0, confidence)


def post_process_cml(data: Dict[str, Any]) -> tuple:
    """Post-process and validate CML OCR data"""
    confidence = 100
    
    # Validate PAN
    pan = data.get('pan_number', '')
    if pan:
        pan = pan.upper().strip().replace(' ', '')
        if validate_pan_number(pan):
            data['pan_number'] = pan
        else:
            confidence -= 15
    else:
        confidence -= 15
    
    # Validate IFSC
    ifsc = data.get('ifsc_code', '')
    if ifsc:
        ifsc = ifsc.upper().strip().replace(' ', '')
        if validate_ifsc_code(ifsc):
            data['ifsc_code'] = ifsc
        else:
            confidence -= 10
    
    # Clean account number
    acc_no = data.get('account_number', '')
    if acc_no:
        data['account_number'] = clean_account_number(acc_no)
    
    # Clean mobile
    mobile = data.get('mobile', '')
    if mobile:
        cleaned = clean_mobile_number(mobile)
        if cleaned:
            data['mobile'] = cleaned
    
    # Clean client name - IMPORTANT: don't confuse with father's name
    name = data.get('client_name', '')
    if name:
        data['client_name'] = normalize_name(name)
    else:
        confidence -= 20
    
    # Construct full_dp_client_id if not present
    dp_id = data.get('dp_id', '')
    client_id = data.get('client_id', '')
    if dp_id and client_id and not data.get('full_dp_client_id'):
        data['full_dp_client_id'] = f"{dp_id}-{client_id}"
    
    # Construct bo_id for CDSL if not present
    if data.get('cml_type') == 'CDSL' and dp_id and client_id and not data.get('bo_id'):
        data['bo_id'] = f"{dp_id}{client_id}"
    
    # Validate DP ID format
    if dp_id:
        if data.get('cml_type') == 'NSDL' and not dp_id.startswith('IN'):
            confidence -= 10
        elif data.get('cml_type') == 'CDSL' and not dp_id.isdigit():
            confidence -= 10
    else:
        confidence -= 15
    
    # Client ID validation
    if not client_id:
        confidence -= 15
    
    return data, max(0, confidence)


async def rerun_ocr_for_client(client_id: str, doc_types: List[str] = None) -> Dict[str, Any]:
    """
    Rerun OCR for a client's documents
    
    Args:
        client_id: The client ID
        doc_types: List of document types to rerun OCR for (if None, rerun all)
    
    Returns:
        Dictionary with rerun results
    """
    from database import db
    from services.file_storage import get_file_from_gridfs
    import tempfile
    import os
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        return {"status": "error", "error": "Client not found"}
    
    documents = client.get('documents', [])
    if not documents:
        return {"status": "error", "error": "No documents found for client"}
    
    results = {
        "client_id": client_id,
        "client_name": client.get('name'),
        "rerun_at": datetime.now(timezone.utc).isoformat(),
        "documents_processed": [],
        "extracted_data": {},
        "errors": []
    }
    
    # Filter documents by type if specified
    if doc_types:
        documents = [d for d in documents if d.get('doc_type') in doc_types]
    
    for doc in documents:
        doc_type = doc.get('doc_type')
        file_id = doc.get('file_id')
        
        if not file_id:
            results['errors'].append(f"No file_id for {doc_type}")
            continue
        
        try:
            # Get file from GridFS
            file_data = await get_file_from_gridfs(file_id)
            if not file_data:
                results['errors'].append(f"Could not retrieve file for {doc_type}")
                continue
            
            # Save to temp file
            file_ext = doc.get('filename', 'file').split('.')[-1] or 'jpg'
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name
            
            try:
                # Run OCR
                ocr_result = await process_document_ocr(tmp_path, doc_type, retry_count=1)
                
                results['documents_processed'].append({
                    "doc_type": doc_type,
                    "status": ocr_result.get('status'),
                    "confidence": ocr_result.get('confidence', 0)
                })
                
                if ocr_result.get('status') == 'processed':
                    results['extracted_data'][doc_type] = ocr_result.get('extracted_data', {})
                else:
                    results['errors'].append(f"OCR failed for {doc_type}: {ocr_result.get('error')}")
                    
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Error processing {doc_type}: {e}")
            results['errors'].append(f"Error processing {doc_type}: {str(e)}")
    
    results['status'] = 'completed' if results['documents_processed'] else 'failed'
    return results


async def compare_ocr_with_client_data(client_id: str) -> Dict[str, Any]:
    """
    Compare OCR extracted data with stored client data to find discrepancies
    """
    from database import db
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        return {"status": "error", "error": "Client not found"}
    
    # Rerun OCR
    ocr_results = await rerun_ocr_for_client(client_id)
    if ocr_results.get('status') == 'failed':
        return ocr_results
    
    discrepancies = []
    
    # Compare PAN card data
    pan_data = ocr_results.get('extracted_data', {}).get('pan_card', {})
    if pan_data:
        if pan_data.get('pan_number') and pan_data['pan_number'] != client.get('pan_number'):
            discrepancies.append({
                "field": "pan_number",
                "source": "pan_card",
                "ocr_value": pan_data['pan_number'],
                "stored_value": client.get('pan_number')
            })
        if pan_data.get('name') and pan_data['name'].upper() != (client.get('name') or '').upper():
            discrepancies.append({
                "field": "name",
                "source": "pan_card",
                "ocr_value": pan_data['name'],
                "stored_value": client.get('name')
            })
    
    # Compare cancelled cheque data
    cheque_data = ocr_results.get('extracted_data', {}).get('cancelled_cheque', {})
    if cheque_data:
        # Check bank details
        banks = client.get('bank_details', [])
        if banks:
            primary_bank = banks[0] if banks else {}
            if cheque_data.get('account_number') and cheque_data['account_number'] != primary_bank.get('account_number'):
                discrepancies.append({
                    "field": "account_number",
                    "source": "cancelled_cheque",
                    "ocr_value": cheque_data['account_number'],
                    "stored_value": primary_bank.get('account_number')
                })
            if cheque_data.get('ifsc_code') and cheque_data['ifsc_code'] != primary_bank.get('ifsc_code'):
                discrepancies.append({
                    "field": "ifsc_code",
                    "source": "cancelled_cheque",
                    "ocr_value": cheque_data['ifsc_code'],
                    "stored_value": primary_bank.get('ifsc_code')
                })
    
    # Compare CML data
    cml_data = ocr_results.get('extracted_data', {}).get('cml_copy', {})
    if cml_data:
        if cml_data.get('dp_id') and cml_data['dp_id'] != client.get('dp_id'):
            discrepancies.append({
                "field": "dp_id",
                "source": "cml_copy",
                "ocr_value": cml_data['dp_id'],
                "stored_value": client.get('dp_id')
            })
        if cml_data.get('client_id') and cml_data['client_id'] != client.get('client_id'):
            discrepancies.append({
                "field": "client_id",
                "source": "cml_copy",
                "ocr_value": cml_data['client_id'],
                "stored_value": client.get('client_id')
            })
        if cml_data.get('email') and cml_data['email'].lower() != (client.get('email') or '').lower():
            discrepancies.append({
                "field": "email",
                "source": "cml_copy",
                "ocr_value": cml_data['email'],
                "stored_value": client.get('email')
            })
    
    return {
        "status": "completed",
        "client_id": client_id,
        "client_name": client.get('name'),
        "ocr_results": ocr_results,
        "discrepancies": discrepancies,
        "has_discrepancies": len(discrepancies) > 0
    }
