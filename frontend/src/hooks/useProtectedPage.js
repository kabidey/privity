import { useEffect, useRef } from 'react';
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
  const hasRedirected = useRef(false);
  
  // Determine if still loading (user data not yet available)
  const isLoading = user === null;
  
  // Compute authorization synchronously (no setState needed)
  let isAuthorized = false;
  if (user !== null) {
    if (!allowIf) {
      // If no allowIf function provided, allow access by default
      isAuthorized = true;
    } else {
      isAuthorized = allowIf(currentUser);
    }
  }
  
  // Handle redirect for unauthorized users (side effect)
  useEffect(() => {
    // Don't redirect until user data is loaded
    if (user === null) return;
    // Don't redirect if already authorized
    if (isAuthorized) return;
    // Don't redirect multiple times
    if (hasRedirected.current) return;
    
    hasRedirected.current = true;
    toast.error(deniedMessage);
    navigate(redirectTo);
  }, [user, isAuthorized, deniedMessage, redirectTo, navigate]);
  
  return {
    isLoading,
    isAuthorized,
    ...currentUser
  };
}

export default useProtectedPage;
