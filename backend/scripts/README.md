# Development Scripts

This directory contains helper scripts for local development.

## Available Scripts

### start-local-dev.sh

Starts the complete local development environment.

**Usage:**
```bash
./scripts/start-local-dev.sh
```

**What it does:**
1. Creates Docker network if needed
2. Starts Supabase local services (DB, Auth, Storage, Studio, Inbucket)
3. Starts application services (API, Redis, RabbitMQ, Celery, etc.)
4. Displays all service URLs and test user credentials

**Output:**
- Supabase Studio: http://127.0.0.1:54323
- Inbucket (Email): http://127.0.0.1:54324
- API: http://localhost:8000
- And more...

---

### stop-local-dev.sh

Stops all local development services.

**Usage:**
```bash
./scripts/stop-local-dev.sh
```

**What it does:**
1. Stops all Docker Compose services
2. Stops Supabase local services

**Note:** Data is preserved. Use `reset-local-db.sh` to clear data.

---

### reset-local-db.sh

Resets the local database to a clean state.

**Usage:**
```bash
./scripts/reset-local-db.sh
```

**What it does:**
1. Asks for confirmation (destructive operation!)
2. Drops and recreates the database
3. Re-runs all migrations
4. Reloads seed data with test users

**Warning:** This will delete ALL local data!

**Use when:**
- You need a fresh database
- Migrations have changed
- You want to reset test data
- Database is in an inconsistent state

---

### view-local-logs.sh

Interactive log viewer for development services.

**Usage:**
```bash
./scripts/view-local-logs.sh
```

**Options:**
1. All application services
2. API service only
3. Celery worker
4. Celery beat
5. Flower
6. Redis
7. RabbitMQ
8. Mailpit
9. Supabase logs

**Tip:** Press `Ctrl+C` to exit log viewing

---

## Quick Reference

### First Time Setup

```bash
# 1. Install prerequisites (Docker, Supabase CLI)
brew install supabase/tap/supabase  # macOS

# 2. Configure environment
cp .envs/.env.local .envs/.env.local.active
# Edit .env.local.active with your API keys

# 3. Start everything
./scripts/start-local-dev.sh
```

### Daily Development

```bash
# Start services
./scripts/start-local-dev.sh

# View logs
./scripts/view-local-logs.sh

# Stop services when done
./scripts/stop-local-dev.sh
```

### When Things Go Wrong

```bash
# Reset database
./scripts/reset-local-db.sh

# Restart everything
./scripts/stop-local-dev.sh
./scripts/start-local-dev.sh

# View logs to debug
./scripts/view-local-logs.sh
```

## Script Requirements

All scripts assume you're running them from the `backend` directory:

```bash
cd backend
./scripts/start-local-dev.sh  # ✅ Correct

cd backend/scripts
./start-local-dev.sh  # ❌ Won't work
```

## Troubleshooting Scripts

### Script Won't Execute

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### Script Fails Immediately

1. Check you're in the `backend` directory
2. Verify Docker is running
3. Check for port conflicts

### Can't Find supabase Command

```bash
# Install Supabase CLI
brew install supabase/tap/supabase  # macOS
# Or follow: https://supabase.com/docs/guides/cli
```

## Adding New Scripts

When creating new scripts:

1. Add them to this directory
2. Make them executable: `chmod +x scripts/your-script.sh`
3. Add error handling: `set -e`
4. Add helpful output with colors
5. Document in this README

## Script Template

```bash
#!/bin/bash

# ============================================
# Script Name
# ============================================
# Description of what this script does

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "supabase/config.toml" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

echo -e "${BLUE}Starting...${NC}"
# Your script logic here
echo -e "${GREEN}✅ Done!${NC}"
```

## Additional Help

For more detailed information, see:
- [Local Development Guide](../LOCAL_DEVELOPMENT_GUIDE.md)
- [Supabase CLI Docs](https://supabase.com/docs/reference/cli)
- [Docker Compose Docs](https://docs.docker.com/compose/)
