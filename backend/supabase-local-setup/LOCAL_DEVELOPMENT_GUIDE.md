# Local Development Guide

This guide will help you set up and use the local development environment for Litinkai.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Available Services](#available-services)
- [Development Workflow](#development-workflow)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

The local development environment includes:

- **Supabase Local Stack**:
  - PostgreSQL database with all migrations
  - Authentication service
  - Storage service for file uploads
  - Supabase Studio (web UI)
  - Inbucket (email testing)

- **Application Services**:
  - FastAPI backend
  - Redis (caching & Celery broker)
  - RabbitMQ (message queue)
  - Celery workers & beat scheduler
  - Flower (Celery monitoring)
  - Mailpit (backup email testing)

## Prerequisites

Before starting, ensure you have:

1. **Docker Desktop** installed and running
2. **Supabase CLI** installed
   ```bash
   # Install on macOS
   brew install supabase/tap/supabase

   # Install on Linux
   curl -fsSL https://cli.supabase.com/install.sh | sh

   # Install on Windows (PowerShell)
   scoop install supabase
   ```

3. **Docker Compose** v2+ installed (usually comes with Docker Desktop)

## Quick Start

### 1. Configure Environment

Copy and configure your local environment file:

```bash
cd backend
cp .envs/.env.local .envs/.env.local.active
```

Edit `.envs/.env.local.active` and add your API keys (OpenAI, ElevenLabs, etc.)

### 2. Start All Services

```bash
cd backend
./scripts/start-local-dev.sh
```

This will:
- Start Supabase local services
- Apply all database migrations
- Load seed data with test users
- Start application services

### 3. Verify Everything is Running

Visit these URLs to confirm services are up:

- **Supabase Studio**: http://127.0.0.1:54323
- **API Health Check**: http://localhost:8000/health
- **Inbucket (Email)**: http://127.0.0.1:54324
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **Flower**: http://localhost:5555

### 4. Test Login

Use any of these test accounts (password: `password123`):

- `superadmin@litinkai.local` - Full access
- `admin@litinkai.local` - Admin access
- `creator@litinkai.local` - Creator access
- `user@litinkai.local` - Regular user
- `premium@litinkai.local` - Premium user

## Environment Configuration

### Local Environment (.env.local)

The `.env.local` file contains configuration for local development:

```bash
# Supabase Local
SUPABASE_URL=http://127.0.0.1:54321
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Environment
ENVIRONMENT=development
DEBUG=true
```

### Production Environment

Production uses different environment variables pointing to Supabase Cloud.

**Important**: The application automatically detects which environment you're using based on the `SUPABASE_URL` setting.

## Available Services

### Supabase Services

| Service | URL | Description |
|---------|-----|-------------|
| Studio | http://127.0.0.1:54323 | Database management UI |
| API | http://127.0.0.1:54321 | REST API |
| Database | postgresql://postgres:postgres@127.0.0.1:54322/postgres | Direct DB access |
| Inbucket | http://127.0.0.1:54324 | Email testing UI |

### Application Services

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Traefik Dashboard | http://localhost:8080 | - |
| Mailpit | http://localhost:8025 | - |
| RabbitMQ | http://localhost:15672 | guest/guest |
| Flower | http://localhost:5555 | - |

## Development Workflow

### Starting Development

```bash
# Start everything
./scripts/start-local-dev.sh

# Or start services separately:
cd supabase && supabase start && cd ..
docker-compose -f local.yml up -d
```

### Viewing Logs

```bash
# Interactive log viewer
./scripts/view-local-logs.sh

# Or directly:
docker-compose -f local.yml logs -f api
docker-compose -f local.yml logs -f celeryworker
```

### Stopping Services

```bash
# Stop everything
./scripts/stop-local-dev.sh

# Or stop services separately:
docker-compose -f local.yml down
cd supabase && supabase stop && cd ..
```

### Making Database Changes

#### 1. Create a new migration

```bash
cd supabase
supabase migration new your_migration_name
```

#### 2. Edit the migration file

Edit the generated file in `supabase/migrations/`

#### 3. Apply the migration

```bash
supabase db reset  # Resets and applies all migrations
```

#### 4. Push to production (when ready)

```bash
supabase db push
```

### Testing Email Flows

#### Using Inbucket (Supabase)

1. Open http://127.0.0.1:54324
2. Trigger an email in your app (e.g., user registration)
3. Check Inbucket for the email

#### Using Mailpit (Application)

1. Open http://localhost:8025
2. Emails sent via SMTP will appear here

## Common Tasks

### Reset Local Database

**Warning**: This deletes all local data!

```bash
./scripts/reset-local-db.sh
```

This will:
- Drop and recreate the database
- Re-run all migrations
- Reload seed data with test users

### Access Database Directly

```bash
# Using psql
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Or through Supabase Studio
# Visit http://127.0.0.1:54323 and use the SQL Editor
```

### Test File Uploads

Files are stored in the local `books` bucket:

```bash
# Files are stored in:
backend/supabase/storage/books/
```

### Debug Celery Tasks

```bash
# View worker logs
docker-compose -f local.yml logs -f celeryworker

# View Flower monitoring
# Visit http://localhost:5555
```

### Clear Redis Cache

```bash
docker-compose -f local.yml exec redis redis-cli FLUSHALL
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :54321  # Or whatever port is in use

# Stop Supabase and restart
cd supabase && supabase stop && supabase start && cd ..
```

### Supabase Won't Start

```bash
# Stop and clean up
cd supabase
supabase stop
supabase start
cd ..

# If that doesn't work, try:
docker system prune -a  # Warning: removes all Docker data
```

### Database Connection Issues

```bash
# Check if Supabase is running
supabase status

# Restart Supabase
cd supabase && supabase restart && cd ..

# Check application logs
docker-compose -f local.yml logs api
```

### Migration Errors

```bash
# Check migration status
cd supabase
supabase db reset

# If migrations fail, check the migration files for errors
# Fix the SQL and reset again
```

### Can't See Test Users

```bash
# Verify seed data was loaded
cd supabase
supabase db reset

# Check in Studio
# Visit http://127.0.0.1:54323
# Go to Authentication > Users
```

### Application Can't Connect to Supabase

1. Check your `.envs/.env.local` file has correct URLs
2. Verify Supabase is running: `supabase status`
3. Check logs: `docker-compose -f local.yml logs api`
4. Ensure `SUPABASE_URL=http://127.0.0.1:54321` (not localhost)

### Emails Not Appearing in Inbucket

1. Check Inbucket is running: http://127.0.0.1:54324
2. Verify email settings in Supabase config.toml
3. Check application logs for email errors

## Best Practices

### DO:

- ✅ Always use the local environment for development
- ✅ Commit migration files to git
- ✅ Test migrations locally before pushing to production
- ✅ Use test users for development
- ✅ Keep your `.env.local` updated with valid API keys

### DON'T:

- ❌ Don't connect to production database from local
- ❌ Don't commit `.env.local` with real API keys
- ❌ Don't modify seed data with production data
- ❌ Don't skip testing migrations locally
- ❌ Don't use production credentials in local env

## Getting Help

If you encounter issues:

1. Check the logs: `./scripts/view-local-logs.sh`
2. Review this guide's troubleshooting section
3. Check Supabase status: `supabase status`
4. Reset the environment: `./scripts/reset-local-db.sh`
5. Ask the team in Slack

## Additional Resources

- [Supabase Local Development Docs](https://supabase.com/docs/guides/local-development)
- [Supabase CLI Reference](https://supabase.com/docs/reference/cli)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

**Happy coding!** 🚀
