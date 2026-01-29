#!/usr/bin/env node
/**
 * Version Increment Script
 * Automatically increments the build number on each deployment
 * Run before build: node scripts/increment-version.js
 */

const fs = require('fs');
const path = require('path');

const versionFilePath = path.join(__dirname, '..', 'src', 'version.js');

// Read current version
let versionContent = fs.readFileSync(versionFilePath, 'utf8');

// Extract current version numbers
const majorMatch = versionContent.match(/major:\s*(\d+)/);
const minorMatch = versionContent.match(/minor:\s*(\d+)/);
const patchMatch = versionContent.match(/patch:\s*(\d+)/);
const buildMatch = versionContent.match(/build:\s*(\d+)/);

let major = majorMatch ? parseInt(majorMatch[1]) : 1;
let minor = minorMatch ? parseInt(minorMatch[1]) : 0;
let patch = patchMatch ? parseInt(patchMatch[1]) : 0;
let build = buildMatch ? parseInt(buildMatch[1]) : 0;

// Increment build number
build += 1;

// Auto-increment patch when build reaches 100
if (build >= 100) {
  build = 1;
  patch += 1;
}

// Auto-increment minor when patch reaches 100
if (patch >= 100) {
  patch = 0;
  minor += 1;
}

// Auto-increment major when minor reaches 100
if (minor >= 100) {
  minor = 0;
  major += 1;
}

const timestamp = new Date().toISOString();
const formatted = `v${major}.${minor}.${patch}`;

// Generate new version file content
const newContent = `// Auto-generated version file - DO NOT EDIT MANUALLY
// This file is automatically updated on each deployment

const VERSION = {
  major: ${major},
  minor: ${minor},
  patch: ${patch},
  build: ${build},
  timestamp: '${timestamp}',
  formatted: '${formatted}'
};

export const getVersion = () => VERSION.formatted;
export const getFullVersion = () => \`v\${VERSION.major}.\${VERSION.minor}.\${VERSION.patch}.\${VERSION.build}\`;
export const getVersionDetails = () => VERSION;

export default VERSION;
`;

// Write updated version file
fs.writeFileSync(versionFilePath, newContent);

console.log(`✅ Version updated: ${formatted} (Build ${build})`);
console.log(`   Timestamp: ${timestamp}`);
