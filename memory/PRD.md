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

### Latest Updates (Feb 06, 2026)

#### ✅ Server-Side Search Refactoring (Feb 06, 2026)
- Implemented server-side search for all major API endpoints to handle large datasets efficiently
- **Backend endpoints updated:**
  - `/api/bookings` - Search by booking number, client name/PAN, stock symbol, creator name
  - `/api/inventory` - Search by stock symbol, name, ISIN
  - `/api/users` - Search by name, email, PAN
  - `/api/stocks` - Search by symbol, name, ISIN, sector
  - `/api/purchases` - Search by vendor name, stock symbol, purchase number
- Added `skip` and `limit` pagination parameters to all search endpoints
- Files: `bookings.py`, `inventory.py`, `users.py`, `stocks.py`, `purchases.py`

#### ✅ WhatsApp Bulk Notification Automation (Feb 06, 2026)
- Created comprehensive WhatsApp automation service
- **New Files:**
  - `/app/backend/services/whatsapp_automation.py` - Core automation logic
  - `/app/backend/services/wati_service.py` - Wati.io API wrapper
- **Automation Features:**
  - Payment reminders for overdue bookings (configurable days)
  - Document upload reminders for pending clients
  - DP Ready notifications when shares are ready for transfer
  - Bulk broadcast to all clients/RPs/BPs
- **New API Endpoints:**
  - `GET/PUT /api/whatsapp/automation/config` - Configure automation settings
  - `POST /api/whatsapp/automation/payment-reminders` - Trigger payment reminders
  - `POST /api/whatsapp/automation/document-reminders` - Trigger document reminders
  - `POST /api/whatsapp/automation/dp-ready-notifications` - Trigger DP notifications
  - `POST /api/whatsapp/automation/bulk-broadcast` - Send bulk messages
  - `GET /api/whatsapp/automation/logs` - View automation logs
  - `GET /api/whatsapp/broadcasts` - View broadcast history

#### ✅ RBAC Endpoint Audit (Feb 06, 2026)
- Added permission checks to previously unprotected endpoints:
  - Group Chat: `chat.view`, `chat.send` permissions
  - Files: `files.view` permission for file info endpoint
- Updated `permission_service.py` with new permission categories:
  - `chat`: view, send
  - `files`: view, upload, delete
  - `notifications`: Added `whatsapp_config` permission
- Fixed bot protection to allow authenticated curl/script API calls

#### ✅ Search Functionality Across All Data Tables (Feb 06, 2026)
- Added client-side search bars to all major data tables for easier data navigation
- **Pages updated:**
  - `/app/frontend/src/pages/Bookings.js` - Search by booking ID, client name, PAN, stock symbol, creator
  - `/app/frontend/src/pages/Inventory.js` - Search by stock symbol, name, ISIN
  - `/app/frontend/src/pages/UserManagement.js` - Search by name, email, PAN, role
  - `/app/frontend/src/pages/Vendors.js` - Search by name, email, PAN, OTC UCC, phone
  - `/app/frontend/src/pages/Stocks.js` - Search by symbol, name, ISIN, sector
  - `/app/frontend/src/pages/Purchases.js` - Search by vendor name, stock symbol, purchase number
  - `/app/frontend/src/pages/Clients.js` - Search by name, PAN (already implemented)
- **Bug fixes:** Fixed JSX syntax errors in Vendors.js, Stocks.js, Purchases.js (missing closing `</div>` tags)
- All search inputs have proper `data-testid` attributes for testing

### Previous Updates (Feb 05, 2026)

#### ✅ Skip Cancelled Cheque Permission (Feb 05, 2026)
- New permission `clients.skip_cancelled_cheque` added
- Role Management: Can assign this permission to allow client creation without cancelled cheque
- Backend: `/app/backend/routers/clients.py` - Updated approval validation
- Frontend: `/app/frontend/src/pages/Clients.js` - Shows "Cancelled Cheque (Optional)" when permission enabled

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
