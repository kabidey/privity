"""
PRIVITY System Documentation PDF Generator
Generates comprehensive API and Architecture documentation
"""
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, ListFlowable, ListItem
)
from reportlab.platypus.tableofcontents import TableOfContents

# Load OpenAPI spec
with open('/tmp/openapi.json', 'r') as f:
    openapi = json.load(f)

# Create PDF
doc = SimpleDocTemplate(
    '/app/PRIVITY_System_Documentation.pdf',
    pagesize=A4,
    rightMargin=1.5*cm,
    leftMargin=1.5*cm,
    topMargin=2*cm,
    bottomMargin=2*cm
)

# Styles
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name='Title1',
    parent=styles['Heading1'],
    fontSize=24,
    spaceAfter=30,
    textColor=colors.Color(0.02, 0.3, 0.23),
    alignment=TA_CENTER
))
styles.add(ParagraphStyle(
    name='Heading2Custom',
    parent=styles['Heading2'],
    fontSize=16,
    spaceBefore=20,
    spaceAfter=10,
    textColor=colors.Color(0.02, 0.3, 0.23)
))
styles.add(ParagraphStyle(
    name='Heading3Custom',
    parent=styles['Heading3'],
    fontSize=12,
    spaceBefore=15,
    spaceAfter=8,
    textColor=colors.Color(0.1, 0.4, 0.3)
))
styles.add(ParagraphStyle(
    name='BodyCustom',
    parent=styles['Normal'],
    fontSize=10,
    spaceAfter=8,
    alignment=TA_JUSTIFY
))
styles.add(ParagraphStyle(
    name='CodeCustom',
    parent=styles['Normal'],
    fontName='Courier',
    fontSize=8,
    backColor=colors.Color(0.95, 0.95, 0.95),
    leftIndent=10,
    rightIndent=10,
    spaceBefore=5,
    spaceAfter=5
))
styles.add(ParagraphStyle(
    name='TableHeader',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.white,
    alignment=TA_CENTER
))

elements = []

# ============== COVER PAGE ==============
elements.append(Spacer(1, 3*inch))
elements.append(Paragraph("PRIVITY", styles['Title1']))
elements.append(Paragraph("Private Equity Share Booking System", styles['Heading2Custom']))
elements.append(Spacer(1, 0.5*inch))
elements.append(Paragraph("System Architecture & API Documentation", styles['BodyCustom']))
elements.append(Spacer(1, 1*inch))
elements.append(Paragraph(f"Version 2.0.0", styles['BodyCustom']))
elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['BodyCustom']))
elements.append(PageBreak())

# ============== TABLE OF CONTENTS ==============
elements.append(Paragraph("Table of Contents", styles['Heading2Custom']))
elements.append(Spacer(1, 0.3*inch))
toc_items = [
    "1. System Overview",
    "2. Technology Stack",
    "3. Backend Architecture",
    "4. Frontend Architecture", 
    "5. Database Schema",
    "6. User Roles & Permissions",
    "7. API Documentation",
    "8. Third-Party Integrations",
    "9. Security Features"
]
for item in toc_items:
    elements.append(Paragraph(item, styles['BodyCustom']))
elements.append(PageBreak())

# ============== 1. SYSTEM OVERVIEW ==============
elements.append(Paragraph("1. System Overview", styles['Heading2Custom']))
elements.append(Paragraph(
    "PRIVITY is a comprehensive Private Equity Share Booking System designed for SMIFS. "
    "It manages the entire lifecycle of share bookings, from client onboarding to payment settlement, "
    "including support for Referral Partners, inventory management, and financial reporting.",
    styles['BodyCustom']
))
elements.append(Spacer(1, 0.2*inch))

# Key Features
elements.append(Paragraph("Key Features:", styles['Heading3Custom']))
features = [
    "Client & Vendor Management with document verification",
    "Stock/Security Master with corporate actions tracking",
    "Multi-level booking approval workflow",
    "Referral Partner (RP) commission system with bank details",
    "Real-time notifications via WebSocket",
    "Financial reporting with Excel/PDF exports",
    "Email audit logging for compliance",
    "Microsoft Azure AD Single Sign-On",
    "Role-based access control (7 user roles)"
]
for f in features:
    elements.append(Paragraph(f"• {f}", styles['BodyCustom']))
elements.append(PageBreak())

# ============== 2. TECHNOLOGY STACK ==============
elements.append(Paragraph("2. Technology Stack", styles['Heading2Custom']))

tech_data = [
    ["Layer", "Technology", "Version"],
    ["Frontend Framework", "React", "19.0.0"],
    ["UI Components", "Shadcn/UI (Radix)", "Latest"],
    ["Styling", "Tailwind CSS", "3.x"],
    ["Backend Framework", "FastAPI", "0.110.1"],
    ["ASGI Server", "Uvicorn", "0.25.0"],
    ["Database", "MongoDB", "6.x"],
    ["DB Driver", "Motor (async)", "3.3.1"],
    ["Authentication", "JWT + MSAL", "PyJWT 2.10.1"],
    ["Real-time", "WebSockets", "15.0.1"],
]

tech_table = Table(tech_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
tech_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
]))
elements.append(tech_table)
elements.append(PageBreak())

# ============== 3. BACKEND ARCHITECTURE ==============
elements.append(Paragraph("3. Backend Architecture", styles['Heading2Custom']))
elements.append(Paragraph(
    "The backend follows a modular architecture with 18 specialized routers, "
    "each handling a specific domain of the application.",
    styles['BodyCustom']
))

elements.append(Paragraph("Directory Structure:", styles['Heading3Custom']))
backend_structure = """
/app/backend/
├── server.py              # Main FastAPI entry point
├── config.py              # Configuration & constants
├── database.py            # MongoDB connection + indexes
├── models/__init__.py     # Pydantic data models
├── utils/auth.py          # JWT utilities
├── services/              # Business logic services
│   ├── email_service.py   # Email + audit logging
│   ├── notification_service.py
│   ├── ocr_service.py     # Document OCR
│   ├── audit_service.py
│   ├── inventory_service.py
│   └── azure_sso_service.py
└── routers/               # API endpoint modules (18 routers)
"""
elements.append(Paragraph(backend_structure.replace('\n', '<br/>'), styles['Code']))

elements.append(Paragraph("Router Modules:", styles['Heading3Custom']))
routers_data = [
    ["Router", "Prefix", "Description"],
    ["auth.py", "/auth", "Login, register, SSO, password management"],
    ["analytics.py", "/analytics", "Performance metrics & summaries"],
    ["audit_logs.py", "/audit-logs", "Activity audit trail"],
    ["bookings.py", "/bookings", "Booking CRUD with approval workflow"],
    ["clients.py", "/clients", "Client & document management"],
    ["dashboard.py", "/dashboard", "Dashboard statistics"],
    ["email_logs.py", "/email-logs", "Email audit logging"],
    ["email_templates.py", "/email-templates", "Email template management"],
    ["finance.py", "/finance", "Payments, refunds, RP commissions"],
    ["inventory.py", "/inventory", "Stock inventory management"],
    ["notifications.py", "/notifications", "Real-time alerts"],
    ["purchases.py", "/purchases", "Purchase order management"],
    ["referral_partners.py", "/referral-partners", "RP management"],
    ["reports.py", "/reports", "P&L reports, exports"],
    ["smtp_config.py", "/smtp-config", "SMTP configuration"],
    ["stocks.py", "/stocks", "Stock/security master"],
    ["users.py", "/users", "User management"],
    ["database_backup.py", "/backup", "Database backup/restore"],
]

routers_table = Table(routers_data, colWidths=[1.5*inch, 1.3*inch, 3.2*inch])
routers_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
]))
elements.append(routers_table)
elements.append(PageBreak())

# ============== 4. FRONTEND ARCHITECTURE ==============
elements.append(Paragraph("4. Frontend Architecture", styles['Heading2Custom']))
elements.append(Paragraph(
    "The frontend is built with React 19 and uses Shadcn/UI components based on Radix primitives. "
    "It follows a page-based structure with shared context providers for theme and notifications.",
    styles['BodyCustom']
))

elements.append(Paragraph("Key Frontend Dependencies:", styles['Heading3Custom']))
frontend_deps = [
    ["Package", "Purpose"],
    ["react / react-dom", "UI Framework (v19)"],
    ["react-router-dom", "Client-side routing"],
    ["axios", "HTTP client for API calls"],
    ["@radix-ui/*", "Shadcn UI primitives"],
    ["tailwindcss", "Utility-first CSS"],
    ["lucide-react", "Icon library"],
    ["recharts", "Charts and graphs"],
    ["sonner", "Toast notifications"],
    ["@azure/msal-react", "Microsoft SSO"],
    ["date-fns", "Date utilities"],
    ["zod", "Schema validation"],
]
deps_table = Table(frontend_deps, colWidths=[2.5*inch, 3.5*inch])
deps_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
]))
elements.append(deps_table)
elements.append(PageBreak())

# ============== 5. DATABASE SCHEMA ==============
elements.append(Paragraph("5. Database Schema", styles['Heading2Custom']))
elements.append(Paragraph(
    "MongoDB is used as the primary database. Below are the main collections and their purposes.",
    styles['BodyCustom']
))

collections_data = [
    ["Collection", "Description", "Key Fields"],
    ["users", "User accounts", "id, email, name, pan_number, role"],
    ["clients", "Clients & Vendors", "id, name, pan_number, otc_ucc, is_vendor"],
    ["stocks", "Stock/Security master", "id, symbol, name, isin_number, face_value"],
    ["bookings", "Share bookings", "id, booking_number, client_id, stock_id, quantity, status"],
    ["purchases", "Purchase orders", "id, po_number, vendor_id, stock_id, quantity"],
    ["inventory", "Stock inventory", "id, stock_id, available_qty, total_value"],
    ["referral_partners", "RP records", "id, rp_code, name, pan_number, bank_details"],
    ["rp_payments", "RP commissions", "id, booking_id, rp_id, amount, status"],
    ["employee_commissions", "Employee share", "id, booking_id, employee_id, amount"],
    ["refund_requests", "Client refunds", "id, booking_id, amount, status"],
    ["notifications", "Real-time alerts", "id, user_id, message, read, created_at"],
    ["audit_logs", "Activity trail", "id, action, entity_type, user_id, created_at"],
    ["email_logs", "Email history", "id, to_email, subject, status, template_key"],
    ["email_templates", "Email templates", "key, subject, body, is_active"],
    ["email_config", "SMTP settings", "smtp_host, smtp_port, smtp_username"],
]

coll_table = Table(collections_data, colWidths=[1.4*inch, 1.8*inch, 2.8*inch])
coll_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
]))
elements.append(coll_table)
elements.append(PageBreak())

# ============== 6. USER ROLES ==============
elements.append(Paragraph("6. User Roles & Permissions", styles['Heading2Custom']))

roles_data = [
    ["Role ID", "Name", "Access Level"],
    ["1", "PE Desk", "Super Admin - Full system access"],
    ["2", "PE Manager", "Admin - Most features except system config"],
    ["3", "Compliance", "Compliance oversight and approvals"],
    ["4", "Employee", "Create bookings, clients, RPs"],
    ["5", "Viewer", "Read-only access"],
    ["6", "Client", "External - Booking confirmation only"],
    ["7", "Finance", "Finance dashboard, payments, refunds"],
]

roles_table = Table(roles_data, colWidths=[1*inch, 1.5*inch, 3.5*inch])
roles_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
    ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
]))
elements.append(roles_table)
elements.append(PageBreak())

# ============== 7. API DOCUMENTATION ==============
elements.append(Paragraph("7. API Documentation", styles['Heading2Custom']))
elements.append(Paragraph(
    f"Base URL: All endpoints are prefixed with /api<br/>"
    f"Authentication: Bearer token (JWT) in Authorization header<br/>"
    f"Content-Type: application/json",
    styles['BodyCustom']
))
elements.append(Spacer(1, 0.2*inch))

# Group endpoints by tag
endpoints_by_tag = {}
for path, methods in openapi.get('paths', {}).items():
    for method, details in methods.items():
        if method in ['get', 'post', 'put', 'delete', 'patch']:
            tags = details.get('tags', ['Other'])
            tag = tags[0] if tags else 'Other'
            if tag not in endpoints_by_tag:
                endpoints_by_tag[tag] = []
            endpoints_by_tag[tag].append({
                'method': method.upper(),
                'path': path,
                'summary': details.get('summary', 'No description'),
                'description': details.get('description', ''),
                'operationId': details.get('operationId', '')
            })

# Sort tags
sorted_tags = sorted(endpoints_by_tag.keys())

for tag in sorted_tags:
    elements.append(Paragraph(f"7.{sorted_tags.index(tag)+1} {tag}", styles['Heading3Custom']))
    
    endpoints = endpoints_by_tag[tag]
    
    # Create table for this tag's endpoints
    api_data = [["Method", "Endpoint", "Description"]]
    
    for ep in endpoints:
        method = ep['method']
        # Color code methods
        method_color = {
            'GET': 'green',
            'POST': 'blue', 
            'PUT': 'orange',
            'DELETE': 'red',
            'PATCH': 'purple'
        }.get(method, 'black')
        
        # Truncate path if too long
        path = ep['path']
        if len(path) > 45:
            path = path[:42] + '...'
        
        summary = ep['summary']
        if len(summary) > 50:
            summary = summary[:47] + '...'
            
        api_data.append([method, path, summary])
    
    api_table = Table(api_data, colWidths=[0.7*inch, 2.5*inch, 2.8*inch])
    api_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.2)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('FONTNAME', (1, 1), (1, -1), 'Courier'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(api_table)
    elements.append(Spacer(1, 0.15*inch))

elements.append(PageBreak())

# ============== 8. THIRD-PARTY INTEGRATIONS ==============
elements.append(Paragraph("8. Third-Party Integrations", styles['Heading2Custom']))

integrations_data = [
    ["Service", "Status", "Purpose", "Configuration"],
    ["OpenAI (Emergent Key)", "Active", "Document OCR", "Uses Emergent LLM Key"],
    ["Microsoft Azure AD", "Ready", "SSO Login", "Requires AZURE_TENANT_ID, AZURE_CLIENT_ID"],
    ["SMTP Email", "Configurable", "Email notifications", "Configurable via UI"],
    ["Stripe", "Available", "Payment processing", "API key in environment"],
]

int_table = Table(integrations_data, colWidths=[1.5*inch, 0.8*inch, 1.5*inch, 2.2*inch])
int_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.02, 0.3, 0.23)),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 9),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
]))
elements.append(int_table)
elements.append(Spacer(1, 0.3*inch))

# ============== 9. SECURITY FEATURES ==============
elements.append(Paragraph("9. Security Features", styles['Heading2Custom']))

security_features = [
    "JWT-based authentication with configurable expiry",
    "Password hashing using bcrypt",
    "Role-based access control (RBAC) with 7 permission levels",
    "Microsoft Azure AD Single Sign-On support",
    "OTP-based password reset with rate limiting",
    "PAN number validation and uniqueness enforcement",
    "Entity separation rules (Client ≠ RP ≠ Employee)",
    "Comprehensive audit logging for all actions",
    "Email audit trail for compliance",
    "CORS configuration for API security",
    "Input validation using Pydantic models",
]

for feature in security_features:
    elements.append(Paragraph(f"• {feature}", styles['BodyCustom']))

elements.append(Spacer(1, 0.5*inch))
elements.append(Paragraph(
    "— End of Documentation —",
    ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.grey)
))

# Build PDF
doc.build(elements)
print("PDF generated successfully: /app/PRIVITY_System_Documentation.pdf")
