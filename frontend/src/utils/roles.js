/**
 * Centralized Role Utility
 * 
 * This file contains all role-related constants and helper functions.
 * Import from this file instead of defining role checks locally in components.
 * 
 * IMPORTANT: Keep this in sync with backend/config.py ROLES and ROLE_PERMISSIONS
 */

// Role IDs - must match backend/config.py
export const ROLE_IDS = {
  PE_DESK: 1,
  PE_MANAGER: 2,
  FINANCE: 3,
  VIEWER: 4,
  PARTNERS_DESK: 5,
  BUSINESS_PARTNER: 6,
  EMPLOYEE: 7,
};

// Role Names - must match backend/config.py
export const ROLE_NAMES = {
  1: "PE Desk",
  2: "PE Manager",
  3: "Finance",
  4: "Viewer",
  5: "Partners Desk",
  6: "Business Partner",
  7: "Employee",
};

/**
 * Get role name from role ID
 * @param {number} roleId - Role ID
 * @returns {string} Role name or "Unknown"
 */
export const getRoleName = (roleId) => {
  return ROLE_NAMES[roleId] || "Unknown";
};

/**
 * Check if role is PE level (PE Desk or PE Manager)
 * PE level users have elevated access to approve bookings, manage users, etc.
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isPELevel = (role) => {
  return role === ROLE_IDS.PE_DESK || role === ROLE_IDS.PE_MANAGER;
};

/**
 * Check if role is PE Desk only (highest privilege)
 * PE Desk has full access including deletions and database management
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isPEDesk = (role) => {
  return role === ROLE_IDS.PE_DESK;
};

/**
 * Check if role is PE Manager
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isPEManager = (role) => {
  return role === ROLE_IDS.PE_MANAGER;
};

/**
 * Check if role is Finance
 * Finance users have access to payment management and finance reports
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isFinance = (role) => {
  return role === ROLE_IDS.FINANCE;
};

/**
 * Check if role is Viewer (read-only)
 * Viewers can see everything but cannot create, edit, delete, or download
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isViewer = (role) => {
  return role === ROLE_IDS.VIEWER;
};

/**
 * Check if role is Partners Desk
 * Partners Desk manages Business Partners
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isPartnersDesk = (role) => {
  return role === ROLE_IDS.PARTNERS_DESK;
};

/**
 * Check if role is Business Partner
 * @param {number} role - Role ID
 * @param {Object} user - Optional user object to check is_bp flag
 * @returns {boolean}
 */
export const isBusinessPartner = (role, user = null) => {
  return role === ROLE_IDS.BUSINESS_PARTNER || (user && user.is_bp);
};

/**
 * Check if role is Employee
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const isEmployee = (role) => {
  return role === ROLE_IDS.EMPLOYEE;
};

/**
 * Check if user can record payments
 * Only PE Level users can record payments
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canRecordPayments = (role) => {
  return isPELevel(role);
};

/**
 * Check if user can delete payments
 * Only PE Level users can delete payments
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canDeletePayments = (role) => {
  return isPELevel(role);
};

/**
 * Check if user can approve bookings
 * Only PE Level users can approve bookings
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canApproveBookings = (role) => {
  return isPELevel(role);
};

/**
 * Check if user can edit landing price
 * Only PE Level users can edit landing price
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canEditLandingPrice = (role) => {
  return isPELevel(role);
};

/**
 * Check if user can manage users
 * Only PE Level users can manage users
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canManageUsers = (role) => {
  return isPELevel(role);
};

/**
 * Check if user can delete records
 * Only PE Desk can delete records
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canDelete = (role) => {
  return isPEDesk(role);
};

/**
 * Check if user can create/edit records (not a viewer)
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canModify = (role) => {
  return !isViewer(role);
};

/**
 * Check if user can download/export data
 * Viewers cannot download
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canDownload = (role) => {
  return !isViewer(role);
};

/**
 * Check if user has access to Finance page
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const hasFinanceAccess = (role) => {
  return isPELevel(role) || isFinance(role);
};

/**
 * Check if user can manage Business Partners
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canManageBusinessPartners = (role) => {
  return isPELevel(role) || isPartnersDesk(role);
};

/**
 * Check if user can view all bookings (not just their own)
 * @param {number} role - Role ID
 * @returns {boolean}
 */
export const canViewAllBookings = (role) => {
  return isPELevel(role) || isFinance(role) || isViewer(role) || isPartnersDesk(role);
};

/**
 * Get all role checks for a user in one object
 * Useful for components that need multiple role checks
 * @param {Object} user - User object from localStorage
 * @returns {Object} Object with all role boolean flags
 */
export const getUserRoleFlags = (user) => {
  const role = user?.role || 7; // Default to Employee
  
  return {
    role,
    roleName: getRoleName(role),
    isPEDesk: isPEDesk(role),
    isPEManager: isPEManager(role),
    isPELevel: isPELevel(role),
    isFinance: isFinance(role),
    isViewer: isViewer(role),
    isPartnersDesk: isPartnersDesk(role),
    isBusinessPartner: isBusinessPartner(role, user),
    isEmployee: isEmployee(role),
    canRecordPayments: canRecordPayments(role),
    canDeletePayments: canDeletePayments(role),
    canApproveBookings: canApproveBookings(role),
    canEditLandingPrice: canEditLandingPrice(role),
    canManageUsers: canManageUsers(role),
    canDelete: canDelete(role),
    canModify: canModify(role),
    canDownload: canDownload(role),
    hasFinanceAccess: hasFinanceAccess(role),
    canManageBusinessPartners: canManageBusinessPartners(role),
    canViewAllBookings: canViewAllBookings(role),
  };
};

export default {
  ROLE_IDS,
  ROLE_NAMES,
  getRoleName,
  isPELevel,
  isPEDesk,
  isPEManager,
  isFinance,
  isViewer,
  isPartnersDesk,
  isBusinessPartner,
  isEmployee,
  canRecordPayments,
  canDeletePayments,
  canApproveBookings,
  canEditLandingPrice,
  canManageUsers,
  canDelete,
  canModify,
  canDownload,
  hasFinanceAccess,
  canManageBusinessPartners,
  canViewAllBookings,
  getUserRoleFlags,
};
