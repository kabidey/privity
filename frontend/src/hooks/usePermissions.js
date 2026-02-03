import { useState, useEffect, useCallback, useMemo } from 'react';
import api from '../utils/api';

/**
 * Hook to manage user permissions based on their role
 * Fetches permissions from the roles API and provides permission checking
 */
export function usePermissions() {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Get user data synchronously for initial render
  const userData = useMemo(() => {
    try {
      const data = localStorage.getItem('user');
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }, []);

  const roleId = userData?.role || 7;
  
  // PE Desk (role 1) always has all permissions - set immediately
  const isPEDesk = roleId === 1;

  // Fetch user's role permissions
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        if (!userData) {
          setPermissions([]);
          setLoading(false);
          return;
        }

        // PE Desk (role 1) has all permissions - no API call needed
        if (isPEDesk) {
          setPermissions(['*']);
          setLoading(false);
          return;
        }

        // Fetch role permissions from API for other roles
        const response = await api.get(`/roles/${roleId}`);
        const rolePerms = response.data.permissions || [];
        setPermissions(rolePerms);
      } catch (err) {
        console.error('Failed to fetch permissions:', err);
        // Fallback to empty permissions on error
        setPermissions([]);
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchPermissions();

    // Re-fetch when user changes
    const handleStorageChange = (e) => {
      if (e.key === 'user') {
        fetchPermissions();
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [userData, roleId, isPEDesk]);

  /**
   * Check if user has a specific permission
   * @param {string} permission - Permission key (e.g., "bookings.approve")
   * @returns {boolean}
   */
  const hasPermission = useCallback((permission) => {
    if (!permission) return false;
    
    // PE Desk always has all permissions (immediate check, no async needed)
    if (isPEDesk) return true;
    
    // Wildcard all
    if (permissions.includes('*')) return true;
    
    // Category wildcard (e.g., "bookings.*")
    const category = permission.split('.')[0];
    if (permissions.includes(`${category}.*`)) return true;
    
    // Exact permission
    return permissions.includes(permission);
  }, [permissions, isPEDesk]);

  /**
   * Check if user has any of the given permissions
   * @param {string[]} permissionList - Array of permission keys
   * @returns {boolean}
   */
  const hasAnyPermission = useCallback((permissionList) => {
    // PE Desk always has all permissions
    if (isPEDesk) return true;
    return permissionList.some(p => hasPermission(p));
  }, [hasPermission, isPEDesk]);

  /**
   * Check if user has all of the given permissions
   * @param {string[]} permissionList - Array of permission keys
   * @returns {boolean}
   */
  const hasAllPermissions = useCallback((permissionList) => {
    // PE Desk always has all permissions
    if (isPEDesk) return true;
    return permissionList.every(p => hasPermission(p));
  }, [hasPermission, isPEDesk]);

  /**
   * Check if user can access a specific menu/feature
   * Maps menu items to their required permissions
   */
  const canAccess = useCallback((feature) => {
    // PE Desk always has access to everything
    if (isPEDesk) return true;
    
    const featurePermissions = {
      // Dashboard
      'dashboard': ['dashboard.view'],
      'pe-dashboard': ['dashboard.pe_view'],
      
      // Core features
      'bookings': ['bookings.view'],
      'clients': ['clients.view'],
      'stocks': ['stocks.view'],
      'inventory': ['inventory.view'],
      'purchases': ['purchases.view'],
      'vendors': ['vendors.view'],
      
      // Finance & Reports
      'finance': ['finance.view'],
      'reports': ['reports.view'],
      'analytics': ['analytics.view'],
      'contract-notes': ['contract_notes.view'],
      
      // User Management
      'users': ['users.view'],
      'roles': ['roles.view'],
      
      // Partners
      'business-partners': ['business_partners.view'],
      'referral-partners': ['referral_partners.view'],
      
      // Email & Communication
      'email-templates': ['email.view_templates'],
      'email-logs': ['email.view_logs'],
      'email-server': ['email.server_config'],
      
      // Security & Admin
      'audit-trail': ['security.view_audit'],
      'security': ['security.view_dashboard'],
      'company-master': ['company.view'],
      'database-backup': ['database.view_backups'],
      'bulk-upload': ['bulk_upload.clients', 'bulk_upload.stocks'],
      
      // DP Operations
      'dp-receivables': ['dp.view_receivables'],
      'dp-transfer': ['dp.transfer'],
      
      // Research
      'research': ['research.view'],
    };

    const required = featurePermissions[feature];
    if (!required) return true; // Default allow if not configured
    
    return hasAnyPermission(required);
  }, [hasAnyPermission]);

  return {
    permissions,
    loading,
    error,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    canAccess,
  };
}

export default usePermissions;
