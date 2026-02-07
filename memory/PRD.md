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

### Latest Updates (Feb 07, 2026)

#### ✅ Fix - Notification Dashboard Blank Screen (Feb 07, 2026)
- **Issue:** Clicking on Notification was causing a blank screen
- **Root Cause:** Incorrect destructuring in NotificationDashboard.js - `const { currentUser: user }` should be `const { user }`
- **Solution:** Fixed the useCurrentUser hook destructuring
- **Files Modified:** `/app/frontend/src/pages/NotificationDashboard.js`

#### ✅ Fix - Critical Linting & Import Errors (Feb 07, 2026)
- **Issues Fixed:**
  - `F821 Undefined name 'total_amount'` in bookings.py - Added missing calculation before notification
  - `F821 Undefined name 'check_permission'` in bookings.py & clients.py - Added missing imports
  - Import error for `DEFAULT_EMAIL_TEMPLATES` - Fixed imports in email_service.py and email_templates.py
- **Files Modified:** 
  - `/app/backend/routers/bookings.py`
  - `/app/backend/routers/clients.py`
  - `/app/backend/services/email_service.py`
  - `/app/backend/routers/email_templates.py`

#### ✅ Refactor - Login.js Split into Components (Feb 07, 2026)
- **Before:** 1036 lines in single Login.js file
- **After:** 535 lines in Login.js + reusable components
- **New Components Created:**
  - `/app/frontend/src/components/auth/constants.js` - PE quotes, floating keywords, themes
  - `/app/frontend/src/components/auth/FloatingIcons.jsx` - Animated background icons
  - `/app/frontend/src/components/auth/TypewriterQuote.jsx` - Quote typewriter effect
  - `/app/frontend/src/components/auth/LoginForm.jsx` - Employee login form
  - `/app/frontend/src/components/auth/RegistrationForm.jsx` - OTP registration form
  - `/app/frontend/src/components/auth/PartnerLogin.jsx` - Business partner OTP login
  - `/app/frontend/src/components/auth/OtpInput.jsx` - Reusable OTP input component
  - `/app/frontend/src/components/auth/index.js` - Export barrel file
- **Benefits:** Better maintainability, reusable components, clearer code structure

#### ✅ Enhancement - Centralized RBAC Service (Feb 07, 2026)
- **Added new helper functions to permission_service.py:**
  - `get_client_visibility_filter()` - MongoDB filter for client queries based on role
  - `get_booking_visibility_filter()` - MongoDB filter for booking queries based on role
  - `get_user_visibility_filter()` - MongoDB filter for user queries based on role
  - `can_view_all_clients()` - Check if user has full client visibility
  - `can_view_all_bookings()` - Check if user has full booking visibility
  - `can_view_all_users()` - Check if user has full user visibility
- **Purpose:** Prevent recurring RBAC bugs by centralizing permission logic

#### ✅ Investigation - Email Template Root Cause (Feb 07, 2026)
- **Investigation Summary:**
  - Email templates can be overridden via database (`email_templates` collection)
  - Possible entry points: Manual editing via PUT endpoint, data migration, direct DB access
  - Verification endpoint exists: `GET /api/email-templates/verify`
  - Reset endpoint exists: `POST /api/email-templates/sync-all`
- **Recommendation:** Admin should run `/api/email-templates/verify` to check for issues, then `/api/email-templates/sync-all` to reset all templates

#### ✅ Fix - Login Page Text Prominence (Feb 07, 2026)
- **Issue:** User reported that multiple text elements on the login page had poor contrast and were hard to read against the dark gradient background
- **Solution:** Updated all text elements to use fully opaque colors with increased font weights:
  - Changed semi-transparent colors (e.g., `text-white/60`, `text-white/80`, `text-white/90`) to fully opaque equivalents (`text-white`, `text-gray-200`, `text-gray-300`)
  - Added `font-medium` or `font-semibold` to labels and helper text for better visibility
  - Updated placeholders from `placeholder:text-white/60` to `placeholder:text-gray-400`
  - Enhanced floating icon labels with `drop-shadow-md` for better contrast
  - Updated warning boxes to use brighter amber tones (`text-amber-200`)
  - Updated footer text to use visible gray tones with proper font weights
- **Elements Fixed:**
  - Form labels (Email, Password, Full Name, Mobile Number, PAN Number)
  - Helper text ("Required for SMS/WhatsApp notifications", "Required for KYC verification")
  - Card description ("Access exclusive PE opportunities", "Start your private equity journey")
  - Tab buttons (Employee/Partner - inactive state)
  - Domain restriction warning
  - Floating icon keyword labels
  - Footer text (copyright, "Powered by Privity", "Vibe Coded by Somnath Dey")
  - Input placeholders
  - "Try Demo" button
  - "Forgot Password?" and "Don't have an account? Register" links
- **Files Modified:**
  - `/app/frontend/src/pages/Login.js` - Comprehensive text color and font-weight updates
- **Test Status:** Verified via screenshots - all text elements now clearly visible with high contrast

#### ✅ Feature - Browser Cache-Busting Solution (Feb 07, 2026)
- **Issue:** Users were not seeing new enhancements after deployment due to aggressive browser/service worker caching
- **Implementation:**
  - Updated service worker to use network-first strategy for JS/CSS bundles
  - Added `ALWAYS_NETWORK_PATTERNS` to force fresh fetches for React bundles and index.html
  - Added auto-reload when service worker detects update (SW_UPDATED message handler in App.js)
  - Added Cache-Control headers (`no-cache, no-store, must-revalidate`) to all API responses
  - Bumped service worker version to 6.3.0 to force cache invalidation
- **Files Modified:**
  - `/app/frontend/public/service-worker.js` - Network-first for critical assets
  - `/app/frontend/src/App.js` - Added SW update listener and auto-reload
  - `/app/backend/middleware/security.py` - Added Cache-Control headers to API responses
- **Test Status:** Verified - Cache-Control headers present in API responses

#### ✅ Feature - Data Quality Cleanup System (Feb 07, 2026)
- **Issue:** Database contained orphaned inventory records and items with missing landing prices
- **Implementation:**
  - Created `/app/backend/scripts/data_cleanup.py` - Comprehensive cleanup script
  - Added `GET /api/inventory/data-quality/report` endpoint - Shows data health metrics
  - Added `POST /api/inventory/data-quality/cleanup` endpoint - Runs cleanup with dry-run option
  - Cleanup operations:
    1. Delete orphaned inventory records (stock_symbol = "Unknown")
    2. Set missing landing_price from WAP or stock master data
    3. Validate and update inventory-stock references
- **Results:** Health score improved from 24.6% to 76.2%
  - 20 orphaned records deleted
  - 1 missing LP fixed (21 items already had WAP fallback working)
  - Inventory count cleaned from 25 to 5 valid records
- **Files Created:**
  - `/app/backend/scripts/data_cleanup.py` - Data cleanup module
  - `/app/backend/scripts/__init__.py` - Package init
- **Files Modified:**
  - `/app/backend/routers/inventory.py` - Added data quality endpoints
- **Test Status:** Verified via API - Data cleanup executed successfully

### Previous Updates (Feb 06-07, 2026)

#### ✅ Fix - Mobile Numbers Not Visible in User Management (Feb 07, 2026)
- **Issue:** Mobile numbers captured during user registration were not visible in the User Management page
- **Root Cause:** Frontend was using `user.mobile` but the API returns `user.mobile_number`
- **Solution:**
  - Updated frontend to use correct field name `mobile_number`
  - Updated `UserUpdate` model to include `mobile_number` and `pan_number` fields
  - Added validation for mobile number updates (10 digits, duplicate check)
- **Files Modified:**
  - `/app/frontend/src/pages/UserManagement.js` - Fixed field name from `mobile` to `mobile_number`
  - `/app/backend/routers/users.py` - Added `mobile_number` and `pan_number` to `UserUpdate` model and handler
- **Test Status:** Verified via screenshot - mobile numbers now display correctly for users who have them

#### ✅ Fix - Removed "Buying Price" from WhatsApp Template (Feb 07, 2026)
- **Issue:** User reported "Buying Price" was still showing in the Booking Confirmation WhatsApp template
- **Root Cause:** Database had cached old template content
- **Solution:**
  - Created `/api/whatsapp/templates/refresh-system` endpoint to force-update system templates
  - Added "Refresh System" button to the Templates UI
  - Executed refresh to update database with latest template content
- **Files Modified:**
  - `/app/backend/routers/whatsapp.py` - Added refresh-system endpoint
  - `/app/frontend/src/pages/WhatsAppNotifications.js` - Added Refresh System button
- **Test Status:** Verified via screenshot - Booking Confirmation template now shows only "Selling Price"

#### ✅ Feature - Comprehensive Content Protection System (Feb 06, 2026)
- **Request:** Implement security measures to prevent content copying and screen capture across the entire app
- **Implementation:**
  - **Text Selection Prevention:** Disabled text selection globally (except in form inputs for usability)
  - **Right-Click Blocking:** Context menu disabled to prevent copy/save options
  - **Keyboard Shortcut Blocking:** Blocked Ctrl+C, Ctrl+A, Ctrl+X, Ctrl+P, Ctrl+S, Ctrl+U, F12, PrintScreen
  - **Drag & Drop Prevention:** Disabled image and content dragging
  - **Tab Visibility Detection:** Content blurs (20px) when user switches tabs or loses window focus
  - **Developer Tools Detection:** Content blurs (25px) when DevTools is detected open
  - **User Watermark:** Subtle watermark overlay (3% opacity) showing user email and date across all pages
  - **Print Prevention:** Printing is blocked with CSS @media print rules
  - **Protection Overlay:** Shows lock icon with "Content Protected" message when tab is unfocused
- **Files Created/Modified:**
  - `/app/frontend/src/components/ContentProtection.js` - Main protection component with all security features
  - `/app/frontend/src/hooks/useContentProtection.js` - Lightweight hook for standalone pages (Login)
  - `/app/frontend/src/index.css` - Added protection CSS (blur, watermark, print block)
  - `/app/frontend/src/components/Layout.js` - Wrapped with ContentProtection component
  - `/app/frontend/src/pages/Login.js` - Added useContentProtection hook
- **Test Status:** Verified via screenshot - blur effect works on tab switch, protection overlay displays correctly

#### ✅ Feature - Advanced Login Page Enhancements (Feb 06, 2026)
- **Request:** Enhance the redesigned login page with more dynamic effects and mobile responsiveness
- **Implementation:**
  - **Mobile Responsiveness:** Floating icons hidden on screens smaller than `lg` breakpoint (1024px)
  - **Increased Icons:** Expanded from 20 to 30 floating icons with better distribution
  - **More Keywords:** Added 20 new keywords from quotes (LIQUIDITY, STABILITY, VOLATILITY, EQUITY, INVESTMENT, PORTFOLIO, THESIS, BUYOUT, IPO, EARNINGS, J-CURVE, CAP TABLE, DUE DILIG, EBITDA, MULTIPLE, BOLT-ON, ORGANIC, INORGANIC, BOARD, STEWARD)
  - **Quote Logic:** Sequential rolling through all 69 quotes with 15-minute no-repeat window
  - **Dynamic Refresh:** Random starting quote and icon positions on each page load
  - **Icon Size Variation:** Random scale (0.8x - 1.2x) for visual interest
  - **Nameplate Logo:** Metallic bolted effect with corner screws
- **Files Modified:**
  - `/app/frontend/src/pages/Login.js` - Enhanced floating icons, quote logic, mobile responsiveness
- **Test Status:** Verified via screenshot - desktop shows icons, mobile hides them, quotes rotate sequentially



#### ✅ Feature - Two-Way WhatsApp Communication (Feb 06, 2026)
- **Request:** Create a Wati webhook for two-way communication when customers reply
- **Implementation:**
  - **Enhanced Webhook** (`POST /api/whatsapp/webhook`):
    - Handles incoming messages, delivery status updates, and session status
    - Creates/updates conversation threads automatically
    - Links messages to clients by phone number lookup
    - Notifies PE Desk of new incoming messages
  - **Conversation Management Endpoints:**
    - `GET /api/whatsapp/conversations` - List all conversations with unread counts
    - `GET /api/whatsapp/conversations/{phone}` - Get full conversation thread
    - `POST /api/whatsapp/conversations/{phone}/reply` - Send reply (session message)
    - `POST /api/whatsapp/conversations/{phone}/send-template` - Send template (outside 24h window)
    - `DELETE /api/whatsapp/conversations/{phone}` - Delete conversation
    - `GET /api/whatsapp/webhook/info` - Get webhook URL and setup instructions
  - **Frontend Conversation Inbox:**
    - New "Conversations" tab in WhatsApp page with unread badge
    - Conversation list with client name, last message, timestamps
    - Full message thread view with inbound/outbound styling
    - Real-time reply input with send functionality
    - Webhook URL display with copy button for Wati setup
- **Webhook URL to configure in Wati:** `{your-domain}/api/whatsapp/webhook`
- **Files Modified:**
  - `/app/backend/routers/whatsapp.py` - Complete webhook rewrite + conversation endpoints
  - `/app/frontend/src/pages/WhatsAppNotifications.js` - Added Conversations tab with chat UI
- **Test Status:** Verified - webhook receives messages, conversations are threaded, replies work

#### ✅ Bug Fix - Wati WhatsApp Integration (Feb 06, 2026)
- **Bug:** Wati WhatsApp integration was not working - integration was disabled and credentials were missing
- **Root Cause:** 
  1. No Wati credentials were configured in the database (`system_config` collection)
  2. Template fetching had a bug - checking for `result` key instead of `success` key
- **Fix:**
  1. Configured Wati API credentials in the correct database (`test_database`)
  2. Fixed template fetching to correctly parse Wati API response
- **Credentials Configured:**
  - Endpoint: `https://live-mt-server.wati.io/302931`
  - Token: User-provided Bearer token
  - API Version: v1 (auto-detected)
- **Files Modified:**
  - `/app/backend/routers/whatsapp.py` - Fixed template parsing logic (lines 654-670)
- **Test Status:** Verified - connection test passes, 59 Wati templates fetched successfully

#### ✅ Feature - Atomic Client Creation with Documents (Feb 06, 2026)
- **Request:** Prevent creating clients without documents - enforce documents are uploaded to GridFS BEFORE client creation
- **Implementation:**
  - New endpoint `POST /clients-with-documents` that:
    1. Uploads mandatory documents (PAN Card, CML Copy) to GridFS FIRST
    2. Verifies documents are stored successfully
    3. Only then creates the client with document references
    4. If document upload fails, NO client is created
  - Frontend uses `FormData` to send client details + files in single request
  - OCR still runs during upload as before
- **Files Modified:**
  - `/app/backend/routers/clients.py` - New `create_client_with_documents` endpoint (lines 700-920)
  - `/app/frontend/src/pages/Clients.js` - Updated `handleSubmit` to use atomic endpoint (lines 634-705)
- **Test Status:** Verified via API and screenshot - client "Test Atomic Client ATMC78714X" created with 2 documents

#### ✅ Feature - Documents Tab Always Enabled for Client Editing (Feb 06, 2026)
- **Request:** Allow PE Desk to upload documents for existing clients that were created without docs
- **Implementation:**
  - Enabled Documents tab in Edit Client dialog (was previously disabled)
  - Added "Upload Documents" button in empty documents dialog for pending clients
  - Added `activeTabInDialog` state for programmatic tab navigation
- **Files Modified:**
  - `/app/frontend/src/pages/Clients.js` - Lines 46, 858, 1003, 1373-1377, 2225-2258

#### ✅ Feature - Production Domain URL Setting in Company Master (Feb 06, 2026)
- **Request:** Add UI setting to configure the production domain for email links (Accept/Deny buttons)
- **Implementation:**
  - Added "Email Link Settings" section in Company Master page
  - "Production Domain URL" field allows PE Desk to set the domain (e.g., `https://privity.yourdomain.com`)
  - Booking approval flow now reads from Company Master first, then falls back to env variables
  - Trailing slashes are automatically removed on save
- **Files Modified:**
  - `/app/backend/routers/company_master.py` - Added custom_domain to save and response
  - `/app/backend/routers/bookings.py` - Lines 633-647, reads custom_domain from Company Master
  - `/app/frontend/src/pages/CompanyMaster.js` - Lines 668-689, UI for Production Domain URL
- **Test Status:** Verified with testing agent (iteration_74)

#### ✅ Bug Fix - Booking Visibility for Mapped Clients (Feb 06, 2026)
- **Bug:** Employees could only see bookings they created, not bookings for clients mapped to them
- **Root Cause:** The booking query only filtered by `created_by`, not by client mapping
- **Fix:** Updated booking query to include `$or` clause: show bookings created by user/team OR for clients mapped to user/team
- **Result:** Employees now see all bookings for clients mapped to them, regardless of who created them
- **Files Modified:**
  - `/app/backend/routers/bookings.py` - Lines 910-937, added mapped client lookup to visibility query

#### ✅ Bug Fix - Payment Status Not Updating to "Paid" (Feb 06, 2026)
- **Bug:** After full payment and DP ready, payment status still showed "pending" instead of "paid"
- **Root Cause:** The payment recording function only set `payment_complete: true` but not `payment_status: "paid"`
- **Fix:** Updated payment recording to set `payment_status: "paid"` when complete, "partial" when partially paid
- **Result:** Payment status now correctly reflects the actual payment state
- **Files Modified:**
  - `/app/backend/routers/bookings.py` - Line 1880, added payment_status update

#### ✅ Bug Fix - Document Download from GridFS (Feb 06, 2026)
- **Bug:** PE level users couldn't download documents even though OCR was done and documents were in GridFS
- **Root Cause:** Document download function looked for `gridfs_id` but documents were stored with `file_id`
- **Fix:** Updated download function to check both `file_id` (new) and `gridfs_id` (legacy) fields
- **Result:** PE users can now download documents from GridFS
- **Files Modified:**
  - `/app/backend/routers/clients.py` - Lines 888-905, check file_id first, then gridfs_id

#### ✅ Email Template Fix - "Landing Price" to "Selling Price" (Feb 06, 2026)
- **Change:** Updated email templates to show "Selling Price" instead of "Landing Price"
- **Files Modified:**
  - `/app/backend/email_templates.py` - Updated booking_confirmation_request template
  - `/app/backend/routers/bookings.py` - Pass selling_price variable to template
  - `/app/backend/services/email_service.py` - Updated hardcoded templates

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
