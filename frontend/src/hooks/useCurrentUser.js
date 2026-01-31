import { useState, useEffect, useCallback } from 'react';

// Role constants
export const ROLES = {
  PE_DESK: 1,
  PE_MANAGER: 2,
  ZONAL_MANAGER: 3,
  MANAGER: 4,
  EMPLOYEE: 5,
  VIEWER: 6,
  FINANCE: 7,
  BUSINESS_PARTNER: 8,
  PARTNERS_DESK: 9,
  REGIONAL_MANAGER: 10,
  BUSINESS_HEAD: 11,
};

// Role names for display
export const ROLE_NAMES = {
  1: 'PE Desk',
  2: 'PE Manager',
  3: 'Zonal Manager',
  4: 'Manager',
  5: 'Employee',
  6: 'Viewer',
  7: 'Finance',
  8: 'Business Partner',
  9: 'Partners Desk',
  10: 'Regional Manager',
  11: 'Business Head',
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
  
  const isPELevel = user?.role <= 3;
  const isPEDesk = user?.role === ROLES.PE_DESK;
  const isPEManager = user?.role === ROLES.PE_MANAGER;
  const isPEHead = user?.role === ROLES.PE_HEAD;
  const isManager = user?.role === ROLES.MANAGER;
  const isEmployee = user?.role === ROLES.EMPLOYEE;
  const isFinance = user?.role === ROLES.FINANCE;
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
    isPEHead,
    isManager,
    isEmployee,
    isFinance,
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
