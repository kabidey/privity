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
    version: 'v1.1.0',
    date: '2026-01-31',
    title: 'Role Hierarchy & Permissions Update',
    changes: [
      { type: 'feature', description: 'New Roles: Regional Manager and Business Head added to hierarchy' },
      { type: 'feature', description: 'Viewer Role Enhanced - Full view access to all modules (no create/edit/delete/download)' },
      { type: 'feature', description: 'CML OCR Fix - Now extracts primary account holder name correctly (not father\'s name)' },
      { type: 'feature', description: 'PE Manager Stock Access - Create, edit stocks and corporate actions' },
      { type: 'feature', description: 'Proprietor Workflow - Simplified creation without mandatory bank declaration' },
      { type: 'improvement', description: 'Version display now shows build number (v1.1.0.XX)' },
      { type: 'improvement', description: 'Changelog now shows on each new build deployment' },
      { type: 'fix', description: 'Name mismatch bypass when proprietor is selected' },
    ]
  },
  {
    version: 'v1.1.0-prev',
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
    title: 'Business Partner & Contract Notes',
    changes: [
      { type: 'feature', description: 'Business Partner (BP) role with OTP-based login' },
      { type: 'feature', description: 'BP Revenue Dashboard with document verification' },
      { type: 'feature', description: 'Contract Notes generation with PDF and email' },
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
