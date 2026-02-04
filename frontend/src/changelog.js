// Changelog data - Add new entries at the top
// Format: { version, date, changes: [{ type, description }] }
// Types: 'feature', 'fix', 'improvement', 'security'
import { getVersionDetails } from './version';

// Get dynamic version info for changelog header
export const getCurrentBuildInfo = () => {
  const details = getVersionDetails();
  return {
    version: `v${details.major}.${details.minor}.${details.patch}`,
    build: details.build,
    fullVersion: `v${details.major}.${details.minor}.${details.patch}.${details.build}`
  };
};

const CHANGELOG = [
  {
    version: 'v6.2.4.7',
    date: '2026-02-04',
    title: 'Business Intelligence & WhatsApp Integration',
    changes: [
      { type: 'feature', description: 'Business Intelligence Report Builder - Generate custom reports with multiple dimensions and filters' },
      { type: 'feature', description: 'BI Report Types - Bookings, Clients, Revenue, Inventory, Payments, P&L analysis with Excel export' },
      { type: 'feature', description: 'WhatsApp Notification System - Self-hosted QR-based WhatsApp integration for alerts' },
      { type: 'feature', description: 'WhatsApp Templates - Customizable message templates for bookings, payments, DP transfers' },
      { type: 'feature', description: 'WhatsApp Recipient Types - Send to clients, users, Business Partners, Referral Partners' },
      { type: 'feature', description: 'BP Override Dashboard Widget - PE Dashboard shows pending BP revenue override count' },
      { type: 'feature', description: 'New Permissions - reports.bi_builder, notifications.whatsapp added to Role Management' },
      { type: 'security', description: 'Permission-based WhatsApp access - Only authorized roles can manage WhatsApp settings' },
    ]
  },
  {
    version: 'v6.2.4',
    date: '2026-02-04',
    title: 'BP Revenue Share Override & Security Hardening',
    changes: [
      { type: 'feature', description: 'BP Revenue Share Override - Business Partners can request lower revenue share with approval workflow' },
      { type: 'feature', description: 'BP Override Approval - PE Desk can approve/reject BP revenue overrides from Bookings page' },
      { type: 'feature', description: 'Override Tracking - Visual badges showing pending/approved/rejected override status' },
      { type: 'security', description: 'Bot Protection Middleware - Blocks crawlers, scanners, and common attack vectors' },
      { type: 'feature', description: 'Threat Monitor Dashboard - Real-time visualization of blocked threats in Security page' },
      { type: 'feature', description: 'Centralized Page Protection - useProtectedPage hook for consistent auth/permission handling' },
      { type: 'fix', description: 'Permission-Based Access - Replaced hardcoded role checks with granular permissions across 14 pages' },
      { type: 'fix', description: 'DP Permission Access - Fixed access for users with dp.* permissions' },
      { type: 'improvement', description: 'Removed Change Password from main menu - Now only in Account Security' },
    ]
  },
  {
    version: 'v6.2.3',
    date: '2026-02-03',
    title: 'Database Management & Selective Clear',
    changes: [
      { type: 'feature', description: 'Selective Database Clear - Choose specific collections or categories to clear' },
      { type: 'feature', description: 'Preview Mode - See exactly what will be deleted before clearing' },
      { type: 'feature', description: 'Exclude Records - Protect specific records from deletion' },
      { type: 'feature', description: 'Clear Files Only - Remove uploaded files without touching database' },
      { type: 'feature', description: 'Refresh Booking Status - Manually recalculate payment and approval status' },
      { type: 'feature', description: 'RP Mapping Update - Edit Referral Partner assignment on existing bookings' },
      { type: 'improvement', description: 'Enhanced Client Employee Mapping - Fixed race condition in dropdown loading' },
    ]
  },
  {
    version: 'v4.1.0',
    date: '2026-02-02',
    title: 'Two-Factor Authentication (TOTP)',
    changes: [
      { type: 'security', description: 'Two-Factor Authentication (2FA) - Enable TOTP-based 2FA using authenticator apps (Google Authenticator, Authy, Microsoft Authenticator)' },
      { type: 'feature', description: 'Account Security Page - Dedicated page for managing 2FA settings, password, and account info' },
      { type: 'feature', description: 'QR Code Generation - Scan QR code with authenticator app for easy setup' },
      { type: 'feature', description: 'Manual Secret Entry - Option to manually enter secret key for TOTP apps' },
      { type: 'feature', description: 'Backup Codes - 10 one-time backup codes for account recovery if device is lost' },
      { type: 'feature', description: 'Regenerate Backup Codes - Generate new backup codes (invalidates old ones)' },
      { type: 'feature', description: 'Security Tips - In-app security recommendations for users' },
      { type: 'security', description: 'Password Confirmation - All 2FA operations require password verification' },
      { type: 'security', description: 'Audit Logging - 2FA enable/disable/verify events are logged for security monitoring' },
    ]
  },
  {
    version: 'v4.0.0',
    date: '2026-02-02',
    title: 'User Hierarchy & Client Mapping Overhaul',
    changes: [
      { type: 'feature', description: 'Multi-Level User Hierarchy - Employee → Manager → Zonal Head → Regional Manager → Business Head' },
      { type: 'feature', description: 'Hierarchical Data Visibility - Managers can view all subordinates\' clients and bookings' },
      { type: 'feature', description: 'Edit Restrictions - Users can only edit their own data, managers have view-only access to subordinate data' },
      { type: 'feature', description: 'Auto-Map Clients to Creator - New clients are automatically mapped to the user who creates them' },
      { type: 'feature', description: 'Cloned Client/Vendor Tag - Visual indicator showing when a client or vendor was cloned' },
      { type: 'feature', description: 'System User Protection - Prevents creating clients with PAN/email matching existing system users' },
      { type: 'feature', description: 'Mapped Employee Email for CC - Mapped employee receives CC on all client communications' },
      { type: 'feature', description: 'PAN Column in User Management - Users table now displays PAN numbers' },
      { type: 'feature', description: 'Team Hierarchy Tab - Visual organization structure in User Management' },
      { type: 'feature', description: 'Circular Reference Prevention - Prevents creating loops in reporting structure' },
      { type: 'improvement', description: 'Removed Own Account Booking option from booking form' },
      { type: 'security', description: 'PE Desk only can assign clients to employees' },
    ]
  },
  {
    version: 'v3.0.0',
    date: '2026-02-01',
    title: 'Inventory Overhaul & Documentation',
    changes: [
      { type: 'feature', description: 'Landing Price (LP) - New price field visible to all users for booking calculations' },
      { type: 'feature', description: 'Weighted Average Price (WAP) - Hidden from users, visible only to PE Desk' },
      { type: 'feature', description: 'PE Desk HIT Report - Track margin between LP and WAP across all transactions' },
      { type: 'feature', description: 'Persistent File Storage - Documents migrated to MongoDB GridFS (survives redeployment)' },
      { type: 'feature', description: 'File Migration Admin Page - Re-upload missing files from legacy storage' },
      { type: 'feature', description: 'In-App Help & Tutorial - Comprehensive documentation accessible from main menu' },
      { type: 'feature', description: 'Unified Menu View - Desktop menu matches mobile grid layout' },
      { type: 'feature', description: 'Launch Documentation Package - Employee tutorial and quick reference guides' },
      { type: 'fix', description: 'Conflicting Inventory API Route - Resolved endpoint override issue' },
      { type: 'fix', description: 'Booking Creation DuplicateKeyError - Fixed database counter issue' },
    ]
  },
  {
    version: 'v2.0.1',
    date: '2026-02-01',
    title: 'Notification System Overhaul & Finance Enhancements',
    changes: [
      { type: 'feature', description: 'Notification Sound System - Browser permission request for audio playback' },
      { type: 'feature', description: 'Sound Toggle - Enable/disable notification sounds from notification bell' },
      { type: 'feature', description: 'Browser Notifications - Native browser notification support with permission request' },
      { type: 'feature', description: 'TCS FY Selector - Export TCS reports for any financial year (current + 5 previous years)' },
      { type: 'feature', description: 'Permission Banner - Prompts new users to enable notifications on first login' },
      { type: 'improvement', description: 'Audio Context Management - Singleton audio context for reliable sound playback' },
      { type: 'improvement', description: 'Notification Bell UI - Added sound toggle, test button, and enable permissions button' },
      { type: 'fix', description: 'Mobile Sidebar - Verified working correctly with all 27 menu items accessible' },
      { type: 'fix', description: 'Duplicate Notifications - Prevented same notification from appearing twice' },
      { type: 'fix', description: 'WebSocket Sound - Re-enabled sound for WebSocket notifications' },
    ]
  },
  {
    version: 'v1.2.0',
    date: '2026-01-31',
    title: 'Stable Release - Role Hierarchy & Finance Updates',
    changes: [
      { type: 'feature', description: 'New Roles: Regional Manager and Business Head added to hierarchy' },
      { type: 'feature', description: 'Viewer Role Enhanced - Full view access to all modules (no create/edit/delete/download)' },
      { type: 'feature', description: 'Employee Commissions - New tab in Finance page to track and pay commissions' },
      { type: 'feature', description: 'CML OCR Fix - Now extracts primary account holder name correctly (not father\'s name)' },
      { type: 'feature', description: 'PE Manager Stock Access - Create, edit stocks and corporate actions' },
      { type: 'feature', description: 'Proprietor Workflow - Simplified creation without mandatory bank declaration' },
      { type: 'improvement', description: 'Version stability - No more auto-reset on deployment' },
      { type: 'fix', description: 'Name mismatch bypass when proprietor is selected' },
    ]
  },
  {
    version: 'v1.1.0',
    date: '2026-01-30',
    title: 'Research Center & Mobile Enhancements',
    changes: [
      { type: 'feature', description: 'Research Center - AI-powered stock research assistant and report management' },
      { type: 'feature', description: 'Proprietorship Workflow - Name mismatch detection with Bank Declaration upload' },
      { type: 'feature', description: 'PE Manager Vendor Access - Create and edit vendors (without delete)' },
      { type: 'feature', description: 'Page Caching - Faster load times for Dashboard, Stocks, Clients' },
      { type: 'improvement', description: 'Mobile Responsiveness - Bottom sheet dialogs on mobile devices' },
      { type: 'improvement', description: 'Simplified Notifications - Reduced intrusive sounds and popups' },
      { type: 'improvement', description: 'Code Refactoring - Email templates extracted, hooks centralized' },
      { type: 'fix', description: 'Route Order Bug - Fixed pending-approval endpoints returning 404' },
      { type: 'fix', description: 'Vendor Creation - Made DP ID optional for vendors' },
      { type: 'fix', description: 'Vendor Update - Fixed field name mismatches in update endpoint' },
      { type: 'fix', description: 'Health Endpoint - Added /health for Kubernetes probes' },
    ]
  },
  {
    version: 'v1.0.0',
    date: '2026-01-29',
    title: 'Major Release',
    changes: [
      { type: 'feature', description: 'Kill Switch - Emergency system freeze for PE Desk with 3-minute cooldown' },
      { type: 'feature', description: 'Version Control System - Automatic version tracking and display' },
      { type: 'feature', description: 'Sohini AI Assistant - In-app AI helper for user queries' },
      { type: 'feature', description: 'Audit Trail - Comprehensive activity logging with analytics' },
      { type: 'feature', description: 'Role-specific Dashboards - PE, Finance, Employee, and Client dashboards' },
      { type: 'feature', description: 'RP & Employee Revenue Dashboards - Hierarchical revenue tracking' },
      { type: 'feature', description: 'Database Backup Enhancement - Backup all collections dynamically' },
      { type: 'improvement', description: 'Resend Email functionality on Email Logs page' },
      { type: 'improvement', description: 'SMTP Test sends actual test email' },
      { type: 'fix', description: 'WebSocket 403 Forbidden error resolved' },
      { type: 'fix', description: 'SMTP configuration status display fixed' },
      { type: 'fix', description: 'Corporate Action dialog double brackets fixed' },
    ]
  },
  {
    version: 'v0.9.0',
    date: '2026-01-28',
    title: 'Business Partner & Confirmation Notes',
    changes: [
      { type: 'feature', description: 'Business Partner (BP) role with OTP-based login' },
      { type: 'feature', description: 'BP Revenue Dashboard with document verification' },
      { type: 'feature', description: 'Confirmation Notes generation with PDF and email' },
      { type: 'feature', description: 'Company Master settings page' },
      { type: 'feature', description: 'Email Audit Logging system' },
      { type: 'improvement', description: 'Mandatory client document uploads' },
      { type: 'improvement', description: 'RP document view functionality' },
      { type: 'fix', description: 'Mobile dialog responsiveness' },
    ]
  },
  {
    version: 'v0.8.0',
    date: '2026-01-27',
    title: 'Real-time Notifications & UI Overhaul',
    changes: [
      { type: 'feature', description: 'Real-time PE availability indicator' },
      { type: 'feature', description: 'WebSocket-based notifications' },
      { type: 'feature', description: 'Floating notification toasts' },
      { type: 'improvement', description: 'iOS-style UI/UX redesign' },
      { type: 'improvement', description: 'Mobile-first responsive design' },
      { type: 'improvement', description: 'Enhanced notification sounds' },
    ]
  },
  {
    version: 'v0.7.0',
    date: '2026-01-26',
    title: 'Backend Refactoring',
    changes: [
      { type: 'improvement', description: 'Modular router architecture - 92% code reduction in server.py' },
      { type: 'feature', description: 'RP approval/rejection email notifications' },
      { type: 'feature', description: 'RP bank details capture' },
      { type: 'security', description: 'Strict Client-RP separation rule enforcement' },
    ]
  },
];

export const getChangelog = () => CHANGELOG;

export const getLatestVersion = () => CHANGELOG[0]?.version || 'v1.0.0';

export default CHANGELOG;
