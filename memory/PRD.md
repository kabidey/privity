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
- Backend: 96% pass rate (22/23 tests)
- Frontend: 100% pass rate
- Overall: 98% success

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
- None - all core features implemented

### P1 (High Priority)
- [ ] Audit logging for all actions
- [ ] Real-time notifications with WebSocket
- [ ] Password reset functionality
- [ ] Two-factor authentication

### P2 (Medium Priority)
- [ ] Bulk booking close functionality
- [ ] Advanced analytics dashboard
- [ ] Email templates customization
- [ ] Mobile app (React Native)

## Next Tasks
1. Add audit logging for compliance
2. Implement WebSocket notifications
3. Add password reset flow
4. Create advanced analytics with more chart types
