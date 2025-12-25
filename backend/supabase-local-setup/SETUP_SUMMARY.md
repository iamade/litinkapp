# Local Supabase Setup - Summary

## What Was Configured

Your Litinkai backend now has a complete local development environment with Supabase.

### ✅ Completed Setup

1. **Supabase Local Configuration**
   - Already initialized and linked to cloud project
   - Configured with 18 existing migrations
   - Storage bucket configured for books, audio, video, images
   - Inbucket email testing enabled

2. **Environment Configuration**
   - Created `.envs/.env.local` for local development
   - Environment auto-detection in `app/core/database.py`
   - Separate configs for local vs production

3. **Seed Data**
   - 5 test users with different roles and subscription tiers
   - Sample books, chapters, and characters
   - Test data for all major features

4. **Developer Scripts**
   - `start-local-dev.sh` - Start everything
   - `stop-local-dev.sh` - Stop everything
   - `reset-local-db.sh` - Reset database
   - `view-local-logs.sh` - View logs interactively

5. **Documentation**
   - `QUICK_START_LOCAL.md` - 5-minute setup guide
   - `LOCAL_DEVELOPMENT_GUIDE.md` - Complete reference
   - `scripts/README.md` - Script documentation
   - Updated main `README.md`

## Files Created/Modified

### New Files

```
backend/
├── .envs/
│   └── .env.local                      # Local environment config
├── supabase/
│   └── seed.sql                        # Test data
├── scripts/
│   ├── start-local-dev.sh              # Start all services
│   ├── stop-local-dev.sh               # Stop all services
│   ├── reset-local-db.sh               # Reset database
│   ├── view-local-logs.sh              # View logs
│   └── README.md                       # Scripts documentation
├── LOCAL_DEVELOPMENT_GUIDE.md          # Complete guide
├── QUICK_START_LOCAL.md                # Quick reference
└── SETUP_SUMMARY.md                    # This file
```

### Modified Files

```
backend/
├── supabase/
│   └── config.toml                     # Added storage bucket config
├── app/core/
│   └── database.py                     # Added environment logging
└── README.md                           # Updated with local dev info
```

## Quick Start

### First Time Setup

```bash
cd backend

# 1. Configure your API keys
cp .envs/.env.local .envs/.env.local.active
# Edit .env.local.active with your actual API keys

# 2. Start everything
./scripts/start-local-dev.sh
```

### Daily Workflow

```bash
# Start
./scripts/start-local-dev.sh

# Code...

# Stop when done
./scripts/stop-local-dev.sh
```

## Test Users

All passwords are `password123`:

| Email | Role | Subscription |
|-------|------|--------------|
| superadmin@litinkai.local | Superadmin | Enterprise |
| admin@litinkai.local | Admin | Professional |
| creator@litinkai.local | Creator | Standard |
| user@litinkai.local | User | Free |
| premium@litinkai.local | Creator | Premium |

## Service URLs

### Supabase (Port 543xx)

- **Studio**: http://127.0.0.1:54323 (Database UI)
- **API**: http://127.0.0.1:54321
- **Database**: postgresql://postgres:postgres@127.0.0.1:54322/postgres
- **Inbucket**: http://127.0.0.1:54324 (Email testing)

### Application Services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **Flower**: http://localhost:5555
- **Mailpit**: http://localhost:8025

## Environment Switching

The application automatically detects which environment to use based on `SUPABASE_URL`:

- **Local**: `http://127.0.0.1:54321` → Uses local Supabase
- **Cloud**: `https://xxx.supabase.co` → Uses cloud Supabase

You can see this in the logs:

```
INFO: Initializing Supabase client for LOCAL environment
INFO: Supabase URL: http://127.0.0.1:54321
INFO: Supabase connection established successfully (LOCAL environment)
```

## Common Tasks

### View All Services Status

```bash
# Supabase services
cd supabase && supabase status && cd ..

# Application services
docker-compose -f local.yml ps
```

### Access Database

```bash
# Via psql
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Via Supabase Studio
open http://127.0.0.1:54323
```

### Test Email Flows

1. Open http://127.0.0.1:54324
2. Trigger an email in your app
3. Check Inbucket for the email

### Debug Celery Tasks

```bash
# View worker logs
docker-compose -f local.yml logs -f celeryworker

# View in Flower
open http://localhost:5555
```

### Make Database Changes

```bash
cd supabase

# Create new migration
supabase migration new your_change_description

# Edit the generated migration file
# Then reset to apply
supabase db reset
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# Check for port conflicts
lsof -i :54321
lsof -i :8000

# Restart everything
./scripts/stop-local-dev.sh
./scripts/start-local-dev.sh
```

### Database Issues

```bash
# Reset database
./scripts/reset-local-db.sh

# Or manually
cd supabase
supabase db reset
cd ..
```

### Can't Connect to Database

1. Check Supabase is running: `cd supabase && supabase status && cd ..`
2. Verify URL in `.envs/.env.local`: `SUPABASE_URL=http://127.0.0.1:54321`
3. Check application logs: `docker-compose -f local.yml logs api`

### Emails Not Appearing

1. Check Inbucket: http://127.0.0.1:54324
2. Verify Supabase config.toml has correct settings
3. Check if email was sent: `docker-compose -f local.yml logs api | grep -i email`

## Next Steps

1. **Configure API Keys**: Edit `.envs/.env.local` with your actual API keys
2. **Start Coding**: Make changes and the API will hot-reload
3. **Test Features**: Use test users to test all functionality
4. **Create Migrations**: When changing the schema, create proper migrations
5. **Never Touch Production**: Always develop locally, never connect to prod DB

## Migration to Cloud/Production

When you're ready to push changes to production:

```bash
# 1. Test locally first
./scripts/reset-local-db.sh
# Test everything works

# 2. Push migrations to cloud
cd supabase
supabase db push

# 3. Deploy application
# (Use your normal deployment process)
```

## Benefits of This Setup

✅ **Safe Development**: Never risk production data
✅ **Fast Iteration**: No network latency
✅ **Complete Feature Parity**: All Supabase features work locally
✅ **Email Testing**: Test emails without sending real ones
✅ **Easy Reset**: Fresh start anytime with seed data
✅ **Offline Development**: Work without internet connection
✅ **Test Migrations**: Verify schema changes before production

## Support

- **Quick Reference**: [QUICK_START_LOCAL.md](QUICK_START_LOCAL.md)
- **Detailed Guide**: [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md)
- **Scripts Help**: [scripts/README.md](scripts/README.md)
- **Supabase Docs**: https://supabase.com/docs/guides/local-development

---

**You're all set for local development!** 🚀
