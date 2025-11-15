# Supabase Startup Fixes - Quick Reference

## What Was Fixed?

Three critical issues were resolved to ensure reliable Supabase local development:

1. **Storage Directory Missing** - Auto-created on startup
2. **Migration Ordering** - Superadmin creation now runs after all required columns exist
3. **Docker Rate Limiting** - Intelligent retry logic with exponential backoff

## Quick Start

```bash
cd backend

# Verify your setup (recommended)
./scripts/verify-supabase-setup.sh

# Start Supabase
make supabase-start

# Or start everything (Supabase + Application)
make all-up
```

## If You Have Issues

### Quick Fixes

```bash
# Most issues resolve with a restart
make supabase-stop
make supabase-start

# Nuclear option (deletes all data!)
make supabase-reset
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Storage directory missing | Auto-created, or `mkdir -p supabase/storage/books` |
| Column "account_status" error | Run `make supabase-reset` |
| Docker rate limit | Authenticate: `docker login` |
| Port already in use | `supabase stop` then try again |

## Documentation

- **[SUPABASE_TROUBLESHOOTING.md](SUPABASE_TROUBLESHOOTING.md)** - Detailed troubleshooting guide
- **[SUPABASE_STARTUP_FIXES_APPLIED.md](SUPABASE_STARTUP_FIXES_APPLIED.md)** - Complete technical details

## Verification

Run the verification script to check your setup:

```bash
./scripts/verify-supabase-setup.sh
```

This checks:
- Docker is running
- Storage directories exist
- Migrations are in correct order
- Ports are available
- Configuration is valid

## What's New?

### Enhanced Startup Script
- **Pre-flight checks** - Validates setup before starting
- **Auto-creation** - Creates missing directories automatically
- **Retry logic** - Handles Docker Hub rate limits gracefully
- **Better errors** - Clear, actionable error messages

### Migration Improvements
- **Correct ordering** - Superadmin creation runs after column creation
- **Defensive SQL** - Checks column existence before using them
- **Idempotent** - Can be re-run safely without errors
- **Dynamic** - Adapts to schema state

### Storage Infrastructure
- **Auto-created** - Storage directory created automatically
- **Git-tracked** - `.gitkeep` ensures directory exists in repository
- **Validated** - Pre-flight checks verify structure

## Success Indicators

When Supabase starts successfully:

```
✅ Supabase services started successfully!

📊 Supabase Local Services:
   Studio URL:    http://127.0.0.1:54323
   Inbucket URL:  http://127.0.0.1:54324
   API URL:       http://127.0.0.1:54321
```

You should be able to:
- ✅ Open Studio at http://127.0.0.1:54323
- ✅ See all tables in SQL Editor
- ✅ Find superadmin profile in profiles table
- ✅ Connect from your application

## Need Help?

1. Check the [Troubleshooting Guide](SUPABASE_TROUBLESHOOTING.md)
2. Run the verification script: `./scripts/verify-supabase-setup.sh`
3. Check startup script output for specific errors
4. Try the nuclear reset: `make supabase-reset`

## For Developers

### File Structure
```
backend/
├── supabase/
│   ├── storage/
│   │   └── books/
│   │       └── .gitkeep          ← NEW: Auto-created
│   ├── migrations/
│   │   ├── ...
│   │   └── 20251113080000_*.sql  ← FIXED: Reordered
│   └── config.toml
├── scripts/
│   ├── start-supabase.sh         ← ENHANCED: Retry logic
│   └── verify-supabase-setup.sh  ← NEW: Verification
├── SUPABASE_TROUBLESHOOTING.md   ← NEW: Guide
└── SUPABASE_STARTUP_FIXES_APPLIED.md  ← NEW: Details
```

### Testing Changes

```bash
# Clean slate test
make supabase-reset

# Verify migrations run cleanly
cd supabase && supabase db reset

# Check superadmin was created
supabase db execute "SELECT * FROM public.check_superadmin_users();"
```

### Contributing

When adding new migrations:
1. Use timestamps in correct sequence
2. Make them idempotent (use IF NOT EXISTS)
3. Check for column existence before using new columns
4. Test with `supabase db reset`

## Maintenance

```bash
# Weekly: Clean Docker
docker system prune -f

# Monthly: Update Supabase CLI
brew upgrade supabase  # macOS

# As needed: Reset database
make supabase-reset
```

---

**Last Updated:** November 14, 2025
**Status:** ✅ Production Ready
