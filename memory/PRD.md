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
1. **PE Desk (Role 1)**: Full system access + User Management + Deletion rights
2. **PE Manager (Role 2)**: PE Desk without delete/DB restore rights + Vendor access (no delete)
3. **Zonal Manager (Role 3)**: Manage users, clients, stocks, bookings, reports
4. **Manager (Role 4)**: Manage own clients, bookings, view reports
5. **Employee (Role 5)**: Create bookings, view clients
6. **Viewer (Role 6)**: Read-only access
7. **Finance (Role 7)**: Employee rights + Full Finance page access (payments, refunds, RP payments)

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

## What's Been Implemented

### Latest Updates (Jan 28, 2026)

#### ✅ Company Logo Upload - COMPLETED (Jan 29, 2026)
**Implementation Details:**
- Added `/app/backend/routers/company_master.py` endpoints:
  - `POST /upload-logo` - Upload company logo (PNG, JPG, SVG, WEBP, max 5MB)
  - `DELETE /logo` - Delete company logo
- Updated CompanyMasterResponse model to include `logo_url` field
- Added logo preview section to Company Master frontend page:
  - 192x192 preview container with placeholder when no logo
  - Logo Guidelines section
  - Upload/Change Logo button
  - Remove Logo button (when logo exists)
  - "Logo uploaded successfully" badge
- Old logo automatically deleted when new one is uploaded
- Logo persists across page refreshes
- **Testing**: 11/11 backend + all frontend tests passed (iteration_35)

#### ✅ Contract Notes - Email Attachments & Auto-Generation - COMPLETED (Jan 29, 2026)
**Implementation Details:**
- Updated `/app/backend/services/email_service.py`:
  - `send_email()` function now accepts `attachments` parameter
  - Supports PDF and other file attachments via MIMEApplication
- Updated `/app/backend/routers/contract_notes.py`:
  - `POST /send-email/{note_id}` now reads PDF and attaches to email
- Updated `/app/backend/server.py` confirm-stock-transfer endpoint:
  - Auto-generates contract note when DP transfer is confirmed
  - Auto-sends email with PDF attachment to client
  - Response includes: `contract_note_generated`, `contract_note_number`, `contract_note_emailed`
- Email audit logging tracks attachment status
- **Testing**: 30/30 backend tests passed (iteration_34)

#### ✅ Contract Notes Generation - COMPLETED (Jan 29, 2026)
**Implementation Details:**
- Created `/app/backend/services/contract_note_service.py` for PDF generation
- Contract note PDF includes:
  - Company/Seller details from Company Master (Name, CIN, GST, PAN, Bank Account)
  - Buyer/Client details (Name, PAN, Address, Demat info)
  - Transaction details (Stock, ISIN, Quantity, Rate, Amount)
  - Financial summary with Stamp Duty calculation
  - Bank details for payment
  - Terms & Conditions and signatures section
- Created `/app/backend/routers/contract_notes.py` with endpoints:
  - `GET /contract-notes` - List with filters and pagination
  - `GET /contract-notes/{id}` - Single note details
  - `POST /contract-notes/generate/{booking_id}` - Generate after DP transfer
  - `GET /contract-notes/download/{id}` - Download PDF
  - `POST /contract-notes/preview/{booking_id}` - Preview without saving
  - `POST /contract-notes/send-email/{id}` - Email to client
  - `GET /contract-notes/by-booking/{booking_id}` - Check existence
- Created `/app/frontend/src/pages/ContractNotes.js` with stats, filters, table
- Contract Note number format: SMIFS/CN/YY-YY/XXXX
- **Testing**: 19/19 backend tests passed (iteration_33)

#### ✅ Company Master Settings - COMPLETED (Jan 29, 2026)
**Implementation Details:**
- Created `/app/backend/routers/company_master.py` with PE Desk only access control
- Endpoints:
  - `GET /company-master` - Get company settings
  - `PUT /company-master` - Update company settings
  - `POST /company-master/upload/{document_type}` - Upload documents
  - `DELETE /company-master/document/{document_type}` - Delete documents
- Fields: Company Name, Address, CIN, GST, PAN, CDSL DP ID, NSDL DP ID, TAN, Bank Details
- Document uploads: CML CDSL, CML NSDL, Cancelled Cheque, PAN Card
- Created `/app/frontend/src/pages/CompanyMaster.js` with form and document upload cards
- Updated Layout.js to show menu item only for PE Desk (role 1)
- **Testing**: 13/13 tests passed (iteration_32)

#### ✅ Email Audit Logging - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Updated `/app/backend/services/email_service.py` with `log_email()` function
- All emails (sent, failed, skipped) are now logged to `email_logs` collection
- Created `/app/backend/routers/email_logs.py` with endpoints:
  - `GET /email-logs` - List logs with filters (status, template, email, entity, date range)
  - `GET /email-logs/stats` - Statistics (sent/failed/skipped counts, by template, by entity)
  - `GET /email-logs/{log_id}` - Single log detail
  - `GET /email-logs/by-entity/{type}/{id}` - Logs by related entity
  - `DELETE /email-logs/cleanup` - Delete old logs (PE Desk only)
- Created `/app/frontend/src/pages/EmailLogs.js` with:
  - Stats cards (Sent, Failed, Skipped, Success Rate)
  - Filters (Status, Template, Email, Entity Type, Date Range)
  - Logs table with pagination
  - Analytics tab with templates/entity breakdowns
- Added `email_logs` database indexes for performance
- **Testing**: 13/13 backend tests passed (iteration_31)

#### ✅ Backend Refactoring - MODULAR ROUTERS MIGRATION - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Migrated remaining endpoints from monolithic `server.py` to modular router files
- Created new routers:
  - `/app/backend/routers/auth.py` - Auth with SSO, passwordless registration, change password
  - `/app/backend/routers/dashboard.py` - Dashboard stats and analytics
  - `/app/backend/routers/analytics.py` - Summary, stock performance, employee performance
  - `/app/backend/routers/reports.py` - P&L reports, Excel/PDF exports
  - `/app/backend/routers/inventory.py` - Inventory management
  - `/app/backend/routers/purchases.py` - Purchase orders with vendor/stock enrichment
  - `/app/backend/routers/audit_logs.py` - Audit log retrieval and statistics
- Updated `/app/backend/routers/__init__.py` to export all 17 routers
- All routers now included in server.py with /api prefix
- **Testing**: 24/24 backend tests passed (iteration_30)

#### ✅ RP Approval/Rejection Email Notifications - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Added two new email templates in `config.py`:
  - `rp_approval_notification`: Sent when RP application is approved
  - `rp_rejection_notification`: Sent when RP application is rejected (includes rejection reason)
- Modified `/app/backend/routers/referral_partners.py` to send emails on approval/rejection
- Email includes RP code, name, PAN number, and approval/rejection details

#### ✅ RP Bank Details Capture - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Added bank detail fields to `ReferralPartnerCreate` and `ReferralPartner` models
- Fields: `bank_name`, `bank_account_number`, `bank_ifsc_code`, `bank_branch`
- Updated backend router to store bank details during RP creation
- Updated frontend `ReferralPartners.js`:
  - Add dialog: Bank Details section with all fields
  - Edit dialog: Bank Details section with all fields
  - View dialog: Displays bank details (account number masked for security)
- Validation: Bank name required, IFSC format (11 chars), account number (9-18 digits)

#### ✅ Strict Client-RP Separation Rule - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- **STRICT RULE: A Client cannot be an RP and vice versa**
- Backend validation:
  - RP creation blocked if PAN/email matches existing Client (`/app/backend/routers/referral_partners.py`)
  - Client creation blocked if PAN/email matches existing RP (`/app/backend/routers/clients.py`)
  - Booking: Auto-zeros RP revenue share if client's PAN matches any RP (`/app/backend/routers/bookings.py`)
- Frontend UI:
  - Added conflict check API: `GET /api/bookings/check-client-rp-conflict/{client_id}`
  - When client is selected in booking form, system checks for RP conflict
  - If conflict found: Shows warning, disables RP selection, auto-clears RP fields
  - Booking notes auto-updated with "[AUTO: RP share zeroed - Client is also an RP]" flag

#### ✅ Employee-RP-Client Separation with PAN - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- **STRICT RULE: An Employee cannot be an RP or Client (and vice versa)**
- Added `pan_number` field to User model (required for registration)
- Backend validation:
  - Employee registration blocked if PAN matches existing RP or Client (`/app/backend/server.py`)
  - RP creation blocked if PAN/email matches existing Employee (`/app/backend/routers/referral_partners.py`)
- Frontend:
  - Added PAN Number field to registration form (`/app/frontend/src/pages/Login.js`)
  - Auto-uppercase, 10-character limit, required validation

#### ✅ Auto-Generated Password & Change Password - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Registration no longer requires password - system auto-generates a 12-char random password
- Password is sent to user's email with welcome message
- User must change password after first login (flag: `must_change_password`)
- `pedesk@smifs.com` is superadmin and doesn't need PAN for registration
- Added `POST /api/auth/change-password` endpoint
- Added Change Password dialog in sidebar (`/app/frontend/src/components/Layout.js`)

#### ✅ Microsoft Azure AD SSO Integration - COMPLETED (Jan 28, 2026)
**Implementation Details:**
- Added Microsoft Azure AD Single Sign-On (SSO) for all users
- SSO users default to Employee role (role=4), admins manually upgrade
- Created `/app/backend/services/azure_sso_service.py` for Azure AD token validation
- Backend endpoints:
  - `GET /api/auth/sso/config` - Returns SSO configuration for frontend
  - `POST /api/auth/sso/login` - Validates Azure AD token, creates/updates user
- Frontend:
  - MSAL (Microsoft Authentication Library) integration
  - "Sign in with Microsoft" button on login page (shows when SSO is configured)
  - Auto-creates user on first SSO login

**Azure AD Setup Required:**
1. Register app in Azure Portal (App registrations)
2. Set Redirect URI: `{frontend_url}`
3. Add API permissions: `openid`, `profile`, `email`
4. Configure `.env` with:
   - `AZURE_TENANT_ID` - Azure AD Tenant ID
   - `AZURE_CLIENT_ID` - Application (client) ID
   - `AZURE_CLIENT_SECRET` - Client secret (optional for SPA)
   - `AZURE_REDIRECT_URI` - Redirect URI

**Registration Flow:**
1. User enters: Name, PAN (not required for superadmin), Email (@smifs.com only)
2. System generates random password and sends email
3. User logs in with temporary password
4. User changes password via sidebar option

**Conflict Matrix:**
| Entity | Cannot be |
|--------|-----------|
| Employee | RP, Client |
| Client | RP, Employee |
| RP | Employee, Client |

**API Flow:**
- `PUT /api/referral-partners/{rp_id}/approve` with `{"approve": true}` → Sends approval email
- `PUT /api/referral-partners/{rp_id}/approve` with `{"approve": false, "rejection_reason": "..."}` → Sends rejection email

**Backend Regression Testing:**
- Verified all 32 backend API endpoints working after major server.py refactoring
- Test report: `/app/test_reports/iteration_29.json`

#### ✅ High RP Share Warning (>30%) - COMPLETED (Jan 28, 2026)
**Feature:**
- When an employee tries to assign more than 30% revenue share to an RP, a prominent warning is displayed
- Warning includes disciplinary action notice and email contact for converting RP to BP
- Styled with dazzling red/yellow gradient background and animation
- "Remove RP Selection" button allows quick correction

**Warning Text:**
> You have chosen an RP to share X% of the booking revenue, it will be verified by PE Desk if the client was sourced by the RP. If this booking is found to be dubious, disciplinary action will be initiated against you. If you still want to share more than 30% of the revenue, please connect with partnersdesk@smifs.com to initiate and convert RP to BP. If you have chosen by mistake, please immediately remove the selection.

#### ✅ Referral Partner (RP) Finance Integration - COMPLETED
**RP Payment Tracking in Finance Module**
- RP Payments automatically created when stock transfer is confirmed for bookings with RPs
- Payment amount calculated as: `profit * (rp_revenue_share_percent / 100)`
- Finance Dashboard shows RP Payments summary cards (Pending RP Payments, RP Payments Done)
- New "RP Payments" tab displays all RP payments with full details
- Update dialog allows marking payments as "Processing" or "Paid" with reference numbers

**30% Revenue Share Cap**
- Backend validation: Returns 400 error if revenue share > 30%
- Frontend validation: Input field caps at 30% max

**API Endpoints**:
- `GET /api/finance/rp-payments` - List all RP payments with status filter
- `GET /api/finance/rp-payments/summary` - Summary statistics
- `PUT /api/finance/rp-payments/{id}` - Update payment status/reference/notes

**RP Payment Schema**:
```javascript
rp_payments: {
  id: string,
  referral_partner_id: string,
  rp_code: string,
  rp_name: string,
  booking_id: string,
  booking_number: string,
  client_id: string,
  client_name: string,
  stock_id: string,
  stock_symbol: string,
  quantity: number,
  profit: number,
  revenue_share_percent: number,
  payment_amount: number,
  status: "pending" | "processing" | "paid",
  payment_date: string | null,
  payment_reference: string | null,
  notes: string | null,
  created_at: datetime
}
```

**Testing Results**: 100% pass rate (10/10 backend tests, 100% frontend verification)

#### ✅ Referral Partner (RP) System - COMPLETED
- Full CRUD system for managing Referral Partners
- Unique RP codes (RP-XXXX format)
- **All fields mandatory**: Name, Email, Phone (10 digits without +91), PAN (10 chars), Aadhar (12 digits), Address
- **All documents mandatory**: PAN Card, Aadhar Card, Cancelled Cheque (uploaded separately after creation)
- Validation: Duplicate PAN, Email, and Aadhar detection
- **RP Approval Workflow**:
  - Employee creates RP → status is "pending" (requires PE approval)
  - PE Desk/PE Manager creates RP → auto-approved
  - "Pending Approvals" tab for PE Level users to review and approve/reject RPs
  - Rejection requires a reason
  - Only approved RPs appear in the booking form dropdown
- Integration into booking form with warning about post-creation restrictions
- **Email notification to RP** when stock transfer is confirmed (rp_deal_notification template with deal details and revenue share)

#### ✅ Backend Refactoring - COMPLETED
- Created modular routers for `/app/backend/routers/`:
  - `bookings.py` - Booking CRUD with atomic inventory operations and RP fields
  - `clients.py` - Client/Vendor management
  - `finance.py` - Finance dashboard, refunds, and RP payments
  - `referral_partners.py` - RP CRUD with approval workflow
- Router registration prioritized over legacy endpoints
- **Removed duplicate endpoints from server.py** - Cleaned up ~400 lines of duplicate code for clients, bookings, and finance endpoints

#### ✅ High-Concurrency Booking Support - COMPLETED
- Atomic booking number generation using MongoDB counters with asyncio locks
- Atomic inventory reservation with locking mechanisms
- All concurrent booking tests passing

#### ✅ Finance Role (Role 7) - COMPLETED
- Employee-like permissions + full Finance page access
- Can view/manage refund requests, RP payments, view payments, export data

#### ✅ Refund Feature - COMPLETED
- Automatic refund request creation when voiding paid bookings
- Finance Dashboard Refunds tab with full management capabilities

## Pages & Routes
| Route | Page | Description |
|-------|------|-------------|
| /login | Login | Auth with register/login toggle |
| /forgot-password | ForgotPassword | Self-service password reset |
| / | Dashboard | Stats, charts, quick actions |
| /clients | Clients | Client management with portfolio links |
| /clients/:id/portfolio | ClientPortfolio | Detailed client holdings |
| /vendors | Vendors | Vendor management (PE Level + PE Manager with restrictions) |
| /stocks | Stocks | Stock management |
| /purchases | Purchases | Purchase recording |
| /inventory | Inventory | Stock levels tracking |
| /bookings | Bookings | Booking management with payment & loss tracking |
| /reports | Reports | P&L with filters and exports |
| /users | UserManagement | Role management (PE Level only) |
| /analytics | Analytics | Advanced analytics (PE Level only) |
| /email-templates | EmailTemplates | Email template editor (PE Level only) |
| /dp-transfer | DPTransferReport | Bookings ready for DP transfer |
| /finance | Finance | Finance dashboard with payments, refunds, RP payments |
| /referral-partners | ReferralPartners | Referral Partner management |

## Test Reports
- `/app/test_reports/iteration_27.json` - RP Approval Workflow (100% pass)
- `/app/test_reports/iteration_26.json` - RP Mandatory Fields & Email Notification (100% pass)
- `/app/test_reports/iteration_25.json` - RP Finance Integration (100% pass)
- `/app/test_reports/iteration_24.json` - Referral Partners feature
- `/app/test_reports/iteration_23.json` - Backend refactoring and concurrency
- `/app/test_reports/iteration_22.json` - Finance role and PE Manager vendor access
- `/app/test_reports/iteration_21.json` - Refund feature
- `/app/test_reports/iteration_29.json` - Backend regression after refactoring + RP email notifications
- `/app/test_reports/iteration_30.json` - Modular router migration verification (24/24 tests passed)
- `/app/test_reports/iteration_31.json` - Email audit logging feature (13/13 tests passed)
- `/app/test_reports/iteration_32.json` - Company Master Settings feature (13/13 tests passed)
- `/app/test_reports/iteration_33.json` - Contract Notes Generation feature (19/19 tests passed)
- `/app/test_reports/iteration_34.json` - Contract Notes Email Attachments & Auto-Generation (30/30 tests passed)

## Prioritized Backlog

### P0 (Critical)
- ✅ All resolved - no critical issues

### P1 (High Priority)
- ✅ RP Finance Integration - Complete
- ✅ 30% Revenue Share Cap - Complete
- ✅ Remove duplicate endpoints from server.py - Complete (verified via regression testing)
- ✅ Implement employee revenue share reduction by RP allocation - Complete
- ✅ RP Approval/Rejection Email Notifications - Complete (Jan 28, 2026)
- ✅ Capture RP bank details (IFSC, Account Number, Bank Name) for payouts - Complete (Jan 28, 2026)
- ✅ Backend Modular Router Migration - Complete (Jan 28, 2026, 24/24 tests passed)
- [ ] Two-factor authentication (TOTP)

### P2 (Medium Priority)
- [ ] Create dashboard view for Referral Partners to see their generated revenue
- ✅ Email sending history/log for auditing - Complete (Jan 28, 2026)
- [ ] Bulk booking closure feature
- [ ] Configurable thresholds for loss-booking auto-approval
- [ ] Role-specific dashboards
- [ ] Backend API documentation (Swagger/OpenAPI)

## Credentials for Testing
- **PE Desk (Super Admin)**: `pedesk@smifs.com` / `Kutta@123`
- **PE Manager**: `pemanager@test.com` / `Test@123`
- **Finance**: `finance@test.com` / `Test@123`
- **Employee**: `employee@test.com` / `Test@123`

## File Structure
```
/app/
├── backend/
│   ├── server.py              # Main app entry point (core setup + unique endpoints)
│   ├── config.py              # Configuration, roles, permissions
│   ├── database.py            # MongoDB connection
│   ├── models/__init__.py     # All Pydantic models
│   ├── routers/
│   │   ├── __init__.py        # Exports all 17 routers
│   │   ├── auth.py            # Authentication (SSO, passwordless, change-password)
│   │   ├── analytics.py       # Analytics endpoints
│   │   ├── audit_logs.py      # Audit log retrieval
│   │   ├── bookings.py        # Booking CRUD with RP fields
│   │   ├── clients.py         # Client/Vendor management
│   │   ├── dashboard.py       # Dashboard stats/analytics
│   │   ├── database_backup.py # DB backup/restore
│   │   ├── email_templates.py # Email template management
│   │   ├── finance.py         # Finance + RP payments + refunds
│   │   ├── inventory.py       # Inventory management
│   │   ├── notifications.py   # Real-time notifications
│   │   ├── purchases.py       # Purchase order management
│   │   ├── referral_partners.py # RP CRUD with approval workflow
│   │   ├── reports.py         # P&L reports and exports
│   │   ├── smtp_config.py     # SMTP configuration
│   │   ├── stocks.py          # Stock management
│   │   └── users.py           # User management
│   └── services/
│       ├── email_service.py
│       ├── notification_service.py
│       ├── ocr_service.py
│       ├── audit_service.py
│       ├── inventory_service.py
│       └── azure_sso_service.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Finance.js     # Finance dashboard with RP Payments tab
│       │   ├── ReferralPartners.js
│       │   ├── Bookings.js    # With RP selection in form
│       │   └── ...
│       └── components/
└── uploads/
```

## 3rd Party Integrations
- **OpenAI via `emergentintegrations`**: Used for OCR on document uploads. Uses the Emergent LLM Key.
- **`openpyxl`**: Used for generating `.xlsx` Excel files for export.
