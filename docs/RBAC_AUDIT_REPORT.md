# RBAC Endpoint Audit Report
**Generated**: Feb 05, 2026  
**Auditor**: E1 Agent  
**Status**: PARTIALLY IMPLEMENTED

## Executive Summary
Audited all 35 backend routers for permission control gaps. Identified 65+ endpoints that could benefit from granular permission controls.

## Implementation Status

### ✅ IMPLEMENTED (Phase 1-3 - Feb 05, 2026)

| Router | Endpoint | Permission Added |
|--------|----------|-----------------|
| `inventory.py` | `GET /inventory` | `inventory.view` |
| `inventory.py` | `GET /inventory/{stock_id}` | `inventory.view` |
| `inventory.py` | `GET /inventory/{stock_id}/landing-price` | `inventory.view` |
| `purchases.py` | `GET /purchases` | `purchases.view` |
| `purchases.py` | `GET /purchases/{id}/payments` | `purchases.view` |
| `purchases.py` | `GET /purchases/{id}/tcs-preview` | `purchases.view` |
| `contract_notes.py` | `GET /contract-notes/download/{id}` | `contract_notes.download` |
| `contract_notes.py` | `POST /contract-notes/preview/{id}` | `contract_notes.view` |
| `contract_notes.py` | `POST /contract-notes/send-email/{id}` | `contract_notes.send` |
| `contract_notes.py` | `GET /contract-notes/by-booking/{id}` | `contract_notes.view` |
| `contract_notes.py` | `POST /contract-notes/regenerate/{id}` | `contract_notes.generate` |
| `database_backup.py` | `POST /restore-from-file` | `database_backup.restore` |
| `files.py` | `GET /scan-missing` | `files.scan` |
| `files.py` | `POST /upload` | `files.upload` |
| `files.py` | `DELETE /{file_id}` | `files.delete` |
| `files.py` | `GET /list/{category}` | `files.view` |
| `files.py` | `GET /scan/missing` | `files.scan` |
| `referral_partners.py` | `GET /referral-partners-approved` | `referral_partners.view` |
| `dashboard.py` | `POST /unblock-ip` | `security.manage_threats` |

### ✅ NEW PERMISSIONS ADDED TO SYSTEM

```
security.view_threats     - View security threat logs and blocked IPs
security.manage_threats   - Clear/manage threat records  
files.view               - View and download uploaded files
files.view_stats         - View storage statistics
files.upload             - Upload new files to the system
files.delete             - Delete uploaded files
files.scan               - Scan for missing files and re-upload
```

## Priority Classification

### 🔴 P0 - Critical Security Gaps (Immediate Action Required)

| Router | Endpoint | Current State | Recommended Permission |
|--------|----------|---------------|------------------------|
| `security.py` | `GET /threats` | No permission check | `security.view_threats` |
| `security.py` | `GET /threats/recent` | No permission check | `security.view_threats` |
| `security.py` | `GET /threats/by-ip/{ip}` | No permission check | `security.view_threats` |
| `security.py` | `GET /threats/summary` | No permission check | `security.view_threats` |
| `security.py` | `DELETE /threats/clear` | No permission check | `security.manage_threats` |
| `files.py` | `DELETE /{file_id}` | No permission check | `files.delete` |
| `files.py` | `POST /upload` | No permission check | `files.upload` |
| `database_backup.py` | `POST /restore-from-file` | No permission check | `database_backup.restore` |
| `database_backup.py` | `POST /backups/gridfs` | No permission check | `database_backup.create` |
| `database_backup.py` | `POST /restore/gridfs` | No permission check | `database_backup.restore` |

### 🟠 P1 - High Priority (Should Fix Soon)

| Router | Endpoint | Current State | Recommended Permission |
|--------|----------|---------------|------------------------|
| `inventory.py` | `GET /` | No permission check | `inventory.view` |
| `inventory.py` | `GET /{stock_id}` | No permission check | `inventory.view` |
| `inventory.py` | `GET /{stock_id}/landing-price` | No permission check | `inventory.view` |
| `inventory.py` | `POST /recalculate` | No permission check | `inventory.recalculate` |
| `purchases.py` | `GET /` | No permission check | `purchases.view` |
| `purchases.py` | `GET /{id}/payments` | No permission check | `purchases.view` |
| `purchases.py` | `GET /{id}/tcs-preview` | No permission check | `purchases.view` |
| `contract_notes.py` | `GET /download/{note_id}` | No permission check | `contract_notes.download` |
| `contract_notes.py` | `POST /preview/{booking_id}` | No permission check | `contract_notes.view` |
| `contract_notes.py` | `POST /send-email/{note_id}` | No permission check | `contract_notes.send` |
| `contract_notes.py` | `POST /regenerate/{note_id}` | No permission check | `contract_notes.generate` |
| `contract_notes.py` | `GET /by-booking/{booking_id}` | No permission check | `contract_notes.view` |
| `users.py` | `PUT /{user_id}/assign-manager` | No permission check | `users.edit` |
| `users.py` | `GET /{user_id}/subordinates` | No permission check | `users.view` |
| `users.py` | `GET /managers-list` | No permission check | `users.view` |

### 🟡 P2 - Medium Priority (Enhancement)

| Router | Endpoint | Current State | Recommended Permission |
|--------|----------|---------------|------------------------|
| `files.py` | `GET /scan-missing` | No permission check | `files.view_stats` |
| `files.py` | `GET /{file_id}` | No permission check | `files.view` |
| `files.py` | `GET /{file_id}/download` | No permission check | `files.view` |
| `files.py` | `GET /{file_id}/info` | No permission check | `files.view` |
| `files.py` | `GET /list/{category}` | No permission check | `files.view` |
| `files.py` | `GET /scan/missing` | No permission check | `files.view_stats` |
| `files.py` | `POST /reupload/{type}/{id}` | No permission check | `files.upload` |
| `business_partners.py` | `GET /{bp_id}` | No permission check | `business_partners.view` |
| `business_partners.py` | `POST /{bp_id}/documents/{type}` | No permission check | `business_partners.edit` |
| `business_partners.py` | `GET /{bp_id}/documents` | No permission check | `business_partners.view` |
| `referral_partners.py` | `POST /{rp_id}/documents` | Has permission (edit) | OK - already protected |
| `referral_partners.py` | `GET /-approved` | No permission check | `referral_partners.view` |
| `dashboard.py` | `POST /unblock-ip` | No permission check | `security.unlock_accounts` |
| `bi_reports.py` | `GET /config` | Custom logic | Consider `reports.bi_view` |
| `bi_reports.py` | `POST /generate` | Custom logic | Report-specific permissions |

### 🟢 P3 - Low Priority / Intentionally Open

| Router | Endpoint | Reason for Low Priority |
|--------|----------|-------------------------|
| `bookings.py` | `GET /booking-confirm/{id}/{token}/accept` | Public token-based access for client confirmation |
| `bookings.py` | `POST /booking-confirm/{id}/{token}/deny` | Public token-based access for client confirmation |
| `company_master.py` | `GET /user-agreement` | Public endpoint for terms |
| `company_master.py` | `POST /accept-agreement` | User-specific action |
| `company_master.py` | `POST /decline-agreement` | User-specific action |
| `license.py` | `GET /status` | Public endpoint for license check |
| `license.py` | `GET /status/me` | User-specific action |
| `license.py` | `POST /activate` | User-specific action |
| `kill_switch.py` | `GET /status` | Need for all authenticated users |
| `users.py` | `GET /hierarchy/levels` | Reference data for all users |
| `users.py` | `GET /team/subordinates` | User-specific view |
| `users.py` | `GET /team/direct-reports` | User-specific view |
| `users.py` | `GET /hierarchy` | Reference data |
| `users.py` | `POST /heartbeat` | User activity tracking |
| `users.py` | `GET /pe-status` | Status check for all users |
| `roles.py` | `POST /check-permission` | Used by frontend for permission checks |

## New Permissions to Add

Add these to `AVAILABLE_PERMISSIONS` in `routers/roles.py`:

```python
"security": {
    "name": "Security",
    "permissions": [
        # Existing...
        {"key": "security.view_threats", "name": "View Threats", "description": "View security threat logs"},
        {"key": "security.manage_threats", "name": "Manage Threats", "description": "Clear/manage threat records"},
    ]
},
"files": {
    "name": "File Management",
    "permissions": [
        {"key": "files.view", "name": "View Files", "description": "View uploaded files"},
        {"key": "files.view_stats", "name": "View File Stats", "description": "View storage statistics"},
        {"key": "files.upload", "name": "Upload Files", "description": "Upload new files"},
        {"key": "files.delete", "name": "Delete Files", "description": "Delete uploaded files"},
    ]
}
```

## Implementation Order

1. **Phase 1**: P0 Security endpoints (security.py, database_backup.py GridFS endpoints)
2. **Phase 2**: P1 Core business endpoints (inventory.py, purchases.py, contract_notes.py)
3. **Phase 3**: P2 File and partner management endpoints
4. **Phase 4**: Review and test all changes

## Testing Strategy

After each phase:
1. Run existing pytest suite
2. Verify PE Desk retains full access
3. Verify Viewer role is properly restricted
4. Test frontend pages that use affected endpoints

## Notes

- Endpoints in `auth.py`, `two_factor.py`, `notifications.py`, `group_chat.py`, `sohini.py` are intentionally excluded as they handle user-specific authentication/session operations
- Some endpoints have custom permission logic (e.g., bi_reports checks report-specific permissions)
- Always test with both PE Desk (full access) and Viewer (restricted) roles after changes
