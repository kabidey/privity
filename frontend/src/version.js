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
  major: 2,
  minor: 0,
  patch: 1,
  build: 1,
  timestamp: '2026-02-01T14:00:00.000Z',
  formatted: 'v2.0.1'
};

// Version getter functions
export const getVersion = () => VERSION.formatted;
export const getFullVersion = () => `v${VERSION.major}.${VERSION.minor}.${VERSION.patch}.${VERSION.build}`;
export const getVersionDetails = () => VERSION;

export default VERSION;
