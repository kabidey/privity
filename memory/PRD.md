# Privity - Share Booking System PRD

## Original Problem Statement
Build a Share Booking System for managing client share bookings, inventory tracking, and P&L reports with role-based access control.

## Architecture
- **Frontend**: React.js with Tailwind CSS, Shadcn UI components, Recharts
- **Backend**: FastAPI (Python) with async MongoDB
- **Database**: MongoDB
- **Authentication**: JWT-based with role-based permissions
- **Theme**: Light/Dark mode with ThemeContext

## User Personas
1. **PE Desk (Role 1)**: Full system access + User Management
2. **Zonal Manager (Role 2)**: Manage users, clients, stocks, bookings, reports
3. **Manager (Role 3)**: Manage own clients, bookings, view reports
4. **Employee (Role 4)**: Create bookings, view clients
5. **Viewer (Role 5)**: Read-only access

## Core Requirements (Static)
- User authentication (register/login)
- Client management (CRUD + bulk upload + portfolio view)
- Vendor management for stock suppliers
- Stock management (CRUD + bulk upload)
- Purchase tracking from vendors
- Inventory management with weighted average pricing
- Booking management with inventory validation
- P&L reporting with filtering and export
- User management for admin roles

## What's Been Implemented

### Phase 1 - Initial (Restored from GitHub)
- ✅ User authentication with JWT
- ✅ Role-based access control (5 roles)
- ✅ Client management with document uploads
- ✅ Stock management
- ✅ Booking management
- ✅ Dashboard with stats
- ✅ P&L Reports with Excel/PDF export
- ✅ Email notifications (MS Exchange)

### Phase 2 - Enhancements (Jan 24, 2026)
- ✅ **Vendors Page** - Dedicated vendor management UI
- ✅ **Purchases Page** - Record stock purchases with stats
- ✅ **Inventory Page** - Stock levels with progress indicators
- ✅ **Enhanced Dashboard** - Recharts integration for P&L trend and top stocks
- ✅ **Reports Filters** - Date range, client, stock filtering

### Phase 3 - Advanced Features (Jan 24, 2026)
- ✅ **User Management Page** - Role assignment for admins (roles 1-2 only)
- ✅ **Dark Mode Toggle** - ThemeContext with localStorage persistence
- ✅ **Client Portfolio Page** - Detailed client holdings with PieChart
- ✅ **Portfolio Button** - Quick access from Clients table
- ✅ **Updated Navigation** - 9-item sidebar (Users visible for admins)

### Phase 4 - Client Management Enhancement (Jan 24, 2026)
- ✅ **Document Upload** - Upload PAN Card, CML Copy, Cancelled Cheque (JPG/PDF)
- ✅ **AI-Powered OCR** - GPT-4o vision extracts info from documents automatically
- ✅ **OTC UCC Code** - Unique client identifier (format: OTC{YYYYMMDD}{UUID8})
- ✅ **Employee Mapping** - Clients mapped to employees who created them
- ✅ **Admin Mapping Controls** - Admins can re-map/unmap clients to different employees
- ✅ **OCR Data Viewer** - Click document icons to view extracted OCR data

### Phase 5 - Advanced Permissions & Fields (Jan 24, 2026)
- ✅ **Extended Client Fields** - Address, Pin Code, Mobile, Email
- ✅ **Multiple Bank Accounts** - Clients can have multiple bank accounts
- ✅ **OCR Bank Auto-Add** - Different bank accounts from CML vs Cheque are auto-added
- ✅ **Client Approval Workflow** - Employee-created clients need Manager/PE Desk approval
- ✅ **Employee Restrictions**:
  - Cannot access Vendors page
  - Cannot view purchase history
  - Can only see their own clients
  - Cannot edit buying price (uses weighted average)
- ✅ **Vendor System** - Same document/OCR system applies to vendors
- ✅ **Role-Based Visibility** - Client of one employee not visible to another

### Phase 6 - Audit Trail & Approvals (Jan 24, 2026)
- ✅ **Audit Trail Logging** - All actions logged with user, timestamp, details
- ✅ **Domain Restriction** - Only @smifs.com employees can register
- ✅ **Auto Employee Role** - New registrations get Employee role by default
- ✅ **Email Notifications** - Detailed booking emails to clients with CC to creator
- ✅ **Booking Approval Workflow** - PE Desk must approve bookings before inventory adjustment
- ✅ **Pending Bookings View** - PE Desk can see and approve/reject pending bookings
- ✅ **Audit Log API** - Admin-only endpoints to view audit history

### Phase 7 - Stock Management & Corporate Actions (Jan 24, 2026)
- ✅ **Enhanced Stock Fields** - Symbol (Short Code), ISIN Number, Sector, Product, Face Value
- ✅ **PE Desk Only Stock Management** - Only PE Desk can add/edit/delete stocks
- ✅ **Corporate Actions Panel** - Separate section for Stock Splits and Bonus Shares
- ✅ **Stock Split** - Record ratio (e.g., 1:2), new face value, record date
- ✅ **Bonus Shares** - Record ratio (e.g., 1:1), record date
- ✅ **Price Adjustment** - Auto-adjust buy prices on record date:
  - Split: new_price = old_price × (ratio_from/ratio_to)
  - Bonus: new_price = old_price × (ratio_from/(ratio_from+ratio_to))
- ✅ **Record Date Validation** - Corporate actions can only be applied on their record date
- ✅ **Audit Logging** - All corporate actions logged for compliance

### Phase 8 - Real-time Notifications & Password Reset (Jan 24, 2026)
- ✅ **Real-time Notifications via WebSocket** - Instant updates for approvals/rejections
  - Client pending approval → Notifies Managers (roles 1, 2, 3)
  - Client approved/rejected → Notifies creator
  - Booking pending approval → Notifies PE Desk (role 1)
  - Booking approved/rejected → Notifies creator
- ✅ **Notification Bell Component** - Bell icon with unread count badge
- ✅ **Notification Popover** - Click to see notification history
- ✅ **Mark as Read** - Individual and bulk mark as read
- ✅ **Notification Persistence** - Stored in MongoDB for history
- ✅ **Password Reset with Email OTP** - Self-service password reset
  - Request OTP via email
  - 6-digit OTP with 10-minute expiry
  - Rate limiting (max 3 attempts)
  - Secure password update
- ✅ **Forgot Password Page** - Clean 3-step UI (email → OTP → success)
- ✅ **Backend Modular Structure Prepared** - Files created for future refactoring:
  - `/app/backend/config.py` - Configuration constants
  - `/app/backend/database.py` - MongoDB connection
  - `/app/backend/models/__init__.py` - Pydantic models
  - `/app/backend/utils/auth.py` - Authentication helpers
  - `/app/backend/utils/email.py` - Email utilities
  - `/app/backend/utils/notifications.py` - WebSocket manager
  - `/app/backend/routers/` - Prepared for route separation

### Phase 9 - Backend Modularization & Advanced Features (Jan 24, 2026)
- ✅ **Backend Modular Structure Created**:
  - `/app/backend/config.py` - Configuration, roles, permissions, email templates
  - `/app/backend/database.py` - MongoDB connection
  - `/app/backend/models/__init__.py` - All Pydantic models
  - `/app/backend/services/email_service.py` - Email with template support
  - `/app/backend/services/analytics_service.py` - Analytics calculations
  - `/app/backend/routers/` - Prepared for route separation
- ✅ **Advanced Analytics Dashboard (PE Desk Only)**:
  - Summary cards: Revenue, Profit, Bookings, Clients, Avg Booking, Margin
  - Daily Trend area chart
  - Sector Distribution pie chart
  - Top Performing Stocks bar chart
  - Top Employees performance bar chart
  - Detailed tables with rankings
  - Time range selector (7/30/90/365 days)
- ✅ **Email Template Customization (PE Desk Only)**:
  - 5 default templates: Welcome, Approved, Booking Created, Booking Approved, Password OTP
  - Edit subject and HTML body
  - Variable placeholders with preview
  - Active/Inactive toggle
  - Reset to default functionality
- ✅ **New Routes**: `/analytics`, `/email-templates`
- ✅ **New API Endpoints**:
  - `/api/analytics/summary`, `/api/analytics/stock-performance`
  - `/api/analytics/employee-performance`, `/api/analytics/daily-trend`
  - `/api/analytics/sector-distribution`
  - `/api/email-templates` (GET, PUT, POST reset, POST preview)

### Phase 10 - Payment Tracking & DP Transfer (Jan 24, 2026)
- ✅ **Payment Tranche Recording**:
  - Up to 4 payment tranches per approved booking
  - Each tranche captures: amount (INR), date, recorded_by, notes
  - Payment amount validation (cannot exceed remaining balance)
  - Auto-calculate total_paid and remaining balance
- ✅ **Payment Status Tracking**:
  - Status progression: `pending` → `partial` → `completed`
  - Visual progress bar showing payment percentage
  - "Paid" badge for completed payments
- ✅ **DP Transfer Ready Flag**:
  - Automatically set `dp_transfer_ready=true` when payment completed
  - "DP Ready" badge displayed in Bookings UI
  - `payment_completed_at` timestamp recorded
- ✅ **DP Transfer Report Page** (PE Desk & Zonal Manager only):
  - Summary cards: Ready for Transfer count, Total Value, Unique Clients, Latest Completion
  - Transfer records table with: Client Name, PAN, DP ID, Stock, Qty, Amount, Payment Date, Status
  - Export functionality: CSV and Excel formats
- ✅ **Role-Based Access**:
  - Only PE Desk (role 1) and Zonal Manager (role 2) can record payments
  - Only PE Desk and Zonal Manager can access DP Transfer Report
  - Payment button hidden for pending/fully-paid/no-selling-price bookings
- ✅ **New Routes**: `/dp-transfer`
- ✅ **New API Endpoints**:
  - `POST /api/bookings/{booking_id}/payments` - Record payment tranche
  - `GET /api/bookings/{booking_id}/payments` - Get payment details
  - `DELETE /api/bookings/{booking_id}/payments/{tranche_number}` - Delete payment (PE Desk only)
  - `GET /api/dp-transfer-report` - Get fully paid bookings ready for transfer
  - `GET /api/dp-transfer-report/export` - Export report as CSV/Excel

### Phase 11 - Loss Booking Approval Workflow (Jan 24, 2026)
- ✅ **Loss Booking Detection**:
  - Automatically detect when selling_price < buying_price (weighted avg)
  - Set `is_loss_booking=true` and `loss_approval_status=pending` for such bookings
  - Loss bookings require separate PE Desk approval before proceeding
- ✅ **Loss Approval Workflow**:
  - Dedicated approval endpoint: `PUT /api/bookings/{id}/approve-loss`
  - Separate from regular booking approval (can require both)
  - Only PE Desk (role 1) can approve/reject loss bookings
  - Audit logging for loss approval/rejection
  - Real-time notifications to booking creator
- ✅ **Pending Loss Bookings API**:
  - `GET /api/bookings/pending-loss-approval` - Returns all loss bookings pending approval
  - Enriched with client/stock details and calculated profit/loss
- ✅ **Enhanced Bookings UI**:
  - New "Loss Approval" tab showing pending loss bookings count
  - Loss booking rows highlighted with red background
  - "Loss Pending" / "Loss Approved" / "Loss Rejected" badges
  - Yellow TrendingDown icon buttons for loss approval actions
  - New columns: Buy Price, Sell Price, P&L
  - P&L column color-coded: green for profit, red for loss
- ✅ **Model Updates**:
  - `is_loss_booking: bool` - Flag for loss bookings
  - `loss_approval_status: str` - pending/approved/rejected/not_required
  - `loss_approved_by: str` - User who approved/rejected
  - `loss_approved_at: str` - Timestamp of approval/rejection

## Pages & Routes
| Route | Page | Description |
|-------|------|-------------|
| /login | Login | Auth with register/login toggle |
| /forgot-password | ForgotPassword | Self-service password reset |
| / | Dashboard | Stats, charts, quick actions |
| /clients | Clients | Client management with portfolio links |
| /clients/:id/portfolio | ClientPortfolio | Detailed client holdings |
| /vendors | Vendors | Vendor management (PE Desk only) |
| /stocks | Stocks | Stock management |
| /purchases | Purchases | Purchase recording |
| /inventory | Inventory | Stock levels tracking |
| /bookings | Bookings | Booking management with payment & loss tracking |
| /reports | Reports | P&L with filters and exports |
| /users | UserManagement | Role management (admin only) |
| /analytics | Analytics | Advanced analytics (PE Desk only) |
| /email-templates | EmailTemplates | Email template editor (PE Desk only) |
| /dp-transfer | DPTransferReport | Bookings ready for DP transfer (PE Desk & Zonal Manager) |

## API Endpoints
- `/api/auth/*` - Authentication (register, login, me, forgot-password, reset-password)
- `/api/users/*` - User management (list, update role)
- `/api/clients/*` - Client CRUD + documents + bulk upload + portfolio
- `/api/stocks/*` - Stock CRUD + bulk upload
- `/api/purchases/*` - Purchase tracking
- `/api/inventory/*` - Inventory management
- `/api/bookings/*` - Booking CRUD + bulk upload + approval + payment tracking + loss approval
- `/api/bookings/{id}/payments` - Payment tranche management
- `/api/bookings/{id}/approve-loss` - Loss booking approval
- `/api/bookings/pending-loss-approval` - Get pending loss bookings
- `/api/dp-transfer-report` - DP transfer report + export
- `/api/dashboard/*` - Stats and analytics
- `/api/reports/*` - P&L reports + exports
- `/api/notifications/*` - Notifications (list, unread-count, mark-read)
- `/api/ws/notifications` - WebSocket for real-time notifications
- `/api/analytics/*` - Advanced analytics endpoints
- `/api/email-templates/*` - Email template management

## Test Results (Latest)
- Backend: 100% pass rate (9/9 tests for bug fixes)
- Frontend: 100% pass rate
- Overall: 100% success

### Bug Fixes (Jan 24, 2026)
- ✅ **Client Form Validation** - Required fields (Name, PAN, DP ID) enforced on frontend and backend
- ✅ **Document Upload** - Fixed permission to allow employees to upload docs to their own clients
- ✅ **OCR Integration** - Fixed ImageContent usage in emergentintegrations library for GPT-4o vision
- ✅ **PDF OCR Support** - Added pdf2image conversion to process PDF documents (CML, PAN, Cheques)
- ✅ **Full DP ID Extraction** - OCR now extracts and combines DP ID + Client ID (e.g., IN301629-10242225)
- ✅ **Mobile Number Cleaning** - Removes ISD codes (+91) and keeps only 10-digit numbers
- ✅ **Vendor Access Restriction** - Vendors tab now visible only to PE Desk (Role 1)

## Tech Stack
- React 18 with React Router v6
- FastAPI with Motor (async MongoDB)
- Tailwind CSS + Shadcn UI
- Recharts for analytics
- JWT authentication
- ReportLab (PDF) + OpenPyXL (Excel)
- ThemeContext for dark mode

## Prioritized Backlog

### P0 (Critical)
- ✅ All resolved - no critical issues

### P1 (High Priority)
- ✅ Real-time notifications with WebSocket - DONE
- ✅ Password reset functionality - DONE
- ✅ Backend modular structure - DONE
- ✅ Advanced Analytics Dashboard (PE Desk) - DONE
- ✅ Email Template Customization - DONE
- ✅ Payment Tracking & DP Transfer Report - DONE
- [ ] Two-factor authentication (TOTP)

### P2 (Medium Priority)
- [ ] Bulk booking close functionality
- [ ] Mobile app (React Native)
- [IN PROGRESS] Complete migration of server.py routes to separate router files
- [ ] Mobile responsive improvements

### Phase 12 - Client Confirmation Workflow Enhancement (Jan 24, 2026)
- ✅ **Delayed Client Confirmation Email**: Client confirmation emails are now ONLY sent after PE Desk approval
  - Normal bookings: Email sent after PE Desk approval
  - Loss bookings: Email sent only after BOTH PE Desk approval AND Loss approval
- ✅ **Enhanced BookingConfirm Page**: 
  - Now handles `pending_approval` and `pending_loss_approval` statuses
  - Shows appropriate messages when booking is not yet ready for client confirmation
  - Fixed incorrect message after acceptance (was showing "pending PE Desk approval" when already approved)
- ✅ **Testing**: All 15+ test cases passed for the delayed confirmation workflow

### Phase 13 - Backend Modularization (Jan 24, 2026)
- ✅ **Modular Structure Created**:
  - `/app/backend/config.py` - Centralized configuration (171 lines)
  - `/app/backend/database.py` - Database connection (17 lines)
  - `/app/backend/models/__init__.py` - All Pydantic models (375 lines)
  - `/app/backend/utils/auth.py` - Authentication utilities (79 lines)
  - `/app/backend/services/email_service.py` - Email functions (284 lines)
  - `/app/backend/services/notification_service.py` - WebSocket & notifications (92 lines)
  - `/app/backend/services/ocr_service.py` - OCR processing (163 lines)
  - `/app/backend/services/audit_service.py` - Audit logging (43 lines)
  - `/app/backend/services/inventory_service.py` - Inventory calculations (76 lines)
  - `/app/backend/routers/auth.py` - Auth routes (213 lines)
  - `/app/backend/routers/users.py` - User management routes (35 lines)
  - `/app/backend/routers/notifications.py` - Notification routes (91 lines)
- ✅ **Server.py Refactored**: Reduced from 4343 to 3648 lines (~16% reduction)
- ✅ **Backend Imports Updated**: server.py now imports from modular structure
- 🔄 **Remaining Work**: Move client, stock, booking, report, analytics routes to separate files

### Bug Fix - Client Documents Display (Jan 24, 2026)
- ✅ **Documents Column Added**: Clients table now shows document count with folder icon
- ✅ **Documents Dialog**: Click to view all uploaded documents (PAN Card, CML Copy, Cancelled Cheque)
- ✅ **Download Feature**: PE Desk can download client documents directly from the dialog
- ✅ **OCR Data View**: View extracted OCR data from the documents dialog

### Feature - Client Management Enhancements (Jan 24, 2026)
- ✅ **PE Desk Only Edit/Delete**: Only PE Desk (role=1) can modify or delete clients
  - Backend returns 403 for non-PE Desk users
  - Frontend hides Edit/Delete buttons for non-PE Desk users
- ✅ **DP Type Field**: New dropdown with options "DP With SMIFS" and "DP Outside"
  - Default value: "outside"
  - Displayed in new DP TYPE column with colored badge
- ✅ **Trading UCC Field**: Conditionally required when DP Type is "SMIFS"
  - Backend validates and returns 400 error if missing
  - Frontend shows field only when SMIFS is selected
  - Trading UCC displayed in parentheses next to SMIFS badge
- ✅ **Real-time Search**: Search bar filters clients by Name or PAN number
  - Client-side filtering for instant results
  - Works on both "All Clients" and "Pending Approval" tabs

### Feature - Booking Form Enhancements (Jan 24, 2026)
- ✅ **Prominent Average Price Display**: Bright blue gradient box shows:
  - Current Average Price (large, bold text)
  - Available Stock quantity
  - Displayed immediately when stock is selected
- ✅ **Weighted Average Info**: Blue text below Landing Price field shows "Will use: ₹X (weighted average)"
- ✅ **Low Inventory Warning**: Red warning box when quantity exceeds available stock:
  - Shows requested quantity vs available stock
  - Warns that "Landing price might change based on new purchases"
  - Input field gets red border
  - Employee can still create booking (not blocked)

### Feature - Client/Vendor Clone (Jan 24, 2026)
- ✅ **Clone Vendor as Client**: PE Desk can clone a vendor to create a new client with same details
  - Blue copy icon in Vendors table Actions column
  - Confirmation dialog before cloning
  - Creates new client entry with new OTC UCC
  - Documents are not cloned (client must upload separately)
- ✅ **Clone Client as Vendor**: PE Desk can clone a client to create a new vendor with same details
  - Blue copy icon in Clients table Actions column (PE Desk only)
  - Confirmation dialog before cloning
  - Creates new vendor entry with new OTC UCC
- ✅ **Validation**: 
  - Cannot clone if already exists with same PAN in target type
  - Only PE Desk (role=1) can perform cloning
  - Audit log entry created for each clone operation

### Feature - Vendor Mandatory Document Upload (Jan 24, 2026)
- ✅ **Tabbed Form Interface**: Vendor form now has two tabs:
  - "Vendor Details" - Basic vendor information
  - "Documents *" - Mandatory document uploads (with red asterisk)
- ✅ **Mandatory Documents for New Vendors**:
  - PAN Card (with OCR auto-fill for name, PAN number)
  - CML Copy (with OCR auto-fill for DP ID, name, email, phone)
  - Cancelled Cheque (with OCR auto-fill for bank details)
- ✅ **Validation**: Cannot create vendor without all three documents
  - Toast error shows missing documents: "Please upload: PAN Card, CML Copy, Cancelled Cheque"
- ✅ **Documents Tab for Existing Vendors**:
  - View and download uploaded documents
  - View OCR extracted data
  - Add additional documents when editing
- ✅ **DOCS Column in Vendors Table**: Shows document count with folder icon for viewing

### Feature - Client Mandatory Documents & Booking Enhancements (Jan 24, 2026)
- ✅ **Client Mandatory Document Upload**: 
  - Same as vendors - all three documents required (PAN Card, CML Copy, Cancelled Cheque)
  - Yellow warning banner: "All documents are mandatory"
  - Validation prevents client creation without documents
  - Document labels now show asterisk (*) for new clients
- ✅ **Booking Page - Client Search**:
  - Real-time search input "Search client by name..." above client dropdown
  - Filters approved clients as you type
  - Shows "No clients found matching..." when no results
- ✅ **Booking Page - Created By Column**:
  - New "CREATED BY" column in bookings table
  - Shows the name of user who created each booking
  - Helps PE Desk identify booking sources (Employee vs Admin)

### Feature - Booking Type with Insider Trading Policy (Jan 24, 2026)
- ✅ **Booking Type Selection**: New "Booking For" field with radio buttons (Client/Team/Own)
  - Client (default): Regular booking for a client
  - Team: Booking for team/company
  - Own: Personal booking - triggers Insider Trading Policy warning
- ✅ **Insider Trading Policy Warning Dialog**: When "Own" is selected:
  - Shows compliance warning about regulatory requirements
  - Provides email link to pe@smifs.com for requesting requisite forms
  - Explains upload facility for completed forms
  - "Cancel" resets to Client type
  - "I Acknowledge & Continue" allows booking with acknowledgment indicator
- ✅ **Acknowledgment Indicator**: Green indicator shows after user acknowledges policy
- ✅ **Insider Form Upload**: 
  - POST `/api/bookings/{id}/insider-form` - Upload completed compliance form
  - GET `/api/bookings/{id}/insider-form` - Download uploaded form (PE Desk only)
  - Only allowed for "Own" bookings
- ✅ **Model Updates**: 
  - `booking_type`: "client", "team", or "own"
  - `insider_form_uploaded`: Boolean flag
  - `insider_form_path`: Path to uploaded form

### Feature - Inventory Blocking System (Jan 24, 2026)
- ✅ **Inventory Blocking on Approval**: When PE Desk approves a booking AND client confirms, stock is BLOCKED (not immediately subtracted)
- ✅ **Transfer Completes Sale**: When marked as "Stock Transferred" via DP Transfer, blocked quantity is permanently sold
- ✅ **Void/Delete Releases Inventory**: When booking is voided or deleted, blocked stock returns to available
- ✅ **Cannot Void/Delete Transferred**: Once stock is transferred, booking cannot be voided or deleted
- ✅ **Weighted Average Unaffected**: Blocked stock doesn't affect weighted average price calculation
- ✅ **Frontend Updates**:
  - Inventory page shows "Blocked Qty" column (orange)
  - Bookings page has "Void" button (Ban icon) for PE Desk
  - Booking form shows blocked quantity in stock info
- ✅ **Model Updates**: Added `is_voided`, `voided_at`, `voided_by`, `void_reason`, `stock_transferred`, `stock_transferred_at`, `stock_transferred_by` fields

**Inventory Logic**:
- `blocked_quantity` = Approved bookings with client confirmation, not voided, not transferred
- `available_quantity` = Total purchased - Transferred - Blocked
- `weighted_avg_price` = Total purchased value / Total purchased quantity

## Next Tasks
1. **(P1) Refactor Email Templates Usage** - ✅ COMPLETED - All hardcoded emails now use template system
2. 🟡 **(P1) Two-factor authentication (TOTP)**
3. **(P2) Bulk booking close functionality**
4. ✅ **(P2) Backend Modularization** - IN PROGRESS - Created modular routers, more to migrate
5. ✅ **(P2) Mobile responsive improvements** - COMPLETED

### Mobile Responsiveness (Jan 25, 2026) - ✅ COMPLETED
**Layout Improvements:**
- Fixed mobile header (PRIVITY logo, notifications, theme toggle, hamburger menu)
- Mobile sidebar navigation with all menu items
- Responsive padding across all pages (p-4 md:p-6 lg:p-8)

**Page-Specific Updates:**
- Dashboard: Responsive stat cards (2-col mobile, 6-col desktop)
- Clients: Horizontally scrollable table, hidden columns on mobile
- Bookings: Responsive buttons, compressed export labels
- Stocks: Responsive header and buttons
- User Management: Responsive layout and table
- Database Backup: 2-col stats grid on mobile

**CSS Additions:**
- `.table-responsive` class for horizontal scroll
- `.hide-mobile` utility class
- Responsive typography scaling

### Client/Vendor Wizard with Multiple Emails (Jan 28, 2026) - ✅ COMPLETED
**Client Creation Wizard (3-Step Process):**
- Step 1: Document Upload (CML, PAN Card, Cancelled Cheque) with OCR processing
- Step 2: Review & Edit Details (auto-populated from OCR)
- Step 3: Bank Accounts & Submit
- Progress indicator shows current step

**Multiple Email Support:**
- Primary Email (from CML) - extracted via OCR
- Secondary Email - PE Desk can add
- Tertiary Email - PE Desk can add
- All three emails receive notifications

**OCR Field Locking for Employees:**
- Fields extracted from documents show 🔒 icon
- Employees cannot edit OCR-populated fields (name, PAN, DP ID, email, mobile)
- PE Desk can edit all fields

**Email Service Enhancement:**
- `send_templated_email()` now accepts `additional_emails` parameter
- All client emails receive booking notifications
- `get_client_emails()` helper returns [primary, secondary, tertiary]

**Vendor Form Updated:**
- Same three email fields (Primary, Secondary, Tertiary)
- Consistent with client email structure

### User Management & Database Backup (Jan 25, 2026) - ✅ COMPLETED
**User Management Features (PE Desk Only):**
- Create new users with email, password, name, and role
- Delete users (except super admin pedesk@smifs.com)
- Reset user passwords
- Update user roles via dropdown
- View all system users with status

**Database Backup & Restore Features (PE Desk Only):**
- View database statistics (total records, collections, backup count)
- View collection-level record counts
- Create named backups with optional description
- View backup history with size, record counts, creator
- Delete old backups (auto-retains last 10)
- Restore database from backup (preserves super admin)

**PE Desk Delete Permissions Verified:**
- DELETE /api/clients/{id} - Delete clients
- DELETE /api/stocks/{id} - Delete stocks
- DELETE /api/bookings/{id} - Delete bookings (if not transferred)
- DELETE /api/purchases/{id} - Delete purchases
- DELETE /api/users/{id} - Delete users (except super admin)
- DELETE /api/database/backups/{id} - Delete backups

### Backend Modularization (Jan 24, 2026)
**Completed Modular Routers:**
- `/app/backend/routers/email_templates.py` - Email template CRUD operations
- `/app/backend/routers/smtp_config.py` - SMTP server configuration
- `/app/backend/routers/stocks.py` - Stocks, inventory, and corporate actions
- `/app/backend/routers/users.py` - User management (create, delete, reset password, update role)
- `/app/backend/routers/database_backup.py` - Database backup and restore operations

**Existing Routers:**
- `/app/backend/routers/auth.py` - Authentication
- `/app/backend/routers/notifications.py` - Real-time notifications

**Remaining in server.py (for future modularization):**
- Clients endpoints
- Vendors endpoints  
- Purchases endpoints
- Bookings endpoints
- Reports endpoints
- DP Transfer endpoints

## Completed Features (Jan 25, 2026)

### Email Templates System (13 Templates)
All system emails are now customizable via the Email Templates page. PE Desk can edit any template:

1. **Welcome Email (Client)** - Sent when client account is created
2. **Client Approved** - Sent when client is approved by PE Desk
3. **Booking Created (Pending Approval)** - Sent when booking is created, awaiting approval
4. **Booking Confirmation Request** - Sent after PE Desk approval, asking client to accept/deny
5. **Booking Pending Loss Review** - Sent for loss bookings awaiting additional approval
6. **Loss Booking Confirmation Request** - Sent after loss booking is fully approved
7. **Booking Status Updated** - Sent when booking status changes
8. **Client Payment Complete** - Sent when full payment is received
9. **Stock Transfer Completed** - Sent when stock is transferred to client's Demat
10. **Purchase Order Created (Vendor)** - Sent to vendor when purchase is created
11. **Vendor Payment Received** - Sent to vendor when payment is recorded
12. **Password Reset OTP** - Sent for password reset requests
13. **User Account Created** - Sent when staff account is created

Each template supports:
- Variable substitution (e.g., `{{client_name}}`, `{{booking_number}}`)
- Subject customization
- HTML body customization
- Enable/disable toggle
- Reset to default option

### Vendor Payment Tracking with Email Notification
- Added payment recording for vendor purchases on Purchases page
- "Pay" button opens dialog to record payment with amount, date, and notes
- Payment status displayed as badges: Pending (outline), Partial (yellow), Paid (green)
- When payment is recorded, vendor receives email notification with:
  - Stock details (symbol, name)
  - Purchase information (quantity, purchase date, total amount)
  - Payment details (this payment amount, total paid, remaining balance, status)

### DP Transfer Confirmation with Client Email
- Added "Transfer" button on DP Transfer Report page
- Confirmation dialog shows booking details (Client, DP ID, Stock, ISIN, Quantity, Amount)
- Optional notes field for transfer remarks
- When transfer is confirmed, client receives email notification with:
  - Booking reference number
  - Stock details (symbol, name, ISIN)
  - Quantity transferred
  - Client's DP ID
  - Transfer date

### API Endpoints Added
- `POST /api/purchases/{purchase_id}/payments` - Record vendor payment
- `GET /api/purchases/{purchase_id}/payments` - Get payment history
- `PUT /api/bookings/{booking_id}/confirm-transfer` - Confirm stock transfer

## Backend Refactoring Status (Jan 25, 2026)
**Progress Made:**
- Created modular architecture files under `/app/backend/`:
  - `config.py` - Configuration constants
  - `database.py` - MongoDB connection
  - `models/__init__.py` - All Pydantic models
  - `services/` - Email, notification, audit, OCR services
  - `utils/auth.py` - Authentication utilities
  - `routers/` - Auth, users, notifications routers working
  - `routers_refactor_templates/` - Templates for remaining routers

**Remaining Work:**
- Migrate routes from server.py to router files (clients, stocks, bookings, reports, purchases)
- Update server.py to import from new routers
- Test all endpoints after migration
- Remove duplicate code from server.py

**Risk Assessment:**
- Backend refactoring is a HIGH-RISK operation
- Should be done incrementally with thorough testing
- Recommend completing one router at a time with full regression testing

### Bug Fix - Booking Selling Price Validation (Jan 28, 2026) - ✅ COMPLETED
**Issue:** Booking creation API accepted bookings without a selling price, leading to incomplete data.

**Fix Applied:**
- Added backend validation in `/app/backend/server.py` (lines 1704-1709)
- Validates that `selling_price` is not null, not zero, and not negative
- Returns 400 error: "Selling price is required and must be greater than 0"

**Test Coverage:**
- 7 backend test cases (all passed):
  - No selling_price → 400 error
  - selling_price=0 → 400 error
  - selling_price=-100 → 400 error
  - selling_price=null → 400 error
  - selling_price=150 → 200 (booking created)
  - selling_price=0.01 → 200 (small positive accepted)
  - selling_price=999999.99 → 200 (large value accepted)
- Frontend validation shows toast: "Selling price is required"

**Test Files Created:**
- `/app/backend/tests/test_booking_selling_price_validation.py`

### Database Backup Enhancements (Jan 28, 2026) - ✅ COMPLETED
**New Features:**
1. **Clear Database** (PE Desk only)
   - DELETE `/api/database/clear` - Clears all collections except users
   - UI requires typing "CLEAR DATABASE" to confirm
   - Preserves super admin account (pedesk@smifs.com)
   - Audit log entry created for tracking

2. **Download Backup as ZIP**
   - GET `/api/database/backups/{id}/download`
   - Returns ZIP file with metadata.json and collections/*.json
   - Download button added to backup list table

3. **Upload & Restore from ZIP**
   - POST `/api/database/restore-from-file`
   - Accepts ZIP file upload via multipart/form-data
   - Validates ZIP structure (requires metadata.json)
   - Restores all collections from uploaded backup
   - Upload Restore button opens dialog with file picker

**UI Changes:**
- Added "Upload Restore" button in header
- Added "Clear DB" button (red, destructive) in header
- Added download icon button in backup list Actions column
- New Clear Database confirmation dialog with typed confirmation
- New Upload Restore dialog with file input

**Test Coverage:** 13 backend tests + UI tests (100% pass rate)

### PE Manager Role Addition (Jan 28, 2026) - ✅ COMPLETED
**New Role: PE Manager (Role ID: 2)**
- Created a new role between PE Desk (1) and Zonal Manager (3)
- PE Manager has almost all PE Desk permissions EXCEPT:
  - **All deletion rights** (stocks, clients, bookings, purchases, inventory, users, backups)
  - **Database clear** operation
  - **Database restore** operation

**Role Hierarchy Updated:**
1. PE Desk (Full Access - Super Admin)
2. PE Manager (PE Desk without delete/restore)
3. Zonal Manager
4. Manager
5. Employee
6. Viewer

**Backend Changes:**
- Added `is_pe_level()` and `is_pe_desk_only()` helper functions in `/app/backend/config.py`
- Updated 50+ endpoints across `server.py`, `users.py`, `database_backup.py` to use these helpers
- PE Manager can now: view analytics, manage users (not delete), manage stocks (not delete), manage bookings (not delete), view/create backups (not restore), manage email templates

**Frontend Changes:**
- Updated ROLES constant in `UserManagement.js` to include PE Manager
- Updated `Layout.js` menu visibility for PE Manager
- Updated `Analytics.js`, `EmailTemplates.js`, `Clients.js` for PE Level access

**Test Coverage:**
- PE Manager can: view users, view analytics, create backups, manage stocks
- PE Manager CANNOT: delete stocks, clear database, restore database, delete users

### User Hierarchy & Team Management (Jan 28, 2026) - ✅ COMPLETED
**Feature:** Employee-Manager mapping system with hierarchical structure

**Hierarchy:**
- PE Desk / PE Manager → Can map all users
- Zonal Manager → Can view their Managers and those Managers' Employees
- Manager → Can view their Employees
- Employee → Can only see their own data

**Mapping Rules:**
- Employee (role 5) → can be assigned to Manager (role 4)
- Manager (role 4) → can be assigned to Zonal Manager (role 3)
- Zonal Manager cannot be assigned (top of hierarchy below PE)
- PE roles cannot be assigned

**Backend Endpoints Added (`/app/backend/routers/users.py`):**
- `GET /api/users/hierarchy` - Get users with their hierarchy info
- `PUT /api/users/{id}/assign-manager` - Assign a user to a manager
- `GET /api/users/{id}/subordinates` - Get all subordinates for a user
- `GET /api/users/managers-list` - Get available managers for dropdown

**Frontend Changes (`/app/frontend/src/pages/UserManagement.js`):**
- Added "Team Hierarchy" tab showing visual org chart
- Added "Reports To" column in user list
- Added link icon for quick manager assignment
- Shows unassigned managers and employees with assign buttons

