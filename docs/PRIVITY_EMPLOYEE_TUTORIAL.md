# PRIVITY Employee User Guide
## Complete Tutorial for Using the Share Booking System

---

# Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Managing Clients](#3-managing-clients)
4. [Creating Bookings](#4-creating-bookings)
5. [Viewing Inventory](#5-viewing-inventory)
6. [Reports & Analytics](#6-reports--analytics)
7. [Notifications & Alerts](#7-notifications--alerts)
8. [Tips & Best Practices](#8-tips--best-practices)
9. [FAQ](#9-faq)

---

# 1. Getting Started

## 1.1 Logging In

1. Open your web browser and navigate to the PRIVITY application URL
2. Enter your registered **Email Address**
3. Enter your **Password**
4. Click **"Sign In"**

![Login Page](screenshots/01_login.png)

**First Time Login:**
- You will be asked to accept the User Agreement
- Optionally change your default password for security
- Read and accept the terms to proceed

## 1.2 Understanding the Interface

After logging in, you'll see:

- **Sidebar Menu** (Left): Navigation to all modules
- **Header Bar** (Top on Mobile): App title, theme toggle, notifications
- **Main Content Area**: Current page content
- **PE Status Indicator**: Shows if PE Desk support is available
  - 🟢 Green = PE Support Available
  - 🔴 Red = PE Support Offline

## 1.3 Dark Mode

Toggle between Light and Dark mode:
1. Click the **Sun/Moon icon** in the sidebar footer (desktop) or header (mobile)
2. Your preference is saved automatically

---

# 2. Dashboard Overview

The Dashboard provides a quick snapshot of your activities.

![Dashboard](screenshots/02_dashboard.png)

**Key Metrics Displayed:**
- Total Bookings (Pending, Confirmed, Completed)
- Today's Activities
- Recent Bookings
- Quick Action Buttons

**Navigation Tips:**
- Click any card to navigate to detailed view
- Use the sidebar to switch between modules

---

# 3. Managing Clients

## 3.1 Viewing Clients

1. Click **"Clients"** in the sidebar menu
2. View the list of all clients with status indicators

![Clients Page](screenshots/03_clients.png)

**Client Status Colors:**
- 🟢 Green = Approved
- 🟡 Yellow = Pending Approval
- 🔴 Red = Rejected

## 3.2 Adding a New Client

1. Click **"Add Client"** button (top right)
2. Fill in the required fields:
   - **Client Type**: Proprietor, Partnership, Company, HUF, Trust, etc.
   - **Name**: Full legal name
   - **PAN Number**: Mandatory for all clients
   - **Mobile & Email**: Contact information
   - **Bank Details**: Account number, IFSC, bank name
   - **Demat Details**: DP ID, Client ID, BO ID
3. Upload required documents (Aadhar, PAN, etc.)
4. Click **"Submit for Approval"**

**Important Notes:**
- PAN number must be unique
- Client requires PE Desk approval before bookings can be made
- Keep all documents ready before starting

## 3.3 Searching & Filtering Clients

- Use the **Search Bar** to find clients by name, PAN, or mobile
- Use **Status Filter** to show only Approved/Pending/Rejected clients
- Click column headers to sort

## 3.4 Viewing Client Portfolio

1. Find the client in the list
2. Click the **Portfolio icon** (pie chart)
3. View all bookings and transactions for that client

---

# 4. Creating Bookings

## 4.1 Creating a New Booking

1. Click **"Bookings"** in the sidebar
2. Click **"Create Booking"** button

![Bookings Page](screenshots/04_bookings.png)

3. Fill in the booking form:
   - **Select Client**: Choose from approved clients
   - **Select Stock**: Choose available stock
   - **Quantity**: Enter number of shares
   - **Selling Price**: Enter the price per share
   - **Booking Type**: Fresh or Additional

**Landing Price Display:**
When you select a stock, you'll see:
- **Landing Price (LP)**: The buying price (shown in green box)
- **Available Stock**: How many shares are available
- **Revenue Preview**: Calculated profit based on your selling price

4. Click **"Create Booking"** to submit

## 4.2 Booking Workflow

After creation, a booking goes through these stages:

```
Created → Client Confirmation → PE Approval → DP Transfer → Completed
```

1. **Client Confirmation**: Client receives email/WhatsApp to confirm
2. **PE Approval**: PE Desk reviews and approves the booking
3. **DP Transfer**: Shares are transferred to client's demat account
4. **Completed**: Transaction is finalized

## 4.3 Tracking Booking Status

Each booking shows status badges:
- **Client Status**: Pending/Accepted/Denied
- **Approval Status**: Pending/Approved/Rejected
- **Payment Status**: Unpaid/Partial/Paid
- **DP Transfer**: Pending/Completed

## 4.4 Understanding Revenue Calculation

```
Revenue = (Selling Price - Landing Price) × Quantity
```

Example:
- Selling Price: ₹150
- Landing Price: ₹120
- Quantity: 100
- **Revenue: (150 - 120) × 100 = ₹3,000**

---

# 5. Viewing Inventory

## 5.1 Inventory Dashboard

Click **"Inventory"** in the sidebar to view all available stocks.

![Inventory Page](screenshots/05_inventory.png)

**Columns Explained:**
- **Stock Symbol**: Trading symbol
- **Available Qty**: Shares available for booking
- **Blocked Qty**: Shares reserved for pending bookings
- **WAP**: Weighted Average Price (actual cost) - *PE Level only*
- **LP**: Landing Price (customer-facing price)
- **Value**: Total value of holdings

## 5.2 Understanding LP vs WAP

| Term | Meaning | Who Sees It |
|------|---------|-------------|
| **WAP** | Actual cost price of stock | PE Desk/Manager only |
| **LP** | Price shown to customers | Everyone |
| **HIT** | (LP - WAP) × Qty = PE margin | PE Desk/Manager only |

**For Employees:**
- You will see the **Landing Price** as the buying price
- This is the price used for all booking calculations
- WAP is hidden to maintain pricing confidentiality

---

# 6. Reports & Analytics

## 6.1 P&L Reports

1. Click **"Reports"** in the sidebar
2. Select date range and filters
3. View profit/loss summary

![Reports Page](screenshots/06_reports.png)

**Available Filters:**
- Date Range
- Stock
- Client
- Status

**Export Options:**
- Click **"Export Excel"** for spreadsheet
- Click **"Export PDF"** for printable report

## 6.2 Revenue Dashboard

View your personal revenue performance:
1. Click **"My Dashboard"** (if available based on your role)
2. See your bookings, commissions, and targets

---

# 7. Notifications & Alerts

## 7.1 Real-Time Notifications

PRIVITY sends instant notifications for:
- New booking confirmations
- Approval status changes
- Payment receipts
- Important system alerts

**Notification Bell:**
- Click the 🔔 icon in the header
- Red badge shows unread count
- Click notification to view details

## 7.2 Floating Notifications

Important alerts appear at the bottom-right corner:
- **Green border**: Success messages
- **Red border**: Error or rejection
- **Yellow border**: Pending action required
- **Blue border**: Information

Click **"Mark as Read"** to dismiss.

---

# 8. Tips & Best Practices

## 8.1 For Efficient Booking

✅ **DO:**
- Verify client details before booking
- Check available inventory first
- Double-check quantity and price
- Save client's preferred contact method

❌ **DON'T:**
- Create duplicate bookings
- Book more than available quantity
- Skip client confirmation
- Modify completed bookings

## 8.2 For Client Management

✅ **Best Practices:**
- Keep client documents up to date
- Verify bank details before payment
- Note special instructions in comments
- Follow up on pending confirmations

## 8.3 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Quick search |
| `Escape` | Close dialogs |
| `Enter` | Submit forms |

---

# 9. FAQ

### Q: I forgot my password. What should I do?
**A:** Click "Forgot Password" on the login page and follow the email instructions. Or contact PE Desk for assistance.

### Q: Why can't I create a booking for a client?
**A:** The client must be in "Approved" status. Check if the client is pending approval from PE Desk.

### Q: How do I know if PE support is available?
**A:** Look at the status indicator under the PRIVITY logo - Green means available, Red means offline.

### Q: Can I edit a booking after creation?
**A:** Only before client confirmation. Contact PE Desk for changes after confirmation.

### Q: Why is my booking showing "Loss"?
**A:** If selling price is less than landing price, it's a loss booking. These require additional approval from PE Desk.

### Q: How do I export data?
**A:** Most pages have "Export Excel" or "Export PDF" buttons. Click to download.

### Q: Who do I contact for help?
**A:** 
- Email: pe@smifs.com
- Phone: 9088963000

---

# Quick Reference Card

| Task | Where to Go |
|------|-------------|
| Add new client | Clients → Add Client |
| Create booking | Bookings → Create Booking |
| Check inventory | Inventory |
| View reports | Reports |
| Track payments | Finance |
| Get help | Contact PE Desk |

---

## Support Contacts

**PE Desk**
- 📧 Email: pe@smifs.com
- 📞 Phone: 9088963000

**System Status**
- 🟢 PE Online - Support Available
- 🔴 PE Offline - Leave Message

---

*Document Version: 1.0*
*Last Updated: February 2026*
*© 2026 SMIFS Limited*
