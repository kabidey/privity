import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useCurrentUser } from './useCurrentUser';

/**
 * Hook to protect pages with role/permission-based access control
 * Handles the loading state, permission validation, and unauthorized redirect
 * 
 * @param {Object} options - Protection options
 * @param {Function} [options.allowIf] - Custom function to check access (receives currentUser hook result)
 * @param {string} [options.deniedMessage] - Custom message to show when access is denied
 * @param {string} [options.redirectTo='/'] - Path to redirect unauthorized users
 * 
 * @returns {Object} { isLoading, isAuthorized, ...currentUser }
 * 
 * @example
 * // Protect page for PE Level users only
 * const { isLoading, isAuthorized, isPELevel } = useProtectedPage({
 *   allowIf: ({ isPELevel }) => isPELevel,
 *   deniedMessage: 'Only PE Desk or PE Manager can access this page.'
 * });
 * 
 * @example
 * // Protect with custom permission check
 * const { isLoading, isAuthorized } = useProtectedPage({
 *   allowIf: ({ hasPermission }) => hasPermission('audit.view'),
 *   deniedMessage: 'You do not have permission to view audit logs.'
 * });
 * 
 * @example
 * // Protect with multiple conditions
 * const { isLoading, isAuthorized } = useProtectedPage({
 *   allowIf: ({ isPELevel, canManageBusinessPartners }) => isPELevel || canManageBusinessPartners,
 *   deniedMessage: 'Access denied.'
 * });
 */
export function useProtectedPage({
  allowIf,
  deniedMessage = 'Access denied. You do not have permission to view this page.',
  redirectTo = '/'
} = {}) {
  const navigate = useNavigate();
  const currentUser = useCurrentUser();
  const { user } = currentUser;
  
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [hasChecked, setHasChecked] = useState(false);
  
  // Determine if still loading (user data not yet available)
  const isLoading = user === null;
  
  useEffect(() => {
    // Don't check permissions until user data is loaded
    if (user === null) return;
    
    // If no allowIf function provided, allow access by default
    if (!allowIf) {
      setIsAuthorized(true);
      setHasChecked(true);
      return;
    }
    
    // Run the permission check
    const allowed = allowIf(currentUser);
    
    if (!allowed) {
      toast.error(deniedMessage);
      navigate(redirectTo);
      setIsAuthorized(false);
    } else {
      setIsAuthorized(true);
    }
    
    setHasChecked(true);
  }, [user, allowIf, deniedMessage, redirectTo, navigate, currentUser]);
  
  return {
    isLoading,
    isAuthorized,
    hasChecked,
    ...currentUser
  };
}

export default useProtectedPage;
