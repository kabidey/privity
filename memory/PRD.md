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

## Next Tasks
1. **(P0) Continue Backend Modularization** - Move remaining routes from server.py:
   - Move client routes to `/routers/clients.py`
   - Move stock routes to `/routers/stocks.py`
   - Move booking routes to `/routers/bookings.py`
   - Move reports routes to `/routers/reports.py`
   - Move analytics routes to `/routers/analytics.py`
2. **(P1) Two-factor authentication (TOTP)**
3. **(P2) Bulk booking close functionality**
4. **(P2) Mobile responsive improvements**

