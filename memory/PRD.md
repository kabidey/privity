# Privity - Share Booking System PRD

## Original Problem Statement
Build a Share Booking System for managing client share bookings, inventory tracking, and P&L reports with role-based access control.

## Architecture
- **Frontend**: React.js with Tailwind CSS, Shadcn UI components, Recharts
- **Backend**: FastAPI (Python) with async MongoDB (modular router architecture)
- **Database**: MongoDB
- **Authentication**: JWT-based with role-based permissions
- **Theme**: Light/Dark mode with ThemeContext, iOS-style design

## User Personas
1. **PE Desk (Role 1)**: Full system access + User Management + Deletion rights
2. **PE Manager (Role 2)**: PE Desk without delete/DB restore rights + Vendor access (no delete)
3. **Zonal Manager (Role 3)**: Manage users, clients, stocks, bookings, reports
4. **Manager (Role 4)**: Manage own clients, bookings, view reports
5. **Employee (Role 5)**: Create bookings, view clients
6. **Viewer (Role 6)**: Read-only access
7. **Finance (Role 7)**: Employee rights + Full Finance page access (payments, refunds, RP payments)
8. **Business Partner (Role 8)**: External partners with OTP login, can create bookings, view own dashboard
9. **Partners Desk (Role 9)**: Employee rights + BP management (no delete rights)

## Core Requirements (Static)
- User authentication (register/login)
- Client management (CRUD + bulk upload + portfolio view)
- Vendor management for stock suppliers
- Stock management (CRUD + bulk upload)
- Purchase tracking from vendors
- Inventory management with weighted average pricing
- Booking management with inventory validation
- P&L reporting with filtering and export
- Referral Partner management and commission tracking
- Business Partner management and revenue sharing

## What's Been Implemented

### Latest Updates (Feb 05, 2026)

#### ✅ WhatsApp Wati.io Integration (Feb 05, 2026)
- Replaced QR-based WhatsApp system with official Wati.io API
- Backend: `/app/backend/routers/whatsapp.py` - Complete rewrite
- Frontend: `/app/frontend/src/pages/WhatsAppNotifications.js` - Wati.io config UI
- Features: Send messages, template messages, bulk send, message history, stats

#### ✅ RP Bank Details Unmasked (Feb 05, 2026)
- `/app/frontend/src/pages/ReferralPartners.js` line 1077
- Shows full account number for PE Desk/Manager (`isPELevel` users)

#### ✅ Payment Proof Upload Fixed (Feb 05, 2026)
- Created `/app/backend/routers/payments.py` with `/payments/upload-proof` endpoint
- Fixed "View Proof" links in Bookings.js and Purchases.js with proper URL construction

#### ✅ Client Document Icon Fix (Feb 05, 2026)
- `/app/frontend/src/pages/Clients.js`
- Added cache clearing and delay before fetchClients() after document upload

#### ✅ send_email() is_html Fix (Feb 05, 2026)
- `/app/backend/services/captcha_service.py`
- Removed invalid `is_html=True` parameter from all send_email() calls

## Prioritized Backlog

### P0 - Critical
- None currently

### P1 - High Priority
- RBAC Endpoint Audit Phase 4 continuation
- Integration testing for document upload flow

### P2 - Medium Priority
- WhatsApp bulk notification automation
- Idea history & versioning
- Collaboration features

### P3 - Low Priority
- Export functionality enhancements
- WhatsApp template customization
- Mobile app integration

## Technical Notes

### API Endpoints
- Backend: Port 8001 (internal), accessed via /api prefix
- Frontend: Port 3000
- MongoDB: Via MONGO_URL environment variable

### Key Files
- `/app/backend/server.py` - Main FastAPI application
- `/app/frontend/src/App.js` - React router configuration
- `/app/backend/services/permission_service.py` - RBAC permissions
- `/app/backend/routers/` - API route handlers
