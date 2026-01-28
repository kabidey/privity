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
- Integration into booking form with warning about post-creation restrictions
- **Email notification to RP** when stock transfer is confirmed (rp_deal_notification template with deal details and revenue share)

#### ✅ Backend Refactoring - COMPLETED
- Created modular routers for `/app/backend/routers/`:
  - `bookings.py` - Booking CRUD with atomic inventory operations and RP fields
  - `clients.py` - Client/Vendor management
  - `finance.py` - Finance dashboard, refunds, and RP payments
  - `referral_partners.py` - RP CRUD
- Router registration prioritized over legacy endpoints

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
- `/app/test_reports/iteration_26.json` - RP Mandatory Fields & Email Notification (100% pass)
- `/app/test_reports/iteration_25.json` - RP Finance Integration (100% pass)
- `/app/test_reports/iteration_24.json` - Referral Partners feature
- `/app/test_reports/iteration_23.json` - Backend refactoring and concurrency
- `/app/test_reports/iteration_22.json` - Finance role and PE Manager vendor access
- `/app/test_reports/iteration_21.json` - Refund feature

## Prioritized Backlog

### P0 (Critical)
- ✅ All resolved - no critical issues

### P1 (High Priority)
- ✅ RP Finance Integration - Complete
- ✅ 30% Revenue Share Cap - Complete
- [ ] Remove duplicate endpoints from server.py (cleanup task)
- [ ] Implement employee revenue share reduction by RP allocation
- [ ] Two-factor authentication (TOTP)

### P2 (Medium Priority)
- [ ] Create dashboard view for Referral Partners to see their generated revenue
- [ ] Email sending history/log for auditing
- [ ] Bulk booking closure feature
- [ ] Configurable thresholds for loss-booking auto-approval
- [ ] Role-specific dashboards

## Credentials for Testing
- **PE Desk (Super Admin)**: `pedesk@smifs.com` / `Kutta@123`
- **PE Manager**: `pemanager@test.com` / `Test@123`
- **Finance**: `finance@test.com` / `Test@123`
- **Employee**: `employee@test.com` / `Test@123`

## File Structure
```
/app/
├── backend/
│   ├── server.py              # Main app (contains legacy endpoints - cleanup needed)
│   ├── config.py              # Configuration, roles, permissions
│   ├── database.py            # MongoDB connection
│   ├── models/__init__.py     # All Pydantic models
│   ├── routers/
│   │   ├── bookings.py        # Booking CRUD with RP fields (priority)
│   │   ├── clients.py         # Client/Vendor management (priority)
│   │   ├── finance.py         # Finance + RP payments (priority)
│   │   ├── referral_partners.py # RP CRUD
│   │   ├── email_templates.py
│   │   ├── smtp_config.py
│   │   ├── stocks.py
│   │   ├── database_backup.py
│   │   └── users.py
│   └── services/
│       ├── email_service.py
│       ├── notification_service.py
│       ├── ocr_service.py
│       ├── audit_service.py
│       └── inventory_service.py
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
