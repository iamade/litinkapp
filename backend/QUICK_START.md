# 🚀 Quick Start Guide

## First Time Setup (5 minutes)

```bash
# 1. Navigate to backend
cd backend

# 2. Start Supabase local
make supabase-start

# 3. Update environment keys (CRITICAL!)
./scripts/update-env-keys.sh

# 4. Create Docker network
docker network create litinkai_local_nw

# 5. Start application services
make dev

# 6. In another terminal, start frontend
cd ..
npm run dev
```

## Daily Development Workflow

### Morning (Start Everything)
```bash
cd backend
make all-up
```

This starts both Supabase and all application services.

### During Development

Your code auto-reloads when you make changes!

**View logs:**
```bash
make logs        # API logs only
make logs-all    # All services
```

**Access dashboards:**
- API: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323
- Mailpit: http://localhost:8025
- Flower (Celery): http://localhost:5555

### End of Day (Stop Everything)
```bash
make all-down
```

## Test Users

| Email | Password | Role |
|-------|----------|------|
| creator@litinkai.local | password123 | Creator |
| user@litinkai.local | password123 | Explorer |
| admin@litinkai.local | password123 | Admin |

## Common Issues

### "Invalid API key"
```bash
./scripts/update-env-keys.sh
make down && make dev
```

### Services won't start
```bash
make all-down
make all-up
```

### Need fresh database
```bash
make supabase-reset  # ⚠️ Deletes all data!
```

## Verify Setup

```bash
# All should return success:
curl http://localhost:8000/health
docker ps | grep litinkai
cd supabase && supabase status
```

## Need More Help?

See the full documentation:
- `SETUP_COMPLETE_NOVEMBER_2024.md` - Complete setup guide
- `README.md` - Full project documentation
- `supabase-local-setup/LOCAL_DEVELOPMENT_GUIDE.md` - Detailed local setup

## Available Make Commands

```bash
make help                # Show all commands
make supabase-start      # Start Supabase only
make supabase-stop       # Stop Supabase only
make dev                 # Start app (development mode)
make debug               # Start app (with debugger)
make down                # Stop app services
make all-up              # Start everything
make all-down            # Stop everything
make logs                # View API logs
make logs-all            # View all logs
make supabase-status     # Check Supabase status
```

---

**Ready to code? Run:** `make all-up` **and start building!** 🎉
