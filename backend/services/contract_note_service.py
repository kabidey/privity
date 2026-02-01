"""
Contract Note Service
Generates Contract Notes (Contract cum Bill) for share transactions
Sent to clients after DP transfer
"""
import io
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, HRFlowable
)
from reportlab.pdfgen import canvas
from num2words import num2words

from database import db


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
    except:
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
    Generate Contract Note PDF for a booking after DP transfer
    
    Args:
        booking: The booking document with client, stock, and transaction details
    
    Returns:
        BytesIO buffer containing the PDF
    """
    # Get company master
    company = await get_company_master()
    
    # Get client details
    client = await db.clients.find_one({"id": booking.get("client_id")}, {"_id": 0})
    
    # Get stock details
    stock = await db.stocks.find_one({"id": booking.get("stock_id")}, {"_id": 0})
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        textColor=colors.Color(0.02, 0.3, 0.23),
        spaceAfter=10
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.Color(0.3, 0.3, 0.3)
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=colors.Color(0.02, 0.3, 0.23),
        spaceBefore=10,
        spaceAfter=5
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12
    )
    
    small_style = ParagraphStyle(
        'SmallStyle',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        textColor=colors.Color(0.4, 0.4, 0.4)
    )
    
    elements = []
    
    # ==================== HEADER WITH LOGO ====================
    company_name = company.get("company_name", "SMIFS Capital Markets Ltd")
    company_address = company.get("company_address", "")
    logo_url = company.get("logo_url")
    
    # Create header with logo and company name side by side
    header_content = []
    
    # Check if logo exists and add it
    if logo_url:
        logo_path = f"/app{logo_url}" if logo_url.startswith("/uploads") else logo_url
        if os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=1.5*cm, height=1.5*cm)
                logo_img.hAlign = 'LEFT'
                header_content.append(logo_img)
            except Exception as e:
                # If logo fails to load, skip it
                pass
    
    # Company name and details
    company_info = f"<b>{company_name}</b>"
    if company_address:
        company_info += f"<br/><font size='9' color='#555555'>{company_address}</font>"
    
    # Registration details
    reg_details = []
    if company.get("company_cin"):
        reg_details.append(f"CIN: {company.get('company_cin')}")
    if company.get("company_pan"):
        reg_details.append(f"PAN: {company.get('company_pan')}")
    if company.get("company_gst"):
        reg_details.append(f"GST: {company.get('company_gst')}")
    
    if reg_details:
        company_info += f"<br/><font size='8' color='#666666'>{' | '.join(reg_details)}</font>"
    
    # Create header table with logo and company info
    if logo_url and os.path.exists(f"/app{logo_url}" if logo_url.startswith("/uploads") else logo_url):
        try:
            logo_path = f"/app{logo_url}" if logo_url.startswith("/uploads") else logo_url
            logo_img = Image(logo_path, width=2*cm, height=2*cm)
            
            header_table_data = [[
                logo_img,
                Paragraph(company_info, ParagraphStyle(
                    'CompanyHeader',
                    parent=styles['Normal'],
                    fontSize=12,
                    alignment=TA_CENTER,
                    leading=14
                ))
            ]]
            
            header_table = Table(header_table_data, colWidths=[2.5*cm, 14*cm])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(header_table)
        except:
            # Fallback to text-only header
            elements.append(Paragraph(f"<b>{company_name}</b>", title_style))
            if company_address:
                elements.append(Paragraph(company_address, header_style))
            if reg_details:
                elements.append(Paragraph(" | ".join(reg_details), header_style))
    else:
        # Text-only header (no logo)
        elements.append(Paragraph(f"<b>{company_name}</b>", title_style))
        if company_address:
            elements.append(Paragraph(company_address, header_style))
        if reg_details:
            elements.append(Paragraph(" | ".join(reg_details), header_style))
    
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.Color(0.02, 0.3, 0.23)))
    elements.append(Spacer(1, 0.2*cm))
    
    # ==================== CONTRACT NOTE TITLE ====================
    contract_number = booking.get("contract_note_number", await generate_contract_note_number())
    
    elements.append(Paragraph("<b>CONTRACT NOTE CUM BILL</b>", title_style))
    
    # Contract details table
    contract_date = booking.get("stock_transfer_date", datetime.now().strftime("%d-%b-%Y"))
    trade_date = booking.get("booking_date", "")
    settlement_date = booking.get("payment_completed_date", contract_date)
    
    contract_info = [
        ["Contract No:", contract_number, "Contract Date:", contract_date],
        ["Trade Date:", trade_date, "Settlement Date:", settlement_date],
        ["Transaction Type:", "Our Sale", "Type:", "Equity Shares"]
    ]
    
    contract_table = Table(contract_info, colWidths=[2.5*cm, 5*cm, 2.5*cm, 5*cm])
    contract_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(contract_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== BUYER DETAILS ====================
    elements.append(Paragraph("<b>BUYER DETAILS</b>", section_title))
    
    buyer_data = [
        ["Name:", client.get("name", "N/A") if client else "N/A"],
        ["PAN:", client.get("pan_number", "N/A") if client else "N/A"],
        ["Address:", client.get("address", "N/A") if client else "N/A"],
        ["Email:", client.get("email", "N/A") if client else "N/A"],
    ]
    
    # Client demat details
    demat_info = []
    if client:
        if client.get("dp_name"):
            demat_info.append(["DP Name:", client.get("dp_name")])
        if client.get("dp_id"):
            demat_info.append(["DP ID:", client.get("dp_id")])
        if client.get("client_id") or client.get("otc_ucc"):
            demat_info.append(["Client ID:", client.get("client_id") or client.get("otc_ucc")])
    
    buyer_table = Table(buyer_data, colWidths=[3*cm, 12*cm])
    buyer_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(buyer_table)
    
    if demat_info:
        demat_table = Table(demat_info, colWidths=[3*cm, 12*cm])
        demat_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(demat_table)
    
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== SELLER DETAILS ====================
    elements.append(Paragraph("<b>SELLER DETAILS</b>", section_title))
    
    seller_data = [
        ["Name:", company_name],
        ["PAN:", company.get("company_pan", "N/A")],
        ["Address:", company_address or "N/A"],
    ]
    
    # Seller demat details
    seller_demat = []
    if company.get("cdsl_dp_id"):
        seller_demat.append(["CDSL DP ID:", company.get("cdsl_dp_id")])
    if company.get("nsdl_dp_id"):
        seller_demat.append(["NSDL DP ID:", company.get("nsdl_dp_id")])
    
    seller_table = Table(seller_data, colWidths=[3*cm, 12*cm])
    seller_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(seller_table)
    
    if seller_demat:
        demat_table = Table(seller_demat, colWidths=[3*cm, 12*cm])
        demat_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(demat_table)
    
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== TRANSACTION DETAILS ====================
    elements.append(Paragraph("<b>TRANSACTION DETAILS</b>", section_title))
    
    stock_name = stock.get("name", "N/A") if stock else "N/A"
    stock_symbol = stock.get("symbol", "N/A") if stock else "N/A"
    isin = stock.get("isin_number", "N/A") if stock else "N/A"
    face_value = stock.get("face_value", 1) if stock else 1
    
    quantity = booking.get("quantity", 0)
    rate = booking.get("selling_price", 0)
    gross_amount = quantity * rate
    
    # Calculate charges (typical unlisted share transaction charges)
    stamp_duty_rate = 0.00015  # 0.015%
    stamp_duty = round(gross_amount * stamp_duty_rate, 2)
    
    # Net amount
    net_amount = gross_amount
    
    trans_header = [["Script Name", "ISIN", "Face Value", "Quantity", "Rate (₹)", "Amount (₹)"]]
    trans_data = [[
        f"{stock_symbol}\n{stock_name[:30]}...",
        isin,
        f"₹ {face_value:.2f}",
        str(quantity),
        f"₹ {rate:,.2f}",
        f"₹ {gross_amount:,.2f}"
    ]]
    
    trans_table = Table(trans_header + trans_data, colWidths=[4*cm, 3*cm, 2*cm, 2*cm, 2.5*cm, 3*cm])
    trans_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(trans_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== FINANCIAL SUMMARY ====================
    elements.append(Paragraph("<b>FINANCIAL SUMMARY</b>", section_title))
    
    summary_data = [
        ["Gross Amount:", f"₹ {gross_amount:,.2f}"],
        ["Stamp Duty (0.015%):", f"₹ {stamp_duty:,.2f}"],
        ["", ""],
        ["Net Payable Amount:", f"₹ {net_amount:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, -1), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
    ]))
    elements.append(summary_table)
    
    # Amount in words
    elements.append(Spacer(1, 0.2*cm))
    amount_words = amount_to_words(net_amount)
    elements.append(Paragraph(f"<b>Amount in Words:</b> {amount_words}", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== BANK DETAILS ====================
    elements.append(Paragraph("<b>SELLER BANK DETAILS (For Payment)</b>", section_title))
    
    bank_data = [
        ["Bank Name:", company.get("company_bank_name", "N/A")],
        ["Account Number:", company.get("company_bank_account", "N/A")],
        ["IFSC Code:", company.get("company_bank_ifsc", "N/A")],
        ["Branch:", company.get("company_bank_branch", "N/A")],
    ]
    
    bank_table = Table(bank_data, colWidths=[3*cm, 12*cm])
    bank_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(bank_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # ==================== TERMS & CONDITIONS ====================
    elements.append(Paragraph("<b>TERMS & CONDITIONS</b>", section_title))
    
    terms = [
        "1. This contract note is issued for the sale of unlisted equity shares.",
        "2. All FEMA related compliance (if any) is the sole responsibility of the purchaser.",
        "3. The purchaser is responsible for all regulatory compliances including Income Tax and GST.",
        "4. Unlisted securities may have limited liquidity and their value can fluctuate.",
        "5. Payment should be made via RTGS/NEFT/IMPS to the bank account mentioned above.",
        "6. Any discrepancy should be reported within 3 working days from receipt of this document.",
        "7. This document is computer generated and does not require physical signature.",
    ]
    
    for term in terms:
        elements.append(Paragraph(term, small_style))
    
    elements.append(Spacer(1, 0.5*cm))
    
    # ==================== SIGNATURES ====================
    sig_data = [
        [f"For {company_name}", "For Purchaser"],
        ["", ""],
        ["", ""],
        ["Authorized Signatory", "Authorized Signatory"]
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


async def create_and_save_contract_note(booking_id: str, user_id: str, user_name: str) -> dict:
    """
    Create contract note for a booking and save to database
    
    Args:
        booking_id: The booking ID
        user_id: The user creating the contract note
        user_name: The user's name
    
    Returns:
        Contract note document
    """
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise ValueError("Booking not found")
    
    # Generate contract note number
    cn_number = await generate_contract_note_number()
    
    # Generate PDF
    pdf_buffer = await generate_contract_note_pdf(booking)
    
    # Save PDF to disk
    import os
    cn_dir = "/app/uploads/contract_notes"
    os.makedirs(cn_dir, exist_ok=True)
    
    filename = f"CN_{cn_number.replace('/', '_')}_{booking_id[:8]}.pdf"
    filepath = os.path.join(cn_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    # Create contract note record
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
        "pdf_url": f"/uploads/contract_notes/{filename}",
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
    Generate Purchase Contract Note PDF for a vendor purchase after DP received
    
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
    elements.append(Paragraph("<b>PURCHASE CONTRACT NOTE</b>", 
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
    stock_isin = stock.get("isin", "N/A") if stock else "N/A"
    
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
        except:
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
