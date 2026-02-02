import { useState, useEffect, useCallback } from 'react';

// Role constants - Roles are independent of hierarchy
export const ROLES = {
  PE_DESK: 1,
  PE_MANAGER: 2,
  FINANCE: 3,
  VIEWER: 4,
  PARTNERS_DESK: 5,
  BUSINESS_PARTNER: 6,
  EMPLOYEE: 7,
};

// Role names for display
export const ROLE_NAMES = {
  1: 'PE Desk',
  2: 'PE Manager',
  3: 'Finance',
  4: 'Viewer',
  5: 'Partners Desk',
  6: 'Business Partner',
  7: 'Employee',
};

// Hook to get current user info
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
  }, []);
  
  const isPELevel = user?.role === ROLES.PE_DESK || user?.role === ROLES.PE_MANAGER;
  const isPEDesk = user?.role === ROLES.PE_DESK;
  const isPEManager = user?.role === ROLES.PE_MANAGER;
  const isFinance = user?.role === ROLES.FINANCE;
  const isViewer = user?.role === ROLES.VIEWER;
  const isPartnersDesk = user?.role === ROLES.PARTNERS_DESK;
  const isBusinessPartner = user?.role === ROLES.BUSINESS_PARTNER;
  const canManageVendors = isPEDesk || isPEManager;
  const canDeleteVendors = isPEDesk;
  const canUploadResearch = isPELevel;
  
  return {
    user,
    role: user?.role,
    roleName: ROLE_NAMES[user?.role] || 'Unknown',
    isPELevel,
    isPEDesk,
    isPEManager,
    isFinance,
    isViewer,
    isPartnersDesk,
    isBusinessPartner,
    canManageVendors,
    canDeleteVendors,
    canUploadResearch,
  };
}

// Utility to get user synchronously (for non-hook contexts)
export function getCurrentUser() {
  const userData = localStorage.getItem('user');
  if (!userData) return null;
  try {
    return JSON.parse(userData);
  } catch (e) {
    return null;
  }
}

// Check if user has required role
export function hasRole(requiredRoles) {
  const user = getCurrentUser();
  if (!user) return false;
  if (Array.isArray(requiredRoles)) {
    return requiredRoles.includes(user.role);
  }
  return user.role === requiredRoles;
}

// Check if user is at PE level (roles 1-3)
export function isPELevel() {
  const user = getCurrentUser();
  return user?.role <= 3;
}

export default useCurrentUser;
