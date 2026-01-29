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
