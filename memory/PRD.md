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

## Pages & Routes
| Route | Page | Description |
|-------|------|-------------|
| /login | Login | Auth with register/login toggle |
| / | Dashboard | Stats, charts, quick actions |
| /clients | Clients | Client management with portfolio links |
| /clients/:id/portfolio | ClientPortfolio | Detailed client holdings |
| /vendors | Vendors | Vendor management |
| /stocks | Stocks | Stock management |
| /purchases | Purchases | Purchase recording |
| /inventory | Inventory | Stock levels tracking |
| /bookings | Bookings | Booking management |
| /reports | Reports | P&L with filters and exports |
| /users | UserManagement | Role management (admin only) |

## API Endpoints
- `/api/auth/*` - Authentication (register, login, me)
- `/api/users/*` - User management (list, update role)
- `/api/clients/*` - Client CRUD + documents + bulk upload + portfolio
- `/api/stocks/*` - Stock CRUD + bulk upload
- `/api/purchases/*` - Purchase tracking
- `/api/inventory/*` - Inventory management
- `/api/bookings/*` - Booking CRUD + bulk upload
- `/api/dashboard/*` - Stats and analytics
- `/api/reports/*` - P&L reports + exports

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
- [ ] Real-time notifications with WebSocket
- [ ] Password reset functionality
- [ ] Two-factor authentication
- [ ] Backend refactoring (split server.py into modules)

### P2 (Medium Priority)
- [ ] Bulk booking close functionality
- [ ] Advanced analytics dashboard
- [ ] Email templates customization
- [ ] Mobile app (React Native)

## Next Tasks
1. Real-time notifications with WebSocket
2. Password reset flow
3. Refactor backend into modular structure (models/, routers/, services/)
4. Create advanced analytics with more chart types
