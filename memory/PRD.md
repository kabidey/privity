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
2. **PE Manager (Role 2)**: PE Desk without delete/DB restore rights
3. **Zonal Manager (Role 3)**: Manage users, clients, stocks, bookings, reports
4. **Manager (Role 4)**: Manage own clients, bookings, view reports
5. **Employee (Role 5)**: Create bookings, view clients
6. **Viewer (Role 6)**: Read-only access

## Core Requirements (Static)
- User authentication (register/login)
- Client management (CRUD + bulk upload + portfolio view)
- Vendor management for stock suppliers
- Stock management (CRUD + bulk upload)
- Purchase tracking from vendors
- Inventory management with weighted average pricing
- Booking management with inventory validation
- P&L reporting with filtering and export

## What's Been Implemented

### Phase 1-11: Previous Development
See CHANGELOG.md for detailed history of phases 1-11.

### Latest Updates (Jan 28, 2026)

#### ✅ Refund Feature - COMPLETED
**Automatic Refund Request Creation on Voiding Paid Bookings**
- When a booking with payments is voided, the system automatically creates a refund request
- Refund request includes:
  - Booking details (number, stock, quantity)
  - Client information (name, email)
  - Refund amount (total paid amount)
  - Client bank details (extracted from primary bank account)
  - Void reason
  - Status tracking (pending → processing → completed/failed)

**Finance Dashboard - Refunds Tab**
- New "Refunds" tab on Finance page showing all refund requests
- Summary cards show pending and completed refund counts/amounts
- Table columns: Date, Booking #, Client, Stock, Amount, Bank Details, Status, Actions
- Edit button opens Update Refund Request dialog

**Refund Update Dialog**
- Shows refund amount, stock, void reason
- Displays client bank details (Bank, Account, IFSC, Holder)
- Status dropdown: Pending, Processing, Completed, Failed
- Transaction Reference Number input
- Notes textarea
- Update Refund button

**API Endpoints**:
- `GET /api/finance/refund-requests` - List all refund requests
- `GET /api/finance/refund-requests/{id}` - Get specific refund
- `PUT /api/finance/refund-requests/{id}` - Update refund status/notes/reference
- `PUT /api/finance/refund-requests/{id}/bank-details` - Update bank details

**Database Schema**:
```javascript
refund_requests: {
  id: string,
  booking_id: string,
  booking_number: string,
  client_id: string,
  client_name: string,
  client_email: string,
  stock_id: string,
  stock_symbol: string,
  quantity: number,
  refund_amount: number,
  bank_details: {
    bank_name: string,
    account_number: string,
    ifsc_code: string,
    account_holder_name: string,
    branch: string
  },
  void_reason: string,
  voided_by: string,
  voided_by_name: string,
  status: "pending" | "processing" | "completed" | "failed",
  reference_number: string,
  notes: string,
  created_at: datetime,
  updated_at: datetime,
  updated_by: string
}
```

**Testing Results**: 100% pass rate (13/13 backend tests, all frontend tests passed)

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
| /users | UserManagement | Role management (PE Level only) |
| /analytics | Analytics | Advanced analytics (PE Level only) |
| /email-templates | EmailTemplates | Email template editor (PE Level only) |
| /dp-transfer | DPTransferReport | Bookings ready for DP transfer |
| /finance | Finance | Finance dashboard with payments and refunds |

## Test Reports
- `/app/test_reports/iteration_21.json` - Refund feature testing (100% pass)

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
- [ ] Backend Monolith Refactoring - Extract routes from server.py (5187 lines) to modular routers
  - Next: Extract clients endpoints to `/app/backend/routers/clients.py`
  - Then: Extract bookings, purchases, reports endpoints
- [ ] Two-factor authentication (TOTP)

### P2 (Medium Priority)
- [ ] Email sending history/log for auditing
- [ ] Bulk booking closure feature
- [ ] Configurable thresholds for loss-booking auto-approval
- [ ] Role-specific dashboards

## Credentials for Testing
- **PE Desk (Super Admin)**: `pedesk@smifs.com` / `Kutta@123`
- **PE Manager**: `pemanager@test.com` / `Test@123`
- **Employee**: `employee@test.com` / `Test@123`

## File Structure
```
/app/
├── backend/
│   ├── server.py              # Main monolith (5187 lines - needs refactoring)
│   ├── config.py              # Configuration, roles, permissions
│   ├── database.py            # MongoDB connection
│   ├── models/__init__.py     # All Pydantic models
│   ├── routers/
│   │   ├── auth.py            # Authentication routes
│   │   ├── users.py           # User management (430 lines)
│   │   ├── stocks.py          # Stocks and inventory
│   │   ├── database_backup.py # Backup/restore
│   │   ├── email_templates.py # Email template CRUD
│   │   ├── smtp_config.py     # SMTP configuration
│   │   └── notifications.py   # Real-time notifications
│   └── services/
│       ├── email_service.py
│       ├── notification_service.py
│       ├── ocr_service.py
│       ├── audit_service.py
│       └── inventory_service.py
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Finance.js     # Finance dashboard with Refunds tab
│       │   └── ...
│       └── components/
└── uploads/
```
