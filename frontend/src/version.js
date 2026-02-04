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
  major: 6,
  minor: 2,
  patch: 4,
  build: 7,
  timestamp: '2026-02-04T16:00:00.000Z',
  formatted: 'v6.2.4.7'
};

// Version getter functions
export const getVersion = () => VERSION.formatted;
export const getFullVersion = () => `v${VERSION.major}.${VERSION.minor}.${VERSION.patch}.${VERSION.build}`;
export const getVersionDetails = () => VERSION;

export default VERSION;
