import { useEffect, useState, useCallback } from 'react';
import { useCurrentUser } from '../hooks/useCurrentUser';

/**
 * ContentProtection Component
 * Provides comprehensive content protection against:
 * - Text selection and copying
 * - Right-click context menu
 * - Keyboard shortcuts (Ctrl+C, Ctrl+A, Ctrl+P, PrintScreen, etc.)
 * - Drag and drop
 * - Developer tools detection
 * - Tab visibility/focus changes (blur content)
 */
const ContentProtection = ({ children }) => {
  const { user } = useCurrentUser();
  const [isBlurred, setIsBlurred] = useState(false);
  const [devToolsOpen, setDevToolsOpen] = useState(false);

  // Detect Developer Tools
  const detectDevTools = useCallback(() => {
    const threshold = 160;
    const widthThreshold = window.outerWidth - window.innerWidth > threshold;
    const heightThreshold = window.outerHeight - window.innerHeight > threshold;
    
    // Check if devtools is likely open based on window size difference
    if (widthThreshold || heightThreshold) {
      setDevToolsOpen(true);
    } else {
      setDevToolsOpen(false);
    }
  }, []);

  useEffect(() => {
    // ========== PREVENT TEXT SELECTION ==========
    const preventSelection = (e) => {
      // Allow selection in input fields and textareas for usability
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return true;
      }
      e.preventDefault();
      return false;
    };

    // ========== PREVENT RIGHT-CLICK CONTEXT MENU ==========
    const preventContextMenu = (e) => {
      e.preventDefault();
      return false;
    };

    // ========== PREVENT KEYBOARD SHORTCUTS ==========
    const preventKeyboardShortcuts = (e) => {
      // Allow typing in input fields
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        // But still block copy/paste shortcuts in inputs
        if ((e.ctrlKey || e.metaKey) && ['c', 'a', 'x'].includes(e.key.toLowerCase())) {
          // Allow copy/paste in password fields for usability
          if (e.target.type === 'password') return true;
        }
      }

      // Block common shortcuts
      if (e.ctrlKey || e.metaKey) {
        const blockedKeys = [
          'c', // Copy
          'a', // Select All
          'x', // Cut
          'p', // Print
          's', // Save
          'u', // View Source
          'shift+i', // Dev Tools
          'shift+j', // Console
          'shift+c', // Inspector
        ];

        const keyCombo = e.shiftKey ? `shift+${e.key.toLowerCase()}` : e.key.toLowerCase();
        
        if (blockedKeys.includes(keyCombo)) {
          e.preventDefault();
          return false;
        }
      }

      // Block F12 (Dev Tools)
      if (e.key === 'F12') {
        e.preventDefault();
        return false;
      }

      // Block PrintScreen
      if (e.key === 'PrintScreen') {
        e.preventDefault();
        // Blur content briefly when PrintScreen is pressed
        setIsBlurred(true);
        setTimeout(() => setIsBlurred(false), 1500);
        return false;
      }

      return true;
    };

    // ========== PREVENT DRAG AND DROP ==========
    const preventDragDrop = (e) => {
      e.preventDefault();
      return false;
    };

    // ========== VISIBILITY CHANGE DETECTION ==========
    const handleVisibilityChange = () => {
      if (document.hidden) {
        setIsBlurred(true);
      } else {
        // Small delay before unblurring to catch screenshot attempts
        setTimeout(() => setIsBlurred(false), 300);
      }
    };

    // ========== FOCUS/BLUR DETECTION ==========
    const handleWindowBlur = () => {
      setIsBlurred(true);
    };

    const handleWindowFocus = () => {
      setTimeout(() => setIsBlurred(false), 200);
    };

    // ========== DEV TOOLS DETECTION ==========
    const devToolsChecker = setInterval(detectDevTools, 1000);
    detectDevTools(); // Initial check

    // ========== COPY EVENT PREVENTION ==========
    const preventCopy = (e) => {
      e.preventDefault();
      // Optionally set clipboard to empty or warning message
      if (e.clipboardData) {
        e.clipboardData.setData('text/plain', '');
      }
      return false;
    };

    // ========== CUT EVENT PREVENTION ==========
    const preventCut = (e) => {
      e.preventDefault();
      return false;
    };

    // ========== PASTE EVENT (allow for inputs) ==========
    const handlePaste = (e) => {
      // Allow paste only in form inputs
      if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        return false;
      }
      return true;
    };

    // Add all event listeners
    document.addEventListener('selectstart', preventSelection);
    document.addEventListener('contextmenu', preventContextMenu);
    document.addEventListener('keydown', preventKeyboardShortcuts);
    document.addEventListener('dragstart', preventDragDrop);
    document.addEventListener('drop', preventDragDrop);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('copy', preventCopy);
    document.addEventListener('cut', preventCut);
    document.addEventListener('paste', handlePaste);
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('focus', handleWindowFocus);

    // Cleanup
    return () => {
      document.removeEventListener('selectstart', preventSelection);
      document.removeEventListener('contextmenu', preventContextMenu);
      document.removeEventListener('keydown', preventKeyboardShortcuts);
      document.removeEventListener('dragstart', preventDragDrop);
      document.removeEventListener('drop', preventDragDrop);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('copy', preventCopy);
      document.removeEventListener('cut', preventCut);
      document.removeEventListener('paste', handlePaste);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('focus', handleWindowFocus);
      clearInterval(devToolsChecker);
    };
  }, [detectDevTools]);

  return (
    <div className="content-protection-wrapper">
      {/* Main content with protection styles */}
      <div 
        className={`protected-content ${isBlurred ? 'content-blurred' : ''} ${devToolsOpen ? 'devtools-warning' : ''}`}
        style={{
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none',
          WebkitTouchCallout: 'none',
        }}
      >
        {children}
      </div>

      {/* Blur overlay when tab is not focused or devtools detected */}
      {(isBlurred || devToolsOpen) && (
        <div className="content-protection-overlay">
          <div className="protection-message">
            <div className="protection-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
            <h3>Content Protected</h3>
            <p>
              {devToolsOpen 
                ? 'Developer tools detected. Please close to view content.'
                : 'Please return to the application to view content.'}
            </p>
          </div>
        </div>
      )}

      {/* Watermark overlay with user identification */}
      {user && (
        <div className="watermark-overlay" aria-hidden="true">
          <div className="watermark-pattern">
            {Array.from({ length: 20 }).map((_, i) => (
              <span key={i} className="watermark-text">
                {user.email} | {new Date().toLocaleDateString()}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ContentProtection;
