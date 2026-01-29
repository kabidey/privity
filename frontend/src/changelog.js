// Changelog data - Add new entries at the top
// Format: { version, date, changes: [{ type, description }] }
// Types: 'feature', 'fix', 'improvement', 'security'

const CHANGELOG = [
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

export const getVersionChanges = (version) => {
  return CHANGELOG.find(entry => entry.version === version);
};

export const getChangesSinceVersion = (lastSeenVersion) => {
  const lastIndex = CHANGELOG.findIndex(entry => entry.version === lastSeenVersion);
  if (lastIndex === -1) return CHANGELOG; // Show all if version not found
  if (lastIndex === 0) return []; // No new changes
  return CHANGELOG.slice(0, lastIndex);
};

export default CHANGELOG;
