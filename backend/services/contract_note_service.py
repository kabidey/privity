"""
Confirmation Note Service
Generates Confirmation Notes (Conformation Note cum Bill) for share transactions
Sent to clients after DP transfer
"""
import io
import os
import uuid
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, HRFlowable
)
from num2words import num2words

from database import db


def safe_str(value, default="N/A"):
    """Safely convert value to string, returning default for None or empty values"""
    if value is None or value == "":
        return default
    return str(value)


def amount_to_words(amount: float) -> str:
    """Convert amount to words in Indian format"""
    try:
        rupees = int(amount)
        paise = int((amount - rupees) * 100)
        
        words = num2words(rupees, lang='en_IN').replace(',', '').title()
        
        if paise > 0:
            paise_words = num2words(paise, lang='en_IN').title()
            return f"{words} Rupees and {paise_words} Paise Only"
        return f"{words} Rupees Only"
    except (ValueError, TypeError):
        return f"INR {amount:,.2f}"


async def get_company_master():
    """Get company master settings"""
    master = await db.company_master.find_one({"_id": "company_settings"})
    return master or {}


async def generate_contract_note_number():
    """Generate unique contract note number"""
    # Format: SMIFS/CN/YY-YY/XXX
    now = datetime.now()
    year_start = now.year if now.month >= 4 else now.year - 1
    year_end = year_start + 1
    
    # Count existing contract notes for this financial year
    fy_start = f"{year_start}-04-01"
    count = await db.contract_notes.count_documents({
        "created_at": {"$gte": fy_start}
    })
    
    serial = str(count + 1).zfill(4)
    return f"SMIFS/CN/{str(year_start)[2:]}-{str(year_end)[2:]}/{serial}"


async def generate_contract_note_pdf(booking: dict) -> io.BytesIO:
    """
    Generate beautiful Conformation Note cum Bill PDF for a booking after DP transfer
    
    Args:
        booking: The booking document with client, stock, and transaction details
    
    Returns:
        BytesIO buffer containing the PDF
    """
    # Get company master - use defaults if not found
    company = await get_company_master()
    if not company:
        company = {
            "company_name": "SMIFS Management Services Limited",
            "company_address": "Administrative Office: 14th Floor, Mahendra Chambers, 8A Royd Street, Kolkata - 700016",
            "company_pan": "AAACS2814G",
            "company_cin": "U74999WB2000PLC091102",
            "company_gst": "19AAACS2814G1ZS",
            "company_bank_name": "HDFC Bank",
            "company_bank_account": "50200012345678",
            "company_bank_ifsc": "HDFC0000123",
            "company_bank_branch": "Park Street, Kolkata",
            "cdsl_dp_id": "12345678",
            "nsdl_dp_id": "IN123456"
        }
    
    # Get client details - use defaults for sample
    client = await db.clients.find_one({"id": booking.get("client_id")}, {"_id": 0})
    if not client:
        client = {
            "name": "Sample Buyer Private Limited",
            "pan_number": "AAAAA0000A",
            "address": "123 Business Park, Mumbai, Maharashtra 400001",
            "email": "buyer@example.com",
            "dp_name": "CDSL Depository",
            "dp_id": "12345678",
            "client_id": "1234567890123456"
        }
    
    # Get stock details - use defaults for sample
    stock = await db.stocks.find_one({"id": booking.get("stock_id")}, {"_id": 0})
    if not stock:
        stock = {
            "name": "NATIONAL STOCK EXCHANGE OF INDIA",
            "symbol": "NSE",
            "isin_number": "INE721I01024",
            "face_value": 1.00
        }
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.2*cm,
        bottomMargin=1.2*cm
    )
    
    # Color scheme - Professional emerald green theme
    primary_color = colors.Color(0.02, 0.31, 0.23)  # Dark emerald
    secondary_color = colors.Color(0.06, 0.47, 0.35)  # Lighter emerald
    accent_color = colors.Color(0.85, 0.65, 0.13)  # Gold accent
    light_bg = colors.Color(0.97, 0.99, 0.97)  # Very light green tint
    border_color = colors.Color(0.8, 0.85, 0.8)  # Light border
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        textColor=primary_color,
        spaceAfter=8,
        fontName='Helvetica-Bold',
        leading=20
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.Color(0.4, 0.4, 0.4),
        spaceAfter=6
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        borderPadding=4
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.Color(0.4, 0.4, 0.4),
        leading=10
    )
    
    value_style = ParagraphStyle(
        'ValueStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.Color(0.1, 0.1, 0.1),
        leading=12,
        fontName='Helvetica'
    )
    
    small_style = ParagraphStyle(
        'SmallStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=10,
        textColor=colors.Color(0.45, 0.45, 0.45)
    )
    
    elements = []
    
    # ==================== HEADER SECTION ====================
    company_name = safe_str(company.get("company_name"), "SMIFS Capital Markets Ltd")
    company_address = safe_str(company.get("company_address"), "")
    logo_url = company.get("logo_url")
    
    # Build header with or without logo
    header_elements = []
    
    # Company name - large and prominent
    header_elements.append(Paragraph(f"<b>{company_name}</b>", ParagraphStyle(
        'CompanyName',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        spaceAfter=2
    )))
    
    # Company address
    if company_address:
        # Truncate long addresses
        addr_display = company_address[:80] + "..." if len(company_address) > 80 else company_address
        header_elements.append(Paragraph(addr_display, ParagraphStyle(
            'CompanyAddr',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.Color(0.4, 0.4, 0.4),
            spaceAfter=2
        )))
    
    # Registration details in a single line
    reg_parts = []
    cin = company.get("company_cin")
    pan = company.get("company_pan")
    gst = company.get("company_gst")
    if cin:
        reg_parts.append(f"CIN: {cin}")
    if pan:
        reg_parts.append(f"PAN: {pan}")
    if gst:
        reg_parts.append(f"GST: {gst}")
    
    if reg_parts:
        header_elements.append(Paragraph(" | ".join(reg_parts), ParagraphStyle(
            'RegDetails',
            parent=styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
            textColor=colors.Color(0.5, 0.5, 0.5)
        )))
    
    for elem in header_elements:
        elements.append(elem)
    
    elements.append(Spacer(1, 0.4*cm))
    
    # Decorative divider
    elements.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceAfter=0.3*cm))
    
    # ==================== DOCUMENT TITLE ====================
    elements.append(Paragraph("<b>CONFORMATION NOTE CUM BILL</b>", title_style))
    elements.append(Paragraph("(Sale of Unlisted Equity Shares)", subtitle_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== DOCUMENT INFO BOX ====================
    contract_number = booking.get("contract_note_number", await generate_contract_note_number())
    contract_date = booking.get("stock_transfer_date", datetime.now().strftime("%d-%b-%Y"))
    trade_date = booking.get("booking_date", "")
    settlement_date = booking.get("payment_completed_date", contract_date)
    
    # Create a clean info box
    info_data = [
        [
            Paragraph("<b>Conformation No:</b>", label_style),
            Paragraph(f"<b>{contract_number}</b>", ParagraphStyle('Value', fontSize=9, textColor=primary_color, fontName='Helvetica-Bold')),
            Paragraph("<b>Date:</b>", label_style),
            Paragraph(contract_date, value_style)
        ],
        [
            Paragraph("<b>Trade Date:</b>", label_style),
            Paragraph(trade_date, value_style),
            Paragraph("<b>Settlement:</b>", label_style),
            Paragraph(settlement_date, value_style)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[3*cm, 5.5*cm, 3*cm, 5.5*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # ==================== BUYER DETAILS ====================
    elements.append(Paragraph("BUYER DETAILS", section_title))
    
    client_name = client.get("name", "N/A") if client else "N/A"
    client_pan = client.get("pan_number", "N/A") if client else "N/A"
    client_address = client.get("address", "N/A") if client else "N/A"
    # Truncate long addresses
    if len(client_address) > 60:
        client_address = client_address[:60] + "..."
    
    buyer_data = [
        [Paragraph("<b>Name</b>", label_style), Paragraph(client_name, value_style)],
        [Paragraph("<b>PAN</b>", label_style), Paragraph(client_pan, value_style)],
        [Paragraph("<b>Address</b>", label_style), Paragraph(client_address, value_style)],
    ]
    
    # Add demat details if available
    if client:
        dp_info_parts = []
        if client.get("dp_name"):
            dp_info_parts.append(f"DP: {client.get('dp_name')}")
        if client.get("dp_id"):
            dp_info_parts.append(f"DP ID: {client.get('dp_id')}")
        if client.get("client_id") or client.get("otc_ucc"):
            dp_info_parts.append(f"Client ID: {client.get('client_id') or client.get('otc_ucc')}")
        
        if dp_info_parts:
            buyer_data.append([
                Paragraph("<b>Demat</b>", label_style), 
                Paragraph(" | ".join(dp_info_parts), value_style)
            ])
    
    buyer_table = Table(buyer_data, colWidths=[3*cm, 14*cm])
    buyer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, border_color),
    ]))
    elements.append(buyer_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== SELLER DETAILS ====================
    elements.append(Paragraph("SELLER DETAILS", section_title))
    
    seller_data = [
        [Paragraph("<b>Name</b>", label_style), Paragraph(company_name, value_style)],
        [Paragraph("<b>PAN</b>", label_style), Paragraph(company.get("company_pan") or "N/A", value_style)],
    ]
    
    # Add seller demat info
    seller_demat_parts = []
    if company.get("cdsl_dp_id"):
        seller_demat_parts.append(f"CDSL: {company.get('cdsl_dp_id')}")
    if company.get("nsdl_dp_id"):
        seller_demat_parts.append(f"NSDL: {company.get('nsdl_dp_id')}")
    
    if seller_demat_parts:
        seller_data.append([
            Paragraph("<b>Demat</b>", label_style), 
            Paragraph(" | ".join(seller_demat_parts), value_style)
        ])
    
    seller_table = Table(seller_data, colWidths=[3*cm, 14*cm])
    seller_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, border_color),
    ]))
    elements.append(seller_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # ==================== TRANSACTION DETAILS ====================
    elements.append(Paragraph("TRANSACTION DETAILS", section_title))
    
    stock_name = stock.get("name", "N/A") if stock else "N/A"
    stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
    isin = stock.get("isin_number", "N/A") if stock else "N/A"
    face_value = stock.get("face_value", 1) if stock else 1
    
    quantity = booking.get("quantity", 0)
    rate = booking.get("selling_price", 0)
    gross_amount = quantity * rate
    
    # Truncate long stock names
    stock_display = stock_symbol
    if stock_name and len(stock_name) > 25:
        stock_display = f"{stock_symbol}\n{stock_name[:25]}..."
    elif stock_name:
        stock_display = f"{stock_symbol}\n{stock_name}"
    
    # Transaction table header
    trans_header = [
        Paragraph("<b>Script</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>ISIN</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Face Value</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Qty</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Rate (₹)</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
        Paragraph("<b>Amount (₹)</b>", ParagraphStyle('TH', fontSize=8, textColor=colors.white, alignment=TA_CENTER)),
    ]
    
    trans_data = [
        Paragraph(stock_display, ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER, leading=10)),
        Paragraph(isin, ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER)),
        Paragraph(f"₹{face_value:.2f}", ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER)),
        Paragraph(f"{quantity:,}", ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER)),
        Paragraph(f"₹{rate:,.2f}", ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER)),
        Paragraph(f"₹{gross_amount:,.2f}", ParagraphStyle('TD', fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold')),
    ]
    
    trans_table = Table([trans_header, trans_data], colWidths=[3.5*cm, 3.5*cm, 2*cm, 2*cm, 2.5*cm, 3.5*cm])
    trans_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), light_bg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(trans_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # ==================== FINANCIAL SUMMARY ====================
    elements.append(Paragraph("FINANCIAL SUMMARY", section_title))
    
    # Stamp duty calculation
    stamp_duty_rate = 0.00015  # 0.015%
    stamp_duty = round(gross_amount * stamp_duty_rate, 2)
    net_amount = gross_amount  # Stamp duty shown separately
    
    summary_data = [
        [Paragraph("Gross Amount", value_style), Paragraph(f"₹ {gross_amount:,.2f}", ParagraphStyle('Amount', fontSize=9, alignment=TA_CENTER))],
        [Paragraph("Stamp Duty (0.015%)", value_style), Paragraph(f"₹ {stamp_duty:,.2f}", ParagraphStyle('Amount', fontSize=9, alignment=TA_CENTER))],
        [
            Paragraph("<b>Net Payable Amount</b>", ParagraphStyle('NetLabel', fontSize=10, fontName='Helvetica-Bold', textColor=primary_color)),
            Paragraph(f"<b>₹ {net_amount:,.2f}</b>", ParagraphStyle('NetAmount', fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=primary_color))
        ],
    ]
    
    summary_table = Table(summary_data, colWidths=[12*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, primary_color),
        ('BACKGROUND', (0, -1), (-1, -1), light_bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    
    # Amount in words
    elements.append(Spacer(1, 0.2*cm))
    amount_words = amount_to_words(net_amount)
    elements.append(Paragraph(f"<b>Amount in Words:</b> <i>{amount_words}</i>", ParagraphStyle(
        'AmountWords', fontSize=8, textColor=colors.Color(0.3, 0.3, 0.3), leading=12
    )))
    elements.append(Spacer(1, 0.4*cm))
    
    # ==================== BANK DETAILS ====================
    elements.append(Paragraph("PAYMENT DETAILS", section_title))
    
    bank_data = [
        [
            Paragraph("<b>Bank Name</b>", label_style),
            Paragraph(company.get("company_bank_name") or "N/A", value_style),
            Paragraph("<b>Branch</b>", label_style),
            Paragraph(company.get("company_bank_branch") or "N/A", value_style)
        ],
        [
            Paragraph("<b>Account No.</b>", label_style),
            Paragraph(company.get("company_bank_account") or "N/A", value_style),
            Paragraph("<b>IFSC</b>", label_style),
            Paragraph(company.get("company_bank_ifsc") or "N/A", value_style)
        ],
    ]
    
    bank_table = Table(bank_data, colWidths=[2.8*cm, 5.7*cm, 2.8*cm, 5.7*cm])
    bank_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.98, 0.97, 0.90)),  # Light cream
        ('BOX', (0, 0), (-1, -1), 1, accent_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.Color(0.9, 0.85, 0.7)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(bank_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # ==================== TERMS & CONDITIONS ====================
    elements.append(Paragraph("TERMS & CONDITIONS", section_title))
    
    terms = [
        "1. This conformation note is issued for the sale of unlisted equity shares.",
        "2. All FEMA related compliance (if any) is the sole responsibility of the purchaser.",
        "3. The purchaser is responsible for all regulatory compliances including Income Tax and GST.",
        "4. Unlisted securities may have limited liquidity and their value can fluctuate.",
        "5. Payment should be made via RTGS/NEFT/IMPS to the bank account mentioned above.",
        "6. Any discrepancy should be reported within 3 working days.",
        "7. This document is computer generated and does not require physical signature.",
    ]
    
    for term in terms:
        elements.append(Paragraph(term, small_style))
        elements.append(Spacer(1, 0.1*cm))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # ==================== SIGNATURES ====================
    sig_data = [
        [
            Paragraph(f"<b>For {company_name}</b>", ParagraphStyle('SigHeader', fontSize=8, alignment=TA_CENTER, textColor=primary_color)),
            Paragraph("<b>For Purchaser</b>", ParagraphStyle('SigHeader', fontSize=8, alignment=TA_CENTER, textColor=primary_color))
        ],
        ["", ""],
        ["", ""],
        [
            Paragraph("_____________________", ParagraphStyle('SigLine', fontSize=8, alignment=TA_CENTER)),
            Paragraph("_____________________", ParagraphStyle('SigLine', fontSize=8, alignment=TA_CENTER))
        ],
        [
            Paragraph("Authorized Signatory", ParagraphStyle('SigLabel', fontSize=7, alignment=TA_CENTER, textColor=colors.Color(0.5, 0.5, 0.5))),
            Paragraph("Authorized Signatory", ParagraphStyle('SigLabel', fontSize=7, alignment=TA_CENTER, textColor=colors.Color(0.5, 0.5, 0.5)))
        ]
    ]
    
    sig_table = Table(sig_data, colWidths=[8.5*cm, 8.5*cm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


async def create_and_save_contract_note(booking_id: str, user_id: str, user_name: str) -> dict:
    """
    Create contract note for a booking and save to database with GridFS storage
    
    Args:
        booking_id: The booking ID
        user_id: The user creating the contract note
        user_name: The user's name
    
    Returns:
        Contract note document
    """
    from services.file_storage import upload_file_to_gridfs, get_file_url
    
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise ValueError("Booking not found")
    
    # Generate contract note number
    cn_number = await generate_contract_note_number()
    
    # Generate PDF
    pdf_buffer = await generate_contract_note_pdf(booking)
    pdf_content = pdf_buffer.getvalue()
    
    # Generate filename
    filename = f"CN_{cn_number.replace('/', '_')}_{booking_id[:8]}.pdf"
    
    # Upload to GridFS for persistent storage
    file_id = await upload_file_to_gridfs(
        pdf_content,
        filename,
        "application/pdf",
        {
            "category": "contract_notes",
            "entity_id": booking_id,
            "contract_note_number": cn_number,
            "client_id": booking.get("client_id"),
            "created_by": user_id
        }
    )
    
    # Also save locally for backward compatibility
    import os
    cn_dir = "/app/uploads/contract_notes"
    os.makedirs(cn_dir, exist_ok=True)
    filepath = os.path.join(cn_dir, filename)
    
    try:
        with open(filepath, "wb") as f:
            f.write(pdf_content)
    except Exception as e:
        print(f"Warning: Local file save failed: {e}")
    
    # Create contract note record with GridFS info
    cn_doc = {
        "id": str(uuid.uuid4()),
        "contract_note_number": cn_number,
        "booking_id": booking_id,
        "booking_number": booking.get("booking_number"),
        "client_id": booking.get("client_id"),
        "stock_id": booking.get("stock_id"),
        "quantity": booking.get("quantity"),
        "rate": booking.get("selling_price"),
        "gross_amount": booking.get("quantity", 0) * booking.get("selling_price", 0),
        "net_amount": booking.get("quantity", 0) * booking.get("selling_price", 0),
        "file_id": file_id,  # GridFS file ID
        "pdf_url": get_file_url(file_id),  # GridFS URL
        "status": "generated",
        "email_sent": False,
        "created_by": user_id,
        "created_by_name": user_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.contract_notes.insert_one(cn_doc)
    
    # Update booking with contract note reference
    await db.bookings.update_one(
        {"id": booking_id},
        {
            "$set": {
                "contract_note_number": cn_number,
                "contract_note_id": cn_doc["id"],
                "contract_note_generated_at": cn_doc["created_at"]
            }
        }
    )
    
    return cn_doc


# ==================== VENDOR PURCHASE CONTRACT NOTE ====================

async def generate_vendor_purchase_contract_note_number():
    """Generate unique purchase contract note number for vendors"""
    now = datetime.now()
    year_start = now.year if now.month >= 4 else now.year - 1
    year_end = year_start + 1
    
    # Count existing vendor contract notes for this financial year
    fy_start = f"{year_start}-04-01"
    count = await db.vendor_contract_notes.count_documents({
        "created_at": {"$gte": fy_start}
    })
    
    serial = str(count + 1).zfill(4)
    return f"SMIFS/PCN/{str(year_start)[2:]}-{str(year_end)[2:]}/{serial}"


async def generate_vendor_purchase_contract_note_pdf(purchase: dict) -> io.BytesIO:
    """
    Generate Purchase Confirmation Note PDF for a vendor purchase after DP received
    
    Args:
        purchase: The purchase document with vendor, stock, and transaction details
    
    Returns:
        BytesIO buffer containing the PDF
    """
    # Get company master
    company = await get_company_master()
    
    # Get vendor details
    vendor = await db.clients.find_one({"id": purchase.get("vendor_id")}, {"_id": 0})
    
    # Get stock details
    stock = await db.stocks.find_one({"id": purchase.get("stock_id")}, {"_id": 0})
    
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Page setup
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a1a'),
        fontName='Helvetica-Bold'
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        fontSize=10,
        spaceAfter=8,
        spaceBefore=10,
        textColor=colors.HexColor('#065f46'),  # Green for purchase
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        fontSize=9,
        leading=12,
        alignment=TA_LEFT
    )
    
    small_style = ParagraphStyle(
        'Small',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#666666')
    )
    
    elements = []
    
    # Company details
    company_name = company.get("company_name", "SMIFS Capital Markets Ltd")
    
    # Header
    elements.append(Paragraph(f"<b>{company_name}</b>", title_style))
    elements.append(Paragraph(
        company.get("company_address", ""),
        ParagraphStyle('Address', fontSize=8, alignment=TA_CENTER)
    ))
    
    # CIN & Contact
    cin_gstin = f"CIN: {company.get('company_cin', 'N/A')} | GSTIN: {company.get('company_gstin', 'N/A')}"
    elements.append(Paragraph(cin_gstin, ParagraphStyle('CIN', fontSize=7, alignment=TA_CENTER, textColor=colors.grey)))
    
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#065f46')))
    elements.append(Spacer(1, 0.2*cm))
    
    # Document Title
    elements.append(Paragraph("<b>PURCHASE CONFIRMATION NOTE</b>", 
        ParagraphStyle('DocTitle', fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#065f46'), fontName='Helvetica-Bold')
    ))
    elements.append(Paragraph("(Stock Purchase Acknowledgment)", 
        ParagraphStyle('Subtitle', fontSize=9, alignment=TA_CENTER, textColor=colors.grey)
    ))
    elements.append(Spacer(1, 0.4*cm))
    
    # Contract Note Details (Left) and Date (Right)
    cn_number = purchase.get("purchase_contract_note_number", "")
    cn_date = datetime.now().strftime('%d-%b-%Y')
    
    header_data = [
        [f"<b>PCN No:</b> {cn_number}", f"<b>Date:</b> {cn_date}"],
        [f"<b>Purchase Order:</b> {purchase.get('purchase_number', '')}", f"<b>DP Type:</b> {purchase.get('dp_type', 'N/A')}"],
    ]
    
    header_table = Table(
        [[Paragraph(c, normal_style) for c in row] for row in header_data],
        colWidths=[9*cm, 6*cm]
    )
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Vendor Details Section
    elements.append(Paragraph("<b>VENDOR DETAILS (SELLER)</b>", section_title))
    
    vendor_name = vendor.get("name", "N/A") if vendor else "N/A"
    vendor_pan = vendor.get("pan_number", "N/A") if vendor else "N/A"
    vendor_address = vendor.get("address", "N/A") if vendor else "N/A"
    vendor_email = vendor.get("email", "N/A") if vendor else "N/A"
    vendor_phone = vendor.get("phone", "N/A") if vendor else "N/A"
    
    vendor_data = [
        ["Name:", vendor_name],
        ["PAN:", vendor_pan],
        ["Address:", vendor_address],
        ["Email:", vendor_email],
        ["Phone:", vendor_phone],
    ]
    
    vendor_table = Table(vendor_data, colWidths=[3*cm, 12*cm])
    vendor_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0fdf4')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#86efac')),
    ]))
    elements.append(vendor_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Stock Details Section
    elements.append(Paragraph("<b>STOCK DETAILS</b>", section_title))
    
    stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
    stock_name = stock.get("name", "N/A") if stock else "N/A"
    stock_isin = stock.get("isin_number", "N/A") if stock else "N/A"
    
    stock_data = [
        ["Stock Symbol:", stock_symbol, "ISIN:", stock_isin],
        ["Stock Name:", stock_name, "", ""],
    ]
    
    stock_table = Table(stock_data, colWidths=[3*cm, 6*cm, 2.5*cm, 3.5*cm])
    stock_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(stock_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Transaction Details
    elements.append(Paragraph("<b>TRANSACTION DETAILS</b>", section_title))
    
    quantity = purchase.get("quantity", 0)
    price_per_share = purchase.get("price_per_share", 0)
    total_amount = purchase.get("total_amount", 0)
    
    txn_data = [
        ["Description", "Quantity", "Rate (₹)", "Amount (₹)"],
        [f"Purchase of {stock_symbol} shares", f"{quantity:,}", f"{price_per_share:,.2f}", f"{total_amount:,.2f}"],
    ]
    
    txn_table = Table(txn_data, colWidths=[7*cm, 3*cm, 3*cm, 3*cm])
    txn_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#065f46')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(txn_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Payment Summary
    elements.append(Paragraph("<b>PAYMENT SUMMARY</b>", section_title))
    
    total_paid = purchase.get("total_paid", 0)
    
    # Get TCS details if any
    tcs_total = 0
    payments = await db.purchase_payments.find({"purchase_id": purchase.get("id")}, {"_id": 0}).to_list(100)
    for p in payments:
        tcs_total += p.get("tcs_amount", 0)
    
    net_paid = total_paid - tcs_total
    
    summary_data = [
        ["Total Purchase Amount:", f"₹{total_amount:,.2f}"],
        ["Total Amount Paid:", f"₹{total_paid:,.2f}"],
        ["TCS Deducted @0.1%:", f"₹{tcs_total:,.2f}"],
        ["Net Amount Transferred:", f"₹{net_paid:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Amount in Words
    elements.append(Paragraph(f"<b>Amount in Words:</b> {amount_to_words(total_amount)}", normal_style))
    elements.append(Spacer(1, 0.4*cm))
    
    # DP Receipt Confirmation
    elements.append(Paragraph("<b>DP RECEIPT CONFIRMATION</b>", section_title))
    
    dp_received_at = purchase.get("dp_received_at", "")
    if dp_received_at:
        try:
            dp_date = datetime.fromisoformat(dp_received_at.replace('Z', '+00:00')).strftime('%d-%b-%Y %H:%M')
        except (ValueError, TypeError):
            dp_date = dp_received_at
    else:
        dp_date = "N/A"
    
    dp_data = [
        ["Stock Received Via:", purchase.get("dp_type", "N/A")],
        ["Received Date:", dp_date],
        ["Received By:", purchase.get("dp_received_by_name", "N/A")],
        ["Quantity Received:", f"{quantity:,} shares"],
    ]
    
    dp_table = Table(dp_data, colWidths=[4*cm, 11*cm])
    dp_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecfdf5')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#10b981')),
    ]))
    elements.append(dp_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Terms & Conditions
    elements.append(Paragraph("<b>TERMS & CONDITIONS</b>", section_title))
    
    terms = [
        "1. This purchase contract note confirms receipt of shares from the vendor.",
        "2. TCS @0.1% has been deducted as per Section 194Q of the Income Tax Act (if applicable).",
        "3. The shares have been credited to our depository account as per the DP type mentioned above.",
        "4. Any discrepancy should be reported within 3 working days from receipt of this document.",
        "5. This document is computer generated and does not require physical signature.",
    ]
    
    for term in terms:
        elements.append(Paragraph(term, small_style))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # Signatures
    sig_data = [
        [f"For {company_name}", f"For {vendor_name}"],
        ["", ""],
        ["", ""],
        ["Authorized Signatory", "Vendor Acknowledgment"]
    ]
    
    sig_table = Table(sig_data, colWidths=[7.5*cm, 7.5*cm])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


async def create_and_save_vendor_contract_note(purchase_id: str, user_id: str, user_name: str) -> dict:
    """
    Create purchase contract note for a vendor and save to database
    
    Args:
        purchase_id: The purchase ID
        user_id: The user creating the contract note
        user_name: The user's name
    
    Returns:
        Vendor contract note document
    """
    purchase = await db.purchases.find_one({"id": purchase_id}, {"_id": 0})
    if not purchase:
        raise ValueError("Purchase not found")
    
    # Generate contract note number
    cn_number = await generate_vendor_purchase_contract_note_number()
    
    # Update purchase with contract note number for PDF generation
    purchase["purchase_contract_note_number"] = cn_number
    
    # Generate PDF
    pdf_buffer = await generate_vendor_purchase_contract_note_pdf(purchase)
    
    # Save PDF to disk
    cn_dir = "/app/uploads/vendor_contract_notes"
    os.makedirs(cn_dir, exist_ok=True)
    
    filename = f"PCN_{cn_number.replace('/', '_')}_{purchase_id[:8]}.pdf"
    filepath = os.path.join(cn_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    # Get vendor details
    vendor = await db.clients.find_one({"id": purchase.get("vendor_id")}, {"_id": 0})
    
    # Create contract note record
    cn_doc = {
        "id": str(uuid.uuid4()),
        "contract_note_number": cn_number,
        "purchase_id": purchase_id,
        "purchase_number": purchase.get("purchase_number"),
        "vendor_id": purchase.get("vendor_id"),
        "vendor_name": vendor.get("name") if vendor else "Unknown",
        "stock_id": purchase.get("stock_id"),
        "quantity": purchase.get("quantity"),
        "rate": purchase.get("price_per_share"),
        "total_amount": purchase.get("total_amount"),
        "pdf_url": f"/uploads/vendor_contract_notes/{filename}",
        "status": "generated",
        "email_sent": False,
        "created_by": user_id,
        "created_by_name": user_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.vendor_contract_notes.insert_one(cn_doc)
    
    # Update purchase with contract note reference
    await db.purchases.update_one(
        {"id": purchase_id},
        {
            "$set": {
                "contract_note_number": cn_number,
                "contract_note_id": cn_doc["id"],
                "contract_note_generated_at": cn_doc["created_at"]
            }
        }
    )
    
    return cn_doc
