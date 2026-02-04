import { useState, useEffect } from 'react';
import {
  ROLE_IDS,
  ROLE_NAMES,
  getRoleName,
  isPELevel as checkIsPELevel,
  isPEDesk as checkIsPEDesk,
  isPEManager as checkIsPEManager,
  isFinance as checkIsFinance,
  isViewer as checkIsViewer,
  isPartnersDesk as checkIsPartnersDesk,
  isBusinessPartner as checkIsBusinessPartner,
  isEmployee as checkIsEmployee,
  canRecordPayments as checkCanRecordPayments,
  canDeletePayments as checkCanDeletePayments,
  canApproveBookings as checkCanApproveBookings,
  canEditLandingPrice as checkCanEditLandingPrice,
  canManageUsers as checkCanManageUsers,
  canDelete as checkCanDelete,
  canModify as checkCanModify,
  canDownload as checkCanDownload,
  hasFinanceAccess as checkHasFinanceAccess,
  canManageBusinessPartners as checkCanManageBusinessPartners,
  canViewAllBookings as checkCanViewAllBookings,
} from '../utils/roles';

// Re-export role constants for backward compatibility
export const ROLES = ROLE_IDS;
export { ROLE_NAMES };

/**
 * Hook to get current user info with all role checks
 * This is the primary way components should check roles
 * 
 * @example
 * const { user, isPELevel, canApproveBookings, isViewer } = useCurrentUser();
 * if (isViewer) return <ReadOnlyView />;
 * if (canApproveBookings) return <ApproveButton />;
 */
export function useCurrentUser() {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (e) {
        console.error('Failed to parse user data');
      }
    }
    
    // Listen for storage changes (e.g., login/logout in another tab)
    const handleStorageChange = (e) => {
      if (e.key === 'user') {
        if (e.newValue) {
          try {
            setUser(JSON.parse(e.newValue));
          } catch (err) {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);
  
  const role = user?.role || 7; // Default to Employee
  
  // Role checks
  const isPELevel = checkIsPELevel(role);
  const isPEDesk = checkIsPEDesk(role);
  const isPEManager = checkIsPEManager(role);
  const isFinance = checkIsFinance(role);
  const isViewer = checkIsViewer(role);
  const isPartnersDesk = checkIsPartnersDesk(role);
  const isBusinessPartner = checkIsBusinessPartner(role, user);
  const isEmployee = checkIsEmployee(role);
  
  // Permission checks
  const canRecordPayments = checkCanRecordPayments(role);
  const canDeletePayments = checkCanDeletePayments(role);
  const canApproveBookings = checkCanApproveBookings(role);
  const canEditLandingPrice = checkCanEditLandingPrice(role);
  const canManageUsers = checkCanManageUsers(role);
  const canDelete = checkCanDelete(role);
  const canModify = checkCanModify(role);
  const canDownload = checkCanDownload(role);
  const hasFinanceAccess = checkHasFinanceAccess(role);
  const canManageBusinessPartners = checkCanManageBusinessPartners(role);
  const canViewAllBookings = checkCanViewAllBookings(role);
  
  // Check if user has a specific permission
  const hasPermission = (permission) => {
    const permissions = user?.permissions || [];
    if (permissions.includes('*')) return true;
    
    const [category] = permission.split('.');
    if (permissions.includes(`${category}.*`)) return true;
    
    return permissions.includes(permission);
  };
  
  // Specific permission checks for new features
  const canViewLPChange = hasPermission('inventory.view_lp_change');
  const canViewLPHistory = hasPermission('inventory.view_lp_history');
  
  // Legacy compatibility
  const canManageVendors = isPEDesk || isPEManager;
  const canDeleteVendors = isPEDesk;
  const canUploadResearch = isPELevel;
  
  return {
    // User data
    user,
    role,
    roleName: getRoleName(role),
    
    // Role checks
    isPELevel,
    isPEDesk,
    isPEManager,
    isFinance,
    isViewer,
    isPartnersDesk,
    isBusinessPartner,
    isEmployee,
    
    // Permission checks
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
    
    // Legacy compatibility
    canManageVendors,
    canDeleteVendors,
    canUploadResearch,
  };
}

/**
 * Utility to get user synchronously (for non-hook contexts)
 * Use this in event handlers or non-React code
 * 
 * @example
 * const user = getCurrentUser();
 * if (isPEDesk(user?.role)) { ... }
 */
export function getCurrentUser() {
  const userData = localStorage.getItem('user');
  if (!userData) return null;
  try {
    return JSON.parse(userData);
  } catch (e) {
    return null;
  }
}

/**
 * Check if user has required role(s)
 * @param {number|number[]} requiredRoles - Single role ID or array of role IDs
 * @returns {boolean}
 */
export function hasRole(requiredRoles) {
  const user = getCurrentUser();
  if (!user) return false;
  if (Array.isArray(requiredRoles)) {
    return requiredRoles.includes(user.role);
  }
  return user.role === requiredRoles;
}

/**
 * Check if current user is at PE level
 * @deprecated Use useCurrentUser().isPELevel instead
 */
export function isPELevel() {
  const user = getCurrentUser();
  return checkIsPELevel(user?.role || 7);
}

export default useCurrentUser;
