/**
 * Application Version Configuration
 * 
 * This is a STATIC version file - it does NOT auto-increment.
 * To update the version, manually edit the values below.
 * 
 * Version Format: v{major}.{minor}.{patch}.{build}
 * - major: Breaking changes
 * - minor: New features
 * - patch: Bug fixes
 * - build: Internal build number
 */

const VERSION = {
  major: 7,
  minor: 2,
  patch: 2,
  build: 1,
  timestamp: '2026-02-08T08:00:00.000Z',
  formatted: 'v7.2.2.1'
};

// Version getter functions
export const getVersion = () => VERSION.formatted;
export const getFullVersion = () => `v${VERSION.major}.${VERSION.minor}.${VERSION.patch}.${VERSION.build}`;
export const getVersionDetails = () => VERSION;

// Cache busting - forces browser to reload when version changes
export const getCacheBustVersion = () => `${VERSION.major}${VERSION.minor}${VERSION.patch}${VERSION.build}`;

// Check if version changed and clear cache
export const checkVersionAndClearCache = () => {
  const storedVersion = localStorage.getItem('app_version');
  const currentVersion = VERSION.formatted;
  
  if (storedVersion && storedVersion !== currentVersion) {
    console.log(`Version changed from ${storedVersion} to ${currentVersion}. Clearing cache...`);
    
    // Clear all caches
    if ('caches' in window) {
      caches.keys().then(names => {
        names.forEach(name => {
          caches.delete(name);
        });
      });
    }
    
    // Clear localStorage except essential items
    const essentialKeys = ['token', 'user', 'theme'];
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!essentialKeys.includes(key)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
    // Update stored version
    localStorage.setItem('app_version', currentVersion);
    
    // Force reload from server
    window.location.reload(true);
    return true;
  }
  
  // Store current version if not present
  if (!storedVersion) {
    localStorage.setItem('app_version', currentVersion);
  }
  
  return false;
};

export default VERSION;
