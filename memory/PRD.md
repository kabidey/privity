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

#### ✅ Critical Bug Fix - Booking Dropdown Empty for Non-PE Users (Feb 06, 2026)
- **Bug:** Approved clients not appearing in booking dropdown for Employee users
- **Root Cause:** `Promise.all` in `fetchData()` included `/api/referral-partners-approved` endpoint which returns 403 for non-PE users. When this failed, the entire Promise.all failed and `setClients()` was never called.
- **Fix:** Separated the referral-partners-approved API call into its own try-catch block, ensuring client data loads even if RP endpoint fails.
- **Result:** Employees can now see and select approved clients in the booking dropdown, and create bookings.
- **Files Modified:**
  - `/app/frontend/src/pages/Bookings.js` - Lines 115-140, separated RP fetch from main Promise.all
- **Test Status:** Verified with testing agent (iteration_72)

#### ✅ Rounding Fix - All Prices/Payments to 2 Decimal Places (Feb 06, 2026)
- **Bug:** Payment amounts showing extreme decimals (e.g., ₹21374.999999999996)
- **Fix:** Applied `round(..., 2)` to all financial calculations:
  - Purchases: total_amount, total_paid, remaining, price_per_share
  - Bookings: total_amount, total_paid, profit_loss
- **Frontend:** Updated `toLocaleString()` calls to use `minimumFractionDigits: 2, maximumFractionDigits: 2`
- **Files Modified:**
  - `/app/backend/routers/purchases.py` - Rounded total_amount, total_paid, price_per_share, remaining
  - `/app/backend/routers/bookings.py` - Rounded total_amount, total_paid, profit_loss
  - `/app/frontend/src/pages/Purchases.js` - Updated getRemainingAmount, payment displays
  - `/app/frontend/src/pages/Inventory.js` - Fixed price display in LP history chart

#### ✅ Bug Fixes - Client Booking & OCR Permissions (Feb 06, 2026)
- **Bug 1: Approved client not available for booking**
  - Fixed `can_book` logic to return `true` if user created the client OR is mapped to it
  - Updated booking restriction to allow users to book for clients they created
  - Users no longer need to be explicitly mapped to book for their own clients
- **Bug 2: Re-run OCR permission not available for PE Level**
  - Added `clients.rerun_ocr` permission explicitly to PE Manager role
  - Added `rerun_ocr` to `ALL_PERMISSIONS['clients']` list for wildcard matching
  - Re-run OCR buttons now visible for all PE Level users
- **Bug 3: Documents not visible in documents dialog**
  - Confirmed documents display correctly with: filename, upload date, OCR confidence
  - Download button works for document retrieval
  - Issue was due to test document being a .txt file (not actual image for OCR)
- **Files Modified:**
  - `/app/backend/routers/clients.py` - Updated can_book logic (lines 325-340)
  - `/app/backend/routers/bookings.py` - Updated booking restriction (lines 254-263)
  - `/app/backend/services/permission_service.py` - Added clients.rerun_ocr permission

#### ✅ Real-time Notification Dashboard (Feb 06, 2026)
- **New Page:** `/notifications` - Dedicated notification dashboard
- **Stats Cards:**
  - Unread Notifications count
  - Messages Sent (7 days)
  - Delivery Rate percentage
  - Failed Messages count
- **Features:**
  - Real-time notification list with read/unread status
  - Search and filter notifications
  - Mark individual or all notifications as read
  - Delete notifications
  - Tabs for PE Level: Incoming Messages, Delivery Status, Automation Logs
  - Auto-refresh every 30 seconds
- **Files Created/Modified:**
  - `/app/frontend/src/pages/NotificationDashboard.js` - New page
  - `/app/frontend/src/components/Layout.js` - Added sidebar menu item
  - `/app/frontend/src/App.js` - Added route

#### ✅ Wati.io Webhook Integration (Feb 06, 2026)
- **Dual API Support (v1 and v3):**
  - v1 API: Standard endpoints for templates and messages
  - v3 API: Extended API with bulk messaging support
  - Auto-detection of best API version during connection
  - Fallback mechanism: tries v1 first, falls back to v3 if needed
- **API Configuration:**
  - API Endpoint URL input
  - API Token (Bearer) input
  - API Version selector (v1/v3)
  - Connection test with detailed error messages
- **New Endpoints:**
  - `POST /api/whatsapp/webhook` - Receives delivery status webhooks from Wati.io
  - `POST /api/whatsapp/test-connection` - Test API connection
  - `GET /api/whatsapp/delivery-stats` - Returns message delivery statistics
  - `GET /api/whatsapp/webhook/events` - View webhook event history
  - `GET /api/whatsapp/incoming-messages` - View incoming WhatsApp messages
  - `PUT /api/whatsapp/incoming-messages/{id}/read` - Mark message as read
- **Features:**
  - Tracks message delivery status (sent, delivered, read, failed)
  - Stores incoming messages for review
  - Notifies PE Desk of failed messages
  - Shows webhook URL for configuration in Wati dashboard
- **Files Modified:**
  - `/app/backend/routers/whatsapp.py` - Complete WatiService rewrite with dual API support
  - `/app/backend/middleware/bot_protection.py` - Whitelisted webhook path
  - `/app/frontend/src/pages/WhatsAppNotifications.js` - Added API version selector

#### ✅ Export Functionality Enhancements (Feb 06, 2026)
- **Clients Page Export:**
  - Export Excel button (downloads .xlsx)
  - Export CSV button (downloads .csv)
  - Includes: OTC UCC, Name, PAN, DP ID, Email, Phone, Address, Bank details, Status
- **Inventory Page Export:**
  - Export Excel button
  - Export CSV button
  - Includes: Stock Symbol, Name, Available/Reserved Qty, WAP, Total Value
- **New Endpoints:**
  - `GET /api/clients-export?format=xlsx|csv`
  - `GET /api/inventory/export?format=xlsx|csv`
- **Files Modified:**
  - `/app/backend/routers/clients.py` - Added export endpoint
  - `/app/backend/routers/inventory.py` - Added export endpoint
  - `/app/frontend/src/pages/Clients.js` - Added export buttons
  - `/app/frontend/src/pages/Inventory.js` - Added export buttons

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

#### ✅ Client Approval Flow UX Improvements (Feb 06, 2026)
- **Issue:** Clients created by employees show as "pending" and cannot be used for bookings until PE Desk approves
- **Solution:** Improved UX to make this clearer while keeping the approval workflow:
  - **Booking Form Client Dropdown:**
    - Shows "(Approved clients only)" label
    - Approved clients are selectable
    - Pending clients shown in separate "Pending PE Desk Approval" section (disabled, orange indicator)
    - Message shown when all clients are pending approval
  - **Clients Page Status Badge:**
    - Enhanced "Pending Approval" badge with orange background
    - Shows "Cannot book until approved" sub-text
  - **Cache Invalidation:**
    - Client mapping now immediately clears localStorage and sessionStorage cache
    - Client approval immediately clears cache
    - Bookings page clears stale cache before fetching clients
  - **Improved Toast Messages:**
    - "Client mapped to employee - changes are live!"
    - "Client approved - now available for bookings!"
- **Files Modified:**
  - `/app/frontend/src/pages/Bookings.js` - Client dropdown with pending section, cache clearing
  - `/app/frontend/src/pages/Clients.js` - handleMappingSubmit, handleApprove cache clearing, status badge

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
