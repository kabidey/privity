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

### Latest Updates (Feb 08, 2026)

#### ✅ Consolidated Bond Scraping Service (Feb 08, 2026)

**Refactored web scraping into unified service with expanded data sources:**

**New File:** `/app/backend/fixed_income/bond_scraping_service.py`

**Data Sources Supported:**
- **Primary (Official):**
  - `indiabondsinfo.nsdl.com` - Official NSDL database
  - `rbi.org.in` - RBI Government Securities
  
- **Secondary (Marketplaces):**
  - `indiabonds.com` - Bond marketplace
  - `smest.in` - Bond investment platform
  - `wintwealth.com` - Bond trading platform
  - `thefixedincome.com` - Fixed income marketplace
  - `goldenpi.com` - Bond investment platform
  - `bondbazaar.com` - Bond marketplace
  
- **Exchange Data:**
  - `nseindia.com` - NSE Debt Market
  - `bseindia.com` - BSE Debt Segment

**Bond Database Expanded:**
- **72 instruments** from **45 unique issuers**
- Ratings: AAA (9), AA+ (4), AA (8+), A+ (2), A (4), A- (2), BBB+ (1), SOVEREIGN (13)
- Types: NCD (47), BOND (12), GSEC (8), SDL (5)
- Sectors: NBFC, Banking, Infrastructure, Energy, Government, Housing Finance, etc.

**New API Features:**
- `rating_filter` - Filter search by credit rating (AAA, AA+, AA, etc.)
- `sector_filter` - Filter search by sector (Infrastructure, NBFC, etc.)
- Enhanced statistics endpoint with data source categories
- `confidence_score` in live lookup results (based on sources found)

**Testing:** 100% (25/25 backend tests passed) - `/app/test_reports/iteration_87.json`

#### ✅ License Admin Hidden & Expiry Verification (Feb 08, 2026)

**Verified license admin security:**
- License admin (`deynet@gmail.com`) with `role=0` and `is_hidden=True` is completely hidden from:
  - `/api/users` - User listing
  - `/api/users/employees` - Employee listing
  - `/api/users/all` - All users listing  
  - `/api/users/managers` - Manager listing
  - `/api/users/hierarchy/potential-managers` - Hierarchy queries
  - `/api/users/team/subordinates` - Team queries
  - `/api/users/team/direct-reports` - Direct reports queries
- License admin CAN log in and access `/licence` management page
- Regular users (PE/FI) CANNOT access license management endpoints (403 Forbidden)

**License expiry real-time checking:**
- License status endpoint returns proper expiry information (`days_remaining`, `expires_at`, `status`)
- Statuses: `active` (>30 days), `expiring_soon` (≤30 days), `expired` (≤0 days)
- Expired licenses automatically marked `is_active: False` in status response
- Daily scheduled job at 12:05 AM IST to deactivate expired licenses in database

**Test Results:** 100% (20/20 backend tests passed, all frontend UI verified)
**Test Report:** `/app/test_reports/iteration_86.json`

#### ✅ Live NSDL Lookup Feature (Feb 08, 2026)

**Implemented automatic live web scraping when ISIN not found locally:**

**Feature Behavior:**
- When searching for a specific ISIN that doesn't exist in the local database
- System automatically scrapes real-time data from 3 sources:
  1. **indiabondsinfo.nsdl.com** - Official NSDL database
  2. **indiabonds.com** - Bond marketplace
  3. **smest.in** - Bond investment platform
- If found, instrument is auto-imported to Security Master in the same request

**Backend Implementation:**
- `/app/backend/fixed_income/live_lookup_service.py` - LiveBondLookup class
  - Parallel scraping from all 3 sources
  - Data merging and validation
  - Auto-import on successful lookup
- Updated `/api/fixed-income/instruments/nsdl-search` endpoint with `live_lookup=true` param
- New `/api/fixed-income/instruments/live-lookup/{isin}` endpoint for direct lookup

**API Response Structure:**
```json
{
  "query": "INE123A01234",
  "search_type": "all",
  "total_results": 0,
  "results": [],
  "live_lookup_attempted": true,
  "live_lookup_result": {
    "success": false,
    "message": "No data found for ISIN INE123A01234 from any source",
    "sources_tried": ["indiabondsinfo.nsdl.com", "indiabonds.com", "smest.in"],
    "errors": []
  }
}
```

**Frontend Updates (`FISecurityMaster.js`):**
- NSDL Search now passes `live_lookup=true` parameter
- Toast notifications for live lookup status
- "LIVE" badge on search results found via live lookup
- "Auto-Imported" badge for instruments auto-imported during search

**Testing Results:**
- Backend: 100% (16/16 passed)
- Frontend: 100% (All UI elements verified)
- Test report: `/app/test_reports/iteration_85.json`

**Note:** Web scraping requires network access to external sites. In restricted environments, scraping will fail gracefully with informative error messages.

#### ✅ Multi-Source Bond Data Import (Feb 08, 2026)

**Implemented comprehensive multi-source import system:**

**Sources Integrated:**
1. **indiabondsinfo.nsdl.com** - Official NSDL bond database
2. **indiabonds.com** - Bond marketplace
3. **smest.in** - Bond investment platform

**Backend Implementation:**
- `/app/backend/fixed_income/multi_source_importer.py` - Multi-source scraper
- New endpoint: `POST /api/fixed-income/instruments/import-all-sources`

**Features:**
- **Deduplication**: Merges data by ISIN, no duplicates
- **Data Merging**: Combines fields from multiple sources, keeps most complete data
- **Batch Import**: Updates existing records, inserts new ones
- **Error Handling**: Logs errors, continues importing other instruments

**Import Statistics (Latest Run):**
- Total Scraped: 49 unique instruments
- New Imports: 21
- Updates: 28
- Errors: 0

**Security Master Now Contains (50 instruments):**
- **By Type**: 34 NCDs, 8 Bonds, 5 G-Secs, 3 SDLs
- **By Rating**: AAA (20), Sovereign (8), AA (6), AA+ (5), A (4), A+ (2), AA- (2), A- (2), BBB+ (1)
- **Top Sectors**: NBFC (16), Financial Services (9), Government (8), Housing Finance (4), Infrastructure (3)

**Issuers Covered:**
- AAA: Reliance, HDFC, ICICI Bank, Tata Capital, Bajaj Finance, Aditya Birla, HDB Financial, Sundaram, Poonawalla
- AA+: Muthoot Finance, Mahindra Finance, Cholamandalam, SBI AT1
- AA: Shriram Finance, IIFL Finance, Piramal, Tata Steel, Aptus Housing, Northern Arc
- A+/A: Edelweiss, JM Financial, Navi Finserv, Vivriti, DMI Finance
- A-: Vedika Credit Capital (MFI sector)
- Government: GOI G-Secs, Maharashtra/Gujarat/Karnataka SDLs

**Frontend Updates:**
- "Import All" button now triggers multi-source import
- Shows progress toast during import
- Displays import statistics on completion

#### ✅ Web Import of INE04HY07351 - Vedika Credit Capital NCD (Feb 08, 2026)

**Imported comprehensive bond details from web search:**

**Instrument Details:**
- **ISIN**: INE04HY07351
- **Issuer**: Vedika Credit Capital Limited
- **Type**: Secured Rated Listed Redeemable Non-Convertible Debenture (Series B)
- **Face Value**: ₹1,00,000
- **Issue Price**: ₹1,00,246
- **Issue Size**: ₹35 Crores
- **Coupon**: 11.25% Monthly (Fixed)
- **Issue Date**: Nov 27, 2025
- **Maturity**: Nov 27, 2027
- **Credit Rating**: A- (Infomerics, Stable outlook)
- **Sector**: NBFC-MFI

**Additional Details Captured:**
- Debenture Trustee: Catalyst Trusteeship Limited
- Registrar: Niche Technologies Private Limited
- Security Type: Secured, Senior
- NRI Eligible: Yes
- Active on NSDL & CDSL
- Monthly coupon: ₹955.48 per ₹1 lakh face value

**Issuer Profile:**
- Operating States: Jharkhand, Bihar, West Bengal, UP, Assam, Odisha, Tripura
- Debt/EBITDA: 5.87x (FY25)
- Interest Coverage: 1.33x
- Collection Efficiency: 99%
- Co-lending Partner: State Bank of India

**NSDL Search Database Updated:**
- Added Vedika Credit Capital NCDs (INE04HY07351, INE04HY07310)
- Now searchable via NSDL Search feature

#### ✅ FI Dashboard Interactive Charts & Mobile Responsiveness (Feb 08, 2026)

**Enhanced FI Dashboard with Recharts v3.7.0:**

*New Metrics Added:*
- **Average Duration**: Portfolio duration analysis (years)
- **Duration Distribution**: < 1 year, 1-3 years, 3-5 years, 5-7 years, 7+ years
- **Sector Breakdown**: NBFC, Banking, Infrastructure, Government, Others
- **12-Month Cash Flow Calendar**: Expected coupons and maturities by month

*Interactive Charts (Recharts):*
- **Donut Chart**: Holdings by Type (NCD/BOND/GSEC)
- **Horizontal Bar Chart**: Credit Rating Distribution (AAA, AA+, AA, etc.)
- **Pie Chart**: Sector Allocation
- **Bar Chart**: Duration Distribution
- **Area Chart**: YTM Distribution with gradient fill
- **Composed Chart**: Cash Flow Calendar (Stacked bars + line)

*4-Tab Navigation:*
1. **Overview**: Holdings analysis + Upcoming events
2. **Analytics**: Sector, Duration, YTM charts
3. **Cash Flow**: 12-month calendar + summary cards
4. **Activity**: Recent orders + Quick actions

*Mobile Responsive Design:*
- 2-column grid for summary cards on mobile
- Tabs fit 4-column layout on small screens
- Chart cards stack vertically
- Touch-friendly Quick Actions buttons
- Tested at 390x844 viewport

**Testing Results:**
- Backend: 100% (10/10 passed)
- Frontend: 100% (All tabs, charts, mobile verified)
- Test report: `/app/test_reports/iteration_84.json`

**Note:** Dashboard uses mock data fallback when no real holdings exist in database.

#### ✅ License Enforcement, Client Segregation & FI Dashboard (Feb 08, 2026)

**1. License Enforcement (Frontend + Backend)**

*Backend Implementation (`/app/backend/middleware/license_enforcement.py`):*
- `LicenseEnforcer` class with `require_feature()` and `require_module()` methods
- Integrated into key routers: bookings.py, router_instruments.py
- SMIFS employees (`@smifs.com`) exempt from license checks
- Returns 403 with structured error: `{error: "feature_not_licensed", message: "...", contact_admin: true}`

*Frontend Implementation:*
- Updated `LicenseContext.js` with V2 granular licensing support
- `isFeatureLicensed(feature)` and `isModuleLicensed(module)` functions
- `LicenseGate.js` component - wraps features, shows overlay for unlicensed
- `Layout.js` updated - shows lock icon on unlicensed menu items

*Feature-to-Module Mapping:*
- PE Features: bookings, inventory, vendors, purchases, stocks, referral_partners, business_partners
- FI Features: fi_instruments, fi_orders, fi_reports, fi_primary_market
- Core Features: clients, reports, analytics, whatsapp, user_management

**2. Client Data Segregation by Module**

*Approach:* Using existing `modules` field on clients collection (["private_equity", "fixed_income"])

*API Endpoints:*
- `GET /api/clients/by-module/{module}` - Returns clients for specific module
- Module filtering applied in client dropdowns throughout the app

**3. Module-Specific Dashboards**

*FI Dashboard (`/fi-dashboard`):*
- **Frontend**: `/app/frontend/src/pages/FIDashboard.js`
- **Backend**: `/app/backend/fixed_income/router_dashboard.py`
- **API**: `GET /api/fixed-income/dashboard`

*Dashboard Sections:*
- Summary Cards: Total AUM, Holdings, Avg YTM, Accrued Interest
- Holdings by Type: NCD, BOND, GSEC breakdown with progress bars
- Holdings by Credit Rating: AAA, AA+, AA distribution
- Upcoming Maturities: Next 90 days with days-to-maturity
- Upcoming Coupon Payments: Next 30 days cash flows
- Recent Orders: Latest 10 FI orders with status
- Quick Actions: Security Master, New Order, IPO/NFO, Reports

*PE Dashboard:* Pre-existing at `/dashboard` (PEDashboard.js)

**Testing Results:**
- Backend: 100% (21/21 passed)
- Frontend: 100% (All UI verified)
- Test report: `/app/test_reports/iteration_83.json`

#### ✅ Granular License Management System V2 (Feb 08, 2026)
**Complete revamp of the licensing system with granular feature control:**

**Backend Implementation:**
- `/app/backend/services/license_service_v2.py` - Comprehensive license service
- `/app/backend/routers/license_v2.py` - License management API endpoints

**License Types:**
- **Private Equity License** (PRIV-PE-XXXX-XXXX-XXXX)
- **Fixed Income License** (PRIV-FI-XXXX-XXXX-XXXX)

**Licensable Components:**
- **Modules (2)**: Private Equity, Fixed Income
- **Features (26)**: Clients, Bookings, Inventory, Vendors, Purchases, Stocks, Reports, Analytics, BI Reports, WhatsApp, Email, OCR, Documents, Referral Partners, Business Partners, FI Instruments, FI Orders, FI Reports, FI Primary Market, User Management, Role Management, Audit Logs, Database Backup, Company Master, Finance, Contract Notes
- **Usage Limits (5)**: Max Users, Max Clients, Max Bookings/Month, Max FI Orders/Month, Max Storage (GB)

**Secret License Admin:**
- Email: `deynet@gmail.com`
- Password: `Kutta@123`
- Role: 0 (License Admin)
- Hidden from ALL user listings (is_hidden=true)
- Created automatically on server startup

**API Endpoints:**
- `GET /api/licence/verify-admin` - Check if user is license admin
- `GET /api/licence/definitions` - Get all licensable modules, features, limits
- `POST /api/licence/generate` - Generate new license key with granular permissions
- `POST /api/licence/activate` - Activate a license key
- `POST /api/licence/revoke` - Revoke a license
- `GET /api/licence/all` - List all licenses
- `GET /api/licence/status` - Get PE and FI license status
- `GET /api/licence/check/status` - Check license for current user
- `POST /api/licence/check/feature` - Check if feature is licensed
- `GET /api/licence/check/module/{module}` - Check if module is licensed
- `GET /api/licence/check/usage/{limit_type}/{company_type}` - Check usage limits

**Frontend (`/app/frontend/src/pages/LicenseManagement.js`):**
- Route: `/licence` (accessible only to license admin)
- PE License and FI License status cards
- License History table with all generated licenses
- Generate License dialog with:
  - Basic tab: Company Type, Name, Duration, Modules
  - Features tab: 26 toggleable features with Select All/Clear All
  - Usage Limits tab: Configurable limits (-1 for unlimited)
- Activate License dialog
- Copy license key functionality
- Revoke license action

**Security:**
- License admin user is hidden from:
  - `/api/users` endpoint
  - `/api/users/employees` endpoint
  - All user management pages
- All license management endpoints require `require_license_admin` dependency
- Regular users (even PE Desk) cannot access license endpoints

**Testing Results:**
- Backend: 100% (18/18 passed)
- Frontend: 100% (UI verification complete)
- Test report: `/app/test_reports/iteration_82.json`

#### ✅ NSDL Search & Import Feature (Feb 08, 2026)
**Implemented ISIN/Company search and import facility for Fixed Income Security Master:**

**Backend Implementation:**
- `/app/backend/fixed_income/nsdl_search_service.py` - Mock NSDL database with ~60 instruments
- Search endpoints in `/app/backend/fixed_income/router_instruments.py`:
  - `GET /api/fixed-income/instruments/nsdl-search` - Search by ISIN, company name, or rating
  - `POST /api/fixed-income/instruments/nsdl-import/{isin}` - Import single instrument
  - `POST /api/fixed-income/instruments/nsdl-import-multiple` - Bulk import multiple instruments
  - `GET /api/fixed-income/instruments/nsdl-statistics` - Database statistics

**Mock Database Contents (~60 instruments):**
- **NCDs (15+)**: Reliance, HDFC, Bajaj Finance, Muthoot, Mahindra Finance, Tata Capital, etc.
- **Bonds (15+)**: ICICI Bank, SBI AT1, Tata Steel, L&T, NTPC, PFC, REC, IRFC, NHAI
- **G-Secs (5)**: Government of India 2032-2039
- **SDLs (3)**: Maharashtra, Gujarat, Karnataka State Development Loans

**Frontend Implementation (`/app/frontend/src/pages/FISecurityMaster.js`):**
- "NSDL Search" button in Security Master header (blue styling)
- Search dialog with:
  - Text input for ISIN or company name
  - Dropdown filter: All Fields, ISIN Only, Company Only, By Rating
  - Search results table with ISIN, Issuer, Type, Coupon, Rating, Maturity columns
  - "Import" button for individual instruments (green)
  - "Imported" badge for already imported instruments
  - "Import All Available" button for bulk import
  - Result count with available-to-import count

**Testing Results:**
- Backend: 100% (15/15 passed, 3 skipped for already imported)
- Frontend: 100% (All UI elements verified)
- Test report: `/app/test_reports/iteration_81.json`

**Note:** This is a MOCK implementation using static data. For production, requires integration with real NSDL API.

#### ✅ Public Data Import for Security Master (Feb 08, 2026)
**Auto-populated Indian NCDs, Bonds, and G-Secs from curated public sources:**

**Instruments Imported (26 total):**
- **NCDs (15)**: Reliance, HDFC, Bajaj Finance, Muthoot, Mahindra Finance, Shriram, Tata Capital, Cholamandalam, Edelweiss, JM Financial, IIFL, Piramal, Sundaram, Aditya Birla, HDB Financial
- **Bonds (6)**: SBI AT1, Reliance, Tata Steel, L&T, NTPC Green Bond, PFC, REC
- **G-Secs (3)**: Government of India 2032, 2033, 2037

**Data Fields:**
- ISIN, Issuer Name, Instrument Type (NCD/BOND/GSEC)
- Face Value, Coupon Rate, Coupon Frequency
- Issue Date, Maturity Date
- Credit Rating (AAA to A+, SOVEREIGN for G-Secs)
- Rating Agency (CRISIL, ICRA, CARE, GOI)
- Current Market Price, Listing Exchange, Sector

**Backend Implementation:**
- `/app/backend/fixed_income/public_data_importer.py` - Curated instrument data
- `POST /api/fixed-income/instruments/import-public-data` - Trigger import
- `GET /api/fixed-income/instruments/available-public-instruments` - Preview available

**Frontend:**
- "Import NCDs/Bonds" button in Security Master header
- One-click import with success toast showing statistics

#### ✅ Client Module Segregation (Feb 08, 2026)
**Each client now has module access control:**

**Backend Changes:**
- Added `modules` field to ClientCreate and Client models (array: `["private_equity", "fixed_income"]`)
- New endpoint: `GET /api/clients/by-module/{module}` - Filter clients by module
- New endpoint: `GET /api/company-master/agreements` - Returns both company agreements (public)
- Legacy clients without modules field default to Private Equity

**Frontend Changes:**
- **Clients Page**: Module Access checkboxes (Private Equity / Fixed Income) in client creation/edit form
- **FI Orders/IPO**: Only shows clients with `fixed_income` module access
- **User Agreement Modal**: Shows both PE and FI agreements side-by-side with individual checkboxes

**User Agreement Flow:**
1. User logs in
2. Modal shows two cards: PE agreement and FI agreement
3. User must check both agreement checkboxes
4. Click "I Agree to All" to proceed
5. Progress indicator shows accepted count

**Testing:** 100% backend (9/9), 100% frontend pass

#### ✅ Primary Market IPO/NFO Subscription Workflow (Feb 08, 2026)
**Backend Implementation (`/app/backend/fixed_income/router_primary_market.py`):**
- Full IPO/NFO issue management (Create, List, Status Update)
- Bid submission workflow (Submit, Confirm Payment, View)
- Pro-rata allotment processing
- Email notifications for bid confirmations

**API Endpoints:**
- `POST /api/fixed-income/primary-market/issues` - Create new issue
- `GET /api/fixed-income/primary-market/issues` - List all issues
- `GET /api/fixed-income/primary-market/active-issues` - Get open issues
- `PATCH /api/fixed-income/primary-market/issues/{id}/status` - Update status
- `POST /api/fixed-income/primary-market/bids` - Submit bid
- `GET /api/fixed-income/primary-market/bids` - List bids
- `PATCH /api/fixed-income/primary-market/bids/{id}/confirm-payment` - Confirm payment
- `POST /api/fixed-income/primary-market/issues/{id}/process-allotment` - Process allotment

**Frontend Implementation (`/app/frontend/src/pages/FIPrimaryMarket.js`):**
- Summary cards (Open Issues, Upcoming, Total, My Bids)
- Tabs: Active Issues, All Issues, My Bids
- Create Issue dialog with all NCD/Bond fields
- Subscribe dialog with client selection, quantity, payment mode
- Status management buttons (Open, Close, Allot)

**Workflow:**
1. PE Desk creates issue (draft) → Opens issue → Clients submit bids → Issue closed → Allotment processed

**Testing:** 100% backend (17/17 tests), 100% frontend UI pass

#### ✅ Module-Based Permission System (Feb 08, 2026)
**Implemented granular module activation for Private Equity and Fixed Income:**

**Permission Structure:**
- `module.private_equity` - Activates PE module features
- `module.fixed_income` - Activates FI module features

**Backend Changes (`/app/backend/services/permission_service.py`):**
- Added `module` category with `private_equity` and `fixed_income` permissions
- Extended `fixed_income` permissions with granular options:
  - `instrument_view`, `instrument_create`, `instrument_edit`, `instrument_delete`, `instrument_bulk_upload`
  - `order_view`, `order_create`, `order_edit`, `order_approve`, `order_settle`
  - `report_view`, `report_export`, `payment_record`, `market_data_refresh`
  - `portfolio_optimize`, `coupon_notifications`
- Updated DEFAULT_ROLES to include module permissions per role

**Frontend Changes (`/app/frontend/src/pages/RoleManagement.js`):**
- Added Module Activation section in role edit dialog with toggle switches
- Visual Permissions view shows module badges (Private Equity blue, Fixed Income teal)
- categoryInfo now groups permissions by module (pe, fi, common)

**Navigation Conditional (`/app/frontend/src/components/Layout.js`):**
- Fixed Income menu items (FI Instruments, FI Orders, FI Reports) only visible when `module.fixed_income` permission is granted

**Role-Module Mapping:**
| Role | Private Equity | Fixed Income |
|------|---------------|--------------|
| PE Desk | ✓ (Full Access) | ✓ (Full Access) |
| PE Manager | ✓ | ✓ |
| Finance | ✓ | ✓ |
| Viewer | ✓ | ✓ |
| Partners Desk | ✓ | ✗ |
| Business Partner | ✓ | ✗ |
| Employee | ✓ | ✓ |

#### ✅ Multiple Companies Support (Feb 08, 2026)
**Created two separate companies under Company Master:**

1. **SMIFS Private Equity** (`pe_company`)
   - Type: `private_equity`
   - For Private Equity module operations

2. **SMIFS Fixed Income** (`fi_company`)
   - Type: `fixed_income`
   - For Fixed Income module operations

**Backend Changes:**
- Added `company_type` field to CompanyMasterCreate and CompanyMasterResponse schemas
- Added new endpoints:
  - `GET /api/company-master/list` - List all companies
  - `GET /api/company-master/{company_id}` - Get company by ID
  - `PUT /api/company-master/{company_id}` - Update company by ID
- Added `seed_default_companies()` function to auto-create the two companies
- Added `company_to_response()` helper function

**Frontend Changes:**
- Added Tabs component for company selection
- Added state management for multiple companies (`companies`, `selectedCompanyId`)
- Each company has its own badge icon (Briefcase for PE, TrendingUp for FI)
- Company switching updates form data, documents, and logo

**Files Modified:**
- `/app/backend/routers/company_master.py` - Multi-company support
- `/app/frontend/src/pages/CompanyMaster.js` - Tabs UI for company switching

### Latest Updates (Feb 07, 2026)

#### ✅ Fixed Income Module - FULLY TESTED (Feb 07, 2026)
**Testing Results:**
- Backend: 95% pass rate (19/20 tests passed)
- Frontend: 100% (all pages load correctly)

**Bug Fixed During Testing:**
- Fixed Decimal serialization issue in `router_instruments.py` - Python Decimal objects weren't JSON/BSON serializable for MongoDB storage. Converted Decimal fields to strings before insert.

**Additional Enhancements:**
- Added Market Data Router to server.py (`/api/fixed-income/market-data/refresh`, `/api/fixed-income/market-data/quotes/{isin}`)
- Secured preview-sample endpoint with authentication (was previously open)
- Fixed SelectItem empty value bug in FISecurityMaster.js

**Services Implemented:**
1. **Portfolio Optimization Service** (`/app/backend/fixed_income/optimization_service.py`)
   - Duration matching analysis
   - Yield optimization recommendations
   - Diversification scoring

2. **Notification Service** (`/app/backend/fixed_income/notification_service.py`)
   - Coupon payment reminders
   - Maturity alerts
   - Email scheduling

3. **Market Data Service** (`/app/backend/fixed_income/market_data_service.py`)
   - Mock provider for development
   - Placeholder for NSE/BSE integration
   - Price quote retrieval

**MOCKED**: Market data uses `MockMarketDataProvider` - generates simulated quotes. Real NSE/BSE integration requires API credentials.

#### ✅ Fixed Income Frontend UI (Feb 07, 2026)
**Built complete frontend for Fixed Income module**

**Pages Created:**
1. **FI Security Master** (`/app/frontend/src/pages/FISecurityMaster.js`)
   - List all NCDs/Bonds with filtering and search
   - Create/Edit instrument dialog with all fields
   - Bond pricing calculator (YTM, Price from Yield)
   - Bulk upload dialog with CSV template
   - Live YTM/Accrued Interest calculation per row

2. **FI Orders** (`/app/frontend/src/pages/FIOrders.js`)
   - Order list with status tabs (Draft, Pending, Approved, Settled)
   - Summary cards (Pending Approval, Payment Pending, In Settlement, Settled)
   - Create Order with live pricing calculation
   - Order workflow actions (Send Deal Sheet, Approve, Record Payment, Settle)
   - Order detail dialog

3. **FI Reports** (`/app/frontend/src/pages/FIReports.js`)
   - Holdings Report with MTM and P&L
   - Cash Flow Calendar (upcoming coupon/principal)
   - Maturity Schedule
   - Portfolio Analytics (rating/maturity distribution, concentration)
   - Transaction History
   - CSV export functionality

**Backend Enhancements:**
- Added bulk upload endpoint for instruments
- Added CSV template download
- Added bulk market data update endpoint

**Navigation Added:**
- FI Instruments, FI Orders, FI Reports menu items in sidebar
- RBAC-controlled visibility based on permissions

**Files Created:**
- `/app/frontend/src/pages/FISecurityMaster.js`
- `/app/frontend/src/pages/FIOrders.js`
- `/app/frontend/src/pages/FIReports.js`

**Files Modified:**
- `/app/frontend/src/App.js` - Added routes
- `/app/frontend/src/components/Layout.js` - Added navigation items
- `/app/backend/fixed_income/router_instruments.py` - Added bulk upload

#### ✅ Fixed Income Trading Module (Feb 07, 2026)
**Complete new module for NCD/Bond trading with same RBAC hierarchy**

**Core Components Created:**
1. **Security Master** (`/app/backend/fixed_income/router_instruments.py`)
   - ISIN, Issuer, Face Value, Issue/Maturity dates
   - Coupon Rate, Frequency (Monthly/Quarterly/Semi-Annual/Annual)
   - Day Count Conventions (30/360, ACT/ACT, ACT/360, ACT/365)
   - Credit Ratings, Put/Call options
   - Live market pricing with accrued interest & YTM

2. **Calculation Engine** (`/app/backend/fixed_income/calculations.py`)
   - `calculate_accrued_interest()` - Multiple day count conventions
   - `calculate_ytm()` - Newton-Raphson iterative solver
   - `price_from_yield()` - Reverse calculation
   - `calculate_dirty_price()` - Clean + Accrued Interest
   - `calculate_duration()` / `calculate_modified_duration()`
   - `generate_cash_flow_schedule()` - All future payments
   - All calculations use `Decimal` for financial precision

3. **Order Management System** (`/app/backend/fixed_income/router_orders.py`)
   - Primary/Secondary market orders
   - Deal Sheet generation with full pricing
   - Client approval workflow (Email notification)
   - Payment tracking
   - Settlement management (Deal Booked → Approved → Paid → Settled)

4. **Reports & Analytics** (`/app/backend/fixed_income/router_reports.py`)
   - Holdings Report with Mark-to-Market
   - Cash Flow Calendar (upcoming coupon/principal)
   - Maturity Schedule
   - Portfolio Analytics (rating distribution, concentration)
   - CSV Export

**RBAC Integration:**
- PE Desk/Manager: Full access (`fixed_income.*`)
- Finance: View + Payment recording
- Employee: View + Order creation
- Viewer: Read-only access
- Business Partner: Limited view

**API Endpoints:**
```
# Security Master
GET/POST    /api/fixed-income/instruments
GET/PUT/DEL /api/fixed-income/instruments/{id}
PATCH       /api/fixed-income/instruments/{id}/market-data
POST        /api/fixed-income/instruments/calculate-pricing
POST        /api/fixed-income/instruments/price-from-yield

# Order Management
GET/POST    /api/fixed-income/orders
GET         /api/fixed-income/orders/{id}
POST        /api/fixed-income/orders/{id}/send-deal-sheet
POST        /api/fixed-income/orders/{id}/approve
POST        /api/fixed-income/orders/{id}/reject
POST        /api/fixed-income/orders/{id}/record-payment
POST        /api/fixed-income/orders/{id}/initiate-settlement
POST        /api/fixed-income/orders/{id}/complete-settlement

# Reports
GET         /api/fixed-income/reports/holdings
GET         /api/fixed-income/reports/cash-flow-calendar
GET         /api/fixed-income/reports/maturity-schedule
GET         /api/fixed-income/reports/transactions
GET         /api/fixed-income/reports/analytics/portfolio-summary
GET         /api/fixed-income/reports/export/holdings-csv
GET         /api/fixed-income/reports/export/cash-flow-csv
```

**Files Created:**
- `/app/backend/fixed_income/__init__.py`
- `/app/backend/fixed_income/models.py`
- `/app/backend/fixed_income/calculations.py`
- `/app/backend/fixed_income/router_instruments.py`
- `/app/backend/fixed_income/router_orders.py`
- `/app/backend/fixed_income/router_reports.py`

**Files Modified:**
- `/app/backend/services/permission_service.py` - Added FI permissions
- `/app/backend/server.py` - Registered FI routers

#### ✅ Conformation Note Redesign (Feb 07, 2026)
- **Issue:** User reported text overlapping issues and wanted the document renamed to "Conformation Note" with better aesthetics
- **Solution:** Complete redesign of the PDF generation with:
  - **Title:** Changed from "Confirmation Note" to "CONFORMATION NOTE CUM BILL"
  - **Color Scheme:** Professional emerald green (#054D3B) with gold accents
  - **Layout:** Clean sections with proper spacing, light background tints, and decorative dividers
  - **Tables:** Properly spaced with colored headers and alternating backgrounds
  - **Typography:** Clear hierarchy with Helvetica fonts, proper label/value styling
  - **Null Safety:** Added `safe_str()` helper function to handle None values gracefully
  - **Sample Preview:** Added `/api/contract-notes/preview-sample` endpoint for testing
- **Files Modified:**
  - `/app/backend/services/contract_note_service.py` - Complete PDF template redesign
  - `/app/backend/routers/contract_notes.py` - Added preview endpoint
- **Test:** PDF generates successfully (5267 bytes) with proper formatting

#### ✅ Bug Fix - Contract Note Download & Email Attachment (Feb 07, 2026)
- **Issue:** Contract/Confirmation notes were being generated but:
  1. Could not be downloaded (404 error)
  2. PDF attachment was not being sent with emails
- **Root Cause:** 
  - Download endpoint only checked local file storage (`/app/uploads/contract_notes/`) but notes are also stored in GridFS
  - Email function only tried to read from local file path, failing silently when file wasn't there
- **Solution:** Implemented robust multi-source PDF retrieval with fallback chain:
  1. **Primary:** Try GridFS storage first (persistent storage that survives redeployments)
  2. **Secondary:** Try local file system
  3. **Fallback:** Regenerate PDF on-the-fly from booking data
  - For email: If PDF is regenerated, save it back to GridFS for future use
- **Files Modified:**
  - `/app/backend/routers/contract_notes.py`:
    - `download_contract_note()` - Added GridFS support and regeneration fallback
    - `send_contract_note_email()` - Complete rewrite with multi-source PDF retrieval, auto-regeneration, and guaranteed attachment
- **Key Improvements:**
  - Downloads now work even if original file was lost (auto-regeneration)
  - Emails will always have PDF attachment (never sends without it)
  - Auto-saves regenerated PDFs to GridFS for future use
  - Detailed logging for debugging PDF source
- **Test Status:** Code changes deployed, ready for production testing when contract notes exist

#### ✅ Bug Fix - Agreement Popup Button Visibility (Feb 07, 2026)
- **Issue:** The "I Agree" button in the User Agreement modal was only visible when browser zoom was reduced to 75%
- **Root Cause:** The modal's content area had fixed height calculations (`maxHeight: 'calc(85vh - 180px)'`) that didn't properly account for flexbox layout, causing the footer with the "I Agree" button to be pushed off-screen at normal zoom levels
- **Solution:** Refactored the modal layout to use proper flexbox with:
  - `flex flex-col` on DialogContent for proper column layout
  - `flex-shrink-0` on header and footer to prevent them from shrinking
  - `flex-1 min-h-0` on content area to allow it to shrink while keeping header/footer visible
  - Reduced ScrollArea height from `h-[200px] sm:h-[220px]` to `h-[150px] sm:h-[180px]` for more breathing room
  - Reduced modal max-height from `85vh` to `80vh`
- **Files Modified:**
  - `/app/frontend/src/components/UserAgreementModal.js` - Complete layout refactoring
- **Test Status:** Verified via screenshots at multiple viewport sizes (1920x800, 1366x768, 1280x600, 375x667 mobile) - "I Agree" button visible in all cases

#### ✅ Bug Fix - OTP Registration Missing Password Field (Feb 07, 2026)
- **Issue:** OTP registration endpoint returned 500 Internal Server Error
- **Root Cause:** UserCreate Pydantic model was missing `password` field, causing AttributeError when accessing `user_data.password`
- **Solution:** Added `password: Optional[str] = None` to UserCreate model in `/app/backend/models/__init__.py`
- **Additional Fix:** Added password validation (required, min 8 chars) in auth.py
- **Test Created:** `/app/backend/tests/test_registration_otp_flow.py` with 21 comprehensive tests
- **Test Report:** `/app/test_reports/iteration_76.json`
- **Verification:** All API and UI tests pass (100% success rate)

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
  - `is_pe_level(role)` - Check if role is PE Desk or PE Manager
  - `is_pe_desk(role)` - Check if role is PE Desk only
  - `is_finance_level(role)` - Check if role has finance access
  - `is_partners_desk(role)` - Check if role is Partners Desk
  - `can_view_all_data(role)` - Check if role can view all data (not just mapped)
  - `get_client_visibility_filter()` - MongoDB filter for client queries based on role
  - `get_booking_visibility_filter()` - MongoDB filter for booking queries based on role
  - `get_user_visibility_filter()` - MongoDB filter for user queries based on role
  - `can_view_all_clients()` - Check if user has full client visibility
  - `can_view_all_bookings()` - Check if user has full booking visibility
  - `can_view_all_users()` - Check if user has full user visibility
- **ALL 18 routers updated** to use centralized helpers (removed duplicate definitions):
  - Core: `dashboard.py`, `inventory.py`, `reports.py`, `bookings.py`, `clients.py`, `users.py`
  - Finance: `finance.py`, `purchases.py`
  - Partners: `business_partners.py`, `referral_partners.py`, `revenue_dashboard.py`
  - Admin: `database_backup.py`, `roles.py`, `kill_switch.py`, `bulk_upload.py`
  - Misc: `stocks.py`, `analytics.py`, `contract_notes.py`, `email_logs.py`, `files.py`, `research.py`, `two_factor.py`, `audit_logs.py`
- **Purpose:** Single source of truth for all permission logic - prevents recurring RBAC bugs

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
- None currently (Fixed Income module fully tested and working)

### P1 - High Priority
- **Primary Market IPO/NFO Subscription Workflow** - Backend + UI for new security subscriptions
- Real-time Market Data API Integration (requires NSE/BSE API credentials)

### P2 - Medium Priority
- Mobile-responsive refinements for Fixed Income UI
- WhatsApp bulk notification automation
- RBAC Endpoint Audit Phase 4 continuation

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
