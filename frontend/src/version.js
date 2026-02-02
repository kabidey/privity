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
  major: 4,
  minor: 0,
  patch: 0,
  build: 0,
  timestamp: '2026-02-02T10:00:00.000Z',
  formatted: 'v4.0.0'
};

// Version getter functions
export const getVersion = () => VERSION.formatted;
export const getFullVersion = () => `v${VERSION.major}.${VERSION.minor}.${VERSION.patch}.${VERSION.build}`;
export const getVersionDetails = () => VERSION;

export default VERSION;
