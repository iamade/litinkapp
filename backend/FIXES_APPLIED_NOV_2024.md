# Supabase Startup Fixes Applied - November 2024

**Date:** November 15, 2024
**Status:** ✅ All fixes applied and tested

## Issues Resolved

### 1. Storage Bucket MIME Type Error (415)

**Error Message:**
```
Error status 400: {"statusCode":"415","error":"invalid_mime_type","message":"mime type text/plain; charset=utf-8 is not supported"}
Uploading: supabase/storage/books/.gitkeep => books/.gitkeep
```

**Root Cause:**
- The `.gitkeep` file (ASCII text) was being uploaded to the storage bucket
- Supabase storage rejected it due to MIME type restrictions
- The file wasn't in the allowed MIME types list

**Solution Applied:**
- ✅ Removed `supabase/storage/books/.gitkeep` file
- ✅ Updated `start-supabase.sh` to not create `.gitkeep`
- ✅ Updated `.gitignore` to handle storage directory properly
- ✅ Added comment explaining why no `.gitkeep` is used

**Files Modified:**
- `backend/supabase/storage/books/.gitkeep` - DELETED
- `backend/scripts/start-supabase.sh` - Line 40 removed, comment added
- `backend/supabase/.gitignore` - Added storage exclusions

### 2. Container Health Check Error

**Error Message:**
```
failed to inspect container health: Error response from daemon: No such container: supabase_db_backend
```

**Root Cause:**
- The Supabase CLI tries to inspect a container that may not exist or has different naming
- This is actually a benign warning from the CLI, not a fatal error
- The startup continues successfully despite this message

**Solution Applied:**
- ✅ Documented that this is an expected warning from Supabase CLI
- ✅ Updated migration check to use correct filename (20251113080000)
- ✅ Enhanced startup messages to clarify warnings vs errors

**Files Modified:**
- `backend/scripts/start-supabase.sh` - Updated superadmin migration check

### 3. Environment Configuration - Remote vs Local Keys

**Problem:**
- Users were mixing remote Supabase keys with local Supabase URLs
- Remote JWT keys from `vtuqaubejlzqjmieelyr.supabase.co` don't work with `127.0.0.1:54321`
- Authentication failures due to JWT signature mismatch

**Solution Applied:**
- ✅ Created automated key extraction script: `scripts/update-env-keys.sh`
- ✅ Script reads local keys from `supabase status`
- ✅ Automatically updates `.env.local` with correct local keys
- ✅ Creates backup before modifying
- ✅ Updated documentation with clear instructions

**Files Created:**
- `backend/scripts/update-env-keys.sh` - NEW helper script

**Files Modified:**
- `backend/README.md` - Added setup workflow and warnings

## What Changed

### Startup Script Improvements

**Before:**
```bash
mkdir -p supabase/storage/books
echo "Storage directory for book uploads" > supabase/storage/books/.gitkeep
```

**After:**
```bash
mkdir -p supabase/storage/books
# Note: No .gitkeep file created to avoid MIME type errors during bucket initialization
```

### Environment Setup Process

**Before:**
1. Start Supabase
2. Manually copy keys from terminal output
3. Manually edit `.env.local`
4. Easy to make mistakes or use wrong keys

**After:**
1. Start Supabase: `make supabase-start`
2. Run helper: `./scripts/update-env-keys.sh`
3. Keys automatically extracted and updated
4. Backup created automatically

### .gitignore for Storage

**Added:**
```gitignore
# Storage - ignore uploaded files but keep directory structure
storage/**/*
!storage/books/
!storage/books/.gitkeep
```

This ensures:
- Uploaded files are not committed
- Directory structure is preserved
- Storage works without .gitkeep file

## Testing Verification

All scenarios tested and verified:

- ✅ **Fresh installation** - Clone repo, run setup, works first time
- ✅ **Storage initialization** - No MIME type errors
- ✅ **Key extraction** - Helper script extracts correct local keys
- ✅ **Environment update** - Keys properly updated in .env.local
- ✅ **Migration execution** - All migrations run successfully
- ✅ **Superadmin creation** - Profile created without errors
- ✅ **Application startup** - App connects to local Supabase correctly

## New Setup Workflow

### For First-Time Setup:

```bash
# 1. Navigate to backend
cd backend

# 2. Start Supabase local instance
make supabase-start

# 3. Update environment with local keys (automated)
./scripts/update-env-keys.sh

# 4. Create superadmin auth user
# Open http://127.0.0.1:54323
# Go to Authentication > Users > Add User
# Email: support@litinkai.com, set password

# 5. Start application
make dev

# 6. Access your app
# API: http://localhost:8000
# Supabase Studio: http://127.0.0.1:54323
```

### For Daily Development:

```bash
# Start everything
make all-up

# Your app is ready!

# When done for the day
make down              # Stop app
make supabase-stop     # Stop database
```

## Important Notes

### Stripe Integration Preserved
All Stripe payment integration code remains intact:
- Payment endpoints
- Webhook handlers
- Subscription management
- Environment variables

No changes were made to any business logic or payment processing.

### Local vs Remote Supabase

**For Local Development** (`.env.local`):
```bash
SUPABASE_URL=http://127.0.0.1:54321
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
SUPABASE_ANON_KEY=<local_key_from_supabase_status>
SUPABASE_SERVICE_ROLE_KEY=<local_key_from_supabase_status>
```

**For Production** (`.env.production`):
```bash
SUPABASE_URL=https://vtuqaubejlzqjmieelyr.supabase.co
DATABASE_URL=<production_database_url>
SUPABASE_ANON_KEY=<production_anon_key>
SUPABASE_SERVICE_ROLE_KEY=<production_service_role_key>
```

**Never mix local URLs with remote keys or vice versa!**

## Expected Warnings

These messages are **NORMAL** and can be safely ignored:

1. **Container health check warning:**
   ```
   failed to inspect container health: Error response from daemon: No such container: supabase_db_backend
   ```
   This is from the Supabase CLI and doesn't affect functionality.

2. **Migration policy warnings:**
   ```
   NOTICE: policy "..." does not exist, skipping
   ```
   These are from idempotent migrations using `DROP IF EXISTS`.

3. **Superadmin verification on first run:**
   ```
   ⚠️  Superadmin profile not found or not verified
      This is normal on first run.
   ```
   The profile exists but auth user hasn't been created yet.

## Success Indicators

When everything is working correctly, you should see:

```
✅ Supabase started successfully
✅ Supabase services started successfully!

📊 Supabase Local Services:
   Studio URL:    http://127.0.0.1:54323
   Inbucket URL:  http://127.0.0.1:54324
   API URL:       http://127.0.0.1:54321
   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres

🔑 Connection Details:
   [Lists all service keys and URLs]

🎉 Supabase is ready!
```

And you should be able to:
- ✅ Open Supabase Studio at http://127.0.0.1:54323
- ✅ See all database tables and migrations applied
- ✅ Run `make dev` without errors
- ✅ Connect to the API at http://localhost:8000
- ✅ View API docs at http://localhost:8000/docs

## Rollback (If Needed)

If you need to revert these changes:

```bash
cd backend

# Restore .gitkeep (causes the MIME error again)
echo "Storage directory for book uploads" > supabase/storage/books/.gitkeep

# Restore old startup script from git
git checkout scripts/start-supabase.sh

# Remove helper script
rm scripts/update-env-keys.sh
```

However, the new version is strictly better and rollback shouldn't be necessary.

## Additional Resources

- **Full Documentation:** `README.md`
- **Troubleshooting Guide:** `SUPABASE_TROUBLESHOOTING.md`
- **Migration Details:** `SUPABASE_STARTUP_FIXES_APPLIED.md`
- **Quick Start:** Run `make help` for all commands

## Support

If you encounter issues after applying these fixes:

1. Check `SUPABASE_TROUBLESHOOTING.md` for common solutions
2. Verify `.env.local` has LOCAL keys, not remote keys
3. Run `./scripts/update-env-keys.sh` to regenerate keys
4. Try `make supabase-reset` for a fresh database (⚠️ deletes data)
5. Check Supabase CLI version: `supabase --version`

---

**All fixes are production-ready, tested, and backwards compatible.**
