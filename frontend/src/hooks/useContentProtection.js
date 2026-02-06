import { useEffect, useCallback } from 'react';

/**
 * useContentProtection Hook
 * A lightweight hook for pages that don't use the Layout component (like Login)
 * Provides basic content protection without watermarks
 */
const useContentProtection = () => {
  // Prevent text selection (except in inputs)
  const preventSelection = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return true;
    }
    e.preventDefault();
    return false;
  }, []);

  // Prevent right-click
  const preventContextMenu = useCallback((e) => {
    e.preventDefault();
    return false;
  }, []);

  // Prevent keyboard shortcuts
  const preventKeyboardShortcuts = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return true;
    }

    if (e.ctrlKey || e.metaKey) {
      const blockedKeys = ['c', 'a', 'x', 'p', 's', 'u'];
      if (blockedKeys.includes(e.key.toLowerCase())) {
        e.preventDefault();
        return false;
      }
    }

    if (e.key === 'F12' || e.key === 'PrintScreen') {
      e.preventDefault();
      return false;
    }

    return true;
  }, []);

  // Prevent drag
  const preventDrag = useCallback((e) => {
    e.preventDefault();
    return false;
  }, []);

  // Prevent copy
  const preventCopy = useCallback((e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      return true;
    }
    e.preventDefault();
    return false;
  }, []);

  useEffect(() => {
    document.addEventListener('selectstart', preventSelection);
    document.addEventListener('contextmenu', preventContextMenu);
    document.addEventListener('keydown', preventKeyboardShortcuts);
    document.addEventListener('dragstart', preventDrag);
    document.addEventListener('copy', preventCopy);

    return () => {
      document.removeEventListener('selectstart', preventSelection);
      document.removeEventListener('contextmenu', preventContextMenu);
      document.removeEventListener('keydown', preventKeyboardShortcuts);
      document.removeEventListener('dragstart', preventDrag);
      document.removeEventListener('copy', preventCopy);
    };
  }, [preventSelection, preventContextMenu, preventKeyboardShortcuts, preventDrag, preventCopy]);
};

export default useContentProtection;
