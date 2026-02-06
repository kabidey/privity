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

#### ✅ Robust OCR & Re-run Feature (Feb 06, 2026)
- **Enhanced OCR Prompts:** Improved extraction prompts for PAN Card, Cancelled Cheque, and CML documents
  - PAN Card: Better field location guidance, format validation (5 letters + 4 digits + 1 letter)
  - Cancelled Cheque: Detailed layout reference for IFSC, Account Number, Bank Name extraction
  - CML Copy: Comprehensive CDSL/NSDL format detection with DP ID, Client ID, bank details extraction
- **New API Endpoint:** `POST /api/clients/{client_id}/rerun-ocr`
  - Supports `doc_types` query param to re-run specific documents
  - Supports `update_client=true` to update client data with new OCR results
  - Returns comparison of old vs new OCR results with confidence scores
  - Creates audit log entry for each re-run action
- **Frontend Integration:**
  - "Re-run OCR" button in Documents dialog header (PE Level only)
  - "Re-run & Update Data" button to both re-run and update client data
  - Individual document re-run button (RefreshCw icon) for each document
  - OCR Confidence percentage display for each document
  - OCR Re-run Results section showing confidence transition after re-run
  - OCR re-run timestamp display when document has been re-run
- **Files Modified:**
  - `/app/backend/services/ocr_service.py` - Enhanced prompts and post-processing
  - `/app/backend/routers/clients.py` - Added rerun_client_ocr endpoint (lines 985-1170)
  - `/app/frontend/src/pages/Clients.js` - Added handleRerunOcr and updated Documents dialog

#### ✅ Rainbow Theme System (Feb 06, 2026)
- Implemented 10 colorful themes beyond basic white/dark mode
- **Light Themes (7):**
  - ☀️ Light - Clean white theme (default)
  - 🌅 Sunset - Warm orange glow
  - 🌲 Forest - Natural greens
  - 💜 Lavender - Soft purple tones
  - 🌸 Rose - Gentle pink hues
  - 🪸 Coral - Vibrant coral reef
  - 🍃 Mint - Fresh mint green
- **Dark Themes (3):**
  - 🌙 Dark - Easy on the eyes
  - 🌊 Ocean - Deep blue vibes
  - 🌌 Midnight - Deep purple night
- **Features:**
  - Theme selector dropdown in navigation bar
  - Theme persists via localStorage
  - CSS variables for consistent styling
  - All text readable with proper contrast
- **Files Modified:**
  - `/app/frontend/src/context/ThemeContext.js` - Updated with THEMES config
  - `/app/frontend/src/components/ThemeSelector.js` - New component
  - `/app/frontend/src/index.css` - Added CSS variables for all themes
  - `/app/frontend/src/components/Layout.js` - Integrated ThemeSelector

#### ✅ Complete WhatsApp Automation Feature (Feb 06, 2026)
- **Backend API Endpoints:**
  - `GET/PUT /api/whatsapp/automation/config` - Configure automation settings
  - `POST /api/whatsapp/automation/payment-reminders` - Trigger payment reminders
  - `POST /api/whatsapp/automation/document-reminders` - Trigger document reminders
  - `POST /api/whatsapp/automation/dp-ready-notifications` - Trigger DP ready notifications
  - `POST /api/whatsapp/automation/run-all` - Run all enabled automations
  - `POST /api/whatsapp/automation/bulk-broadcast` - Send bulk broadcast
  - `GET /api/whatsapp/automation/logs` - View automation logs
  - `GET /api/whatsapp/broadcasts` - View broadcast history

- **Frontend UI (WhatsApp Notifications > Automation tab):**
  - Automation Settings card with toggles for Payment Reminders, Document Upload Reminders, DP Ready Notifications
  - Configurable "Days overdue" for payment reminders
  - "Save Settings" button to persist configuration
  - "Run All Enabled Automations" button for manual triggering
  - Bulk Broadcast section with "New Broadcast" dialog
  - Automation Logs table showing run history
  - Broadcasts table showing sent broadcasts

- **Scheduled Automation:**
  - WhatsApp automations run automatically at 10:00 AM IST daily via `scheduler_service.py`
  - Job: `whatsapp_automations` using APScheduler CronTrigger

- **Files Created/Modified:**
  - `/app/backend/services/whatsapp_automation.py` - Core automation logic
  - `/app/backend/services/wati_service.py` - Wati.io API wrapper
  - `/app/backend/services/scheduler_service.py` - Added WhatsApp automation job
  - `/app/backend/routers/whatsapp.py` - Added automation endpoints
  - `/app/frontend/src/pages/WhatsAppNotifications.js` - Added Automation tab

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
