# Supabase Local Development Troubleshooting Guide

## Quick Fix Commands

```bash
# Most common issues can be resolved with:
cd backend
make supabase-stop
make supabase-start

# If that doesn't work, try a full reset (WARNING: deletes all data):
make supabase-reset
```

## Common Issues and Solutions

### 1. Storage Directory Missing

**Error Message:**
```
open supabase/storage/books: no such file or directory
```

**Solution:**
The storage directory is now created automatically by the startup script. If you encounter this error:

```bash
cd backend
mkdir -p supabase/storage/books
echo "Storage directory for book uploads" > supabase/storage/books/.gitkeep
make supabase-start
```

### 2. Migration Column Errors

**Error Message:**
```
ERROR: column "account_status" of relation "profiles" does not exist
```

**Solution:**
This has been fixed by reordering migrations. The superadmin creation migration now runs after all required columns are added. If you still see this:

```bash
cd backend
make supabase-reset  # This will re-run all migrations in the correct order
```

### 3. Docker Hub Rate Limiting

**Error Message:**
```
toomanyrequests: Rate exceeded
failed to pull docker image
```

**Solution:**
The startup script now includes automatic retry logic with exponential backoff. However, if rate limits persist:

**Option 1: Authenticate with Docker Hub (Recommended)**
```bash
docker login
# Enter your Docker Hub credentials
# Free accounts get higher rate limits than anonymous users
```

**Option 2: Wait and Retry**
```bash
# Docker Hub rate limits reset after 6 hours for anonymous users
# Wait 10-15 minutes and try again
make supabase-start
```

**Option 3: Use Docker Hub Pro Account**
- Docker Hub Pro accounts have much higher rate limits
- Consider upgrading if you frequently hit rate limits

### 4. Docker Not Running

**Error Message:**
```
Error: Docker is not running
```

**Solution:**
```bash
# macOS/Windows: Open Docker Desktop application
# Linux: Start Docker daemon
sudo systemctl start docker

# Verify Docker is running
docker ps

# Then try again
make supabase-start
```

### 5. Port Already in Use

**Error Message:**
```
Error: Port 54321 is already in use
```

**Solution:**
```bash
# Check what's using the ports
lsof -i :54321
lsof -i :54322
lsof -i :54323

# Stop existing Supabase instance
cd backend/supabase
supabase stop

# Or kill the process using the port
kill -9 <PID>

# Start fresh
cd ..
make supabase-start
```

### 6. Migration Already Applied Warnings

**Warning Message:**
```
NOTICE: policy "Users can view own profile" for relation "profiles" does not exist, skipping
```

**Status:** This is NORMAL and not an error!

These notices appear because migrations use `DROP POLICY IF EXISTS` before creating policies. They're idempotent by design and can be safely ignored.

### 7. Superadmin Creation Warnings

**Warning Message:**
```
WARNING: Error during superadmin creation: column "account_status" does not exist
```

**Solution:**
This warning should no longer appear after the migration reordering fix. If you still see it:

```bash
cd backend
make supabase-reset
```

The superadmin migration now:
- Checks for column existence before using them
- Dynamically builds SQL based on available columns
- Handles partial schema states gracefully

### 8. Network Creation Errors

**Error Message:**
```
Error creating network: litinkai_local_nw
```

**Solution:**
```bash
# Remove existing network if conflicting
docker network rm litinkai_local_nw

# Recreate it
docker network create litinkai_local_nw

# Try starting again
make supabase-start
```

### 9. Permission Denied Errors

**Error Message:**
```
Permission denied: supabase/storage/books
```

**Solution:**
```bash
# Fix permissions
cd backend
sudo chmod -R 755 supabase/storage
sudo chown -R $(whoami) supabase/storage

# Try again
make supabase-start
```

### 10. Out of Memory Errors

**Error Message:**
```
Error: Cannot allocate memory
```

**Solution:**
```bash
# Increase Docker Desktop memory allocation
# macOS/Windows: Docker Desktop → Settings → Resources → Memory
# Recommended: At least 4GB for Supabase

# Linux: Check available memory
free -h

# Stop other Docker containers
docker stop $(docker ps -q)

# Try again
make supabase-start
```

## Advanced Troubleshooting

### View Detailed Logs

```bash
# View Supabase startup logs
cd backend/supabase
supabase start --debug

# View specific container logs
docker logs supabase-db
docker logs supabase-auth
docker logs supabase-storage
```

### Check Migration Status

```bash
cd backend/supabase
supabase migration list
```

### Verify Database Connection

```bash
cd backend/supabase
supabase db execute "SELECT 1 as test;"
```

### Check Superadmin Status

```bash
cd backend/supabase
supabase db execute "SELECT * FROM public.check_superadmin_users();"
```

### Reset Everything (Nuclear Option)

```bash
cd backend

# Stop all services
make supabase-stop
docker stop $(docker ps -q)

# Remove all Supabase data
make supabase-reset

# Clean Docker system (WARNING: removes all unused images/volumes)
docker system prune -a --volumes

# Start fresh
make supabase-start
```

## Pre-Flight Checklist

Before starting Supabase, verify:

- [ ] Docker is running (`docker ps` works)
- [ ] You're in the `backend` directory
- [ ] Storage directory exists: `ls -la supabase/storage/books`
- [ ] Migrations directory exists: `ls -la supabase/migrations`
- [ ] No other Supabase instance running: `docker ps | grep supabase`
- [ ] Required ports are free: 54321-54327

## Directory Structure

Your backend directory should look like this:

```
backend/
├── supabase/
│   ├── config.toml
│   ├── seed.sql
│   ├── migrations/
│   │   ├── 20250101000000_create_initial_schema.sql
│   │   ├── 20250102000000_add_unique_email_constraint.sql
│   │   ├── ...
│   │   └── 20251113225537_add_seed_compatibility_columns.sql
│   └── storage/
│       └── books/
│           └── .gitkeep
├── scripts/
│   ├── start-supabase.sh
│   └── stop-supabase.sh
└── Makefile
```

## Getting Help

If none of these solutions work:

1. Check the [Supabase CLI documentation](https://supabase.com/docs/guides/cli)
2. Check Docker status: `docker info`
3. Check system resources: `df -h` and `free -h`
4. Review the startup script output carefully
5. Try the nuclear reset option above
6. Check Supabase CLI version: `supabase --version`

## Preventive Measures

### Regular Maintenance

```bash
# Weekly: Clean up Docker
docker system prune -f

# Monthly: Update Supabase CLI
brew upgrade supabase  # macOS
# or
npm update -g supabase  # npm install
```

### Best Practices

1. **Always stop Supabase when done**: `make supabase-stop`
2. **Don't force quit Docker Desktop** - stop services first
3. **Keep Docker Desktop updated**
4. **Monitor disk space** - Docker images can be large
5. **Use `make all-up`** instead of starting services separately
6. **Authenticate with Docker Hub** to avoid rate limits

## Environment-Specific Notes

### macOS
- Ensure Docker Desktop has sufficient resources allocated
- M1/M2 Macs: Some images may need Rosetta 2 enabled

### Windows
- Use WSL2 backend for Docker Desktop
- Ensure WSL2 has sufficient resources
- Run commands in WSL2 terminal, not PowerShell

### Linux
- Ensure Docker daemon is running: `sudo systemctl status docker`
- User must be in docker group: `sudo usermod -aG docker $USER`
- May need to increase file descriptor limits

## Success Indicators

When Supabase starts successfully, you should see:

```
✅ Supabase services started successfully!

📊 Supabase Local Services:
   Studio URL:    http://127.0.0.1:54323
   Inbucket URL:  http://127.0.0.1:54324 (Email testing)
   API URL:       http://127.0.0.1:54321
   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

You should be able to:
- Open Supabase Studio at http://127.0.0.1:54323
- See all tables in the SQL Editor
- Find the superadmin profile in the profiles table
- Connect to the database from your application
