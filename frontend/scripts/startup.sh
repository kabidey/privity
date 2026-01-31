#!/bin/bash
# Startup script for frontend - increments version before starting
cd /app/frontend
node scripts/increment-version.js
exec yarn start
