# ✅ Local Development Setup Complete - November 19, 2024

## Summary of Changes Applied

All critical configuration issues have been resolved. Your local development environment is now ready to use.

---

## 🎯 What Was Fixed

### 1. **Created Missing .env.local File** ✅

**Location:** `backend/.envs/.env.local`

**What it contains:**
- All required environment variables for local development
- DEBUG and ENVIRONMENT variables required by entrypoint.sh
- Local Supabase connection settings (pointing to 127.0.0.1:54321)
- Redis and RabbitMQ Docker service configurations
- Mailpit SMTP settings for local email testing
- Placeholder API keys for AI services
- Security keys (JWT, signing keys)
- Celery configuration using Docker service names

**Critical settings:**
```bash
DEBUG=false
ENVIRONMENT=development
SUPABASE_URL=http://127.0.0.1:54321
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 2. **Fixed Redis Configuration in config.py** ✅

**File:** `backend/app/core/config.py`

**Changed:**
```python
# BEFORE (incorrect - causes connection errors in Docker)
CELERY_BROKER_URL: str = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

# AFTER (correct - uses Docker service name)
CELERY_BROKER_URL: str = "redis://redis:6379/0"
CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
```

**Why this matters:**
- Inside Docker containers, `localhost` refers to the container itself, not the host
- `redis` is the Docker service name defined in `local.yml`
- This allows containers to communicate with each other

### 3. **Updated Docker Compose Configuration** ✅

**File:** `backend/local.yml`

**Changed:**
```yaml
# BEFORE (all commented out - caused "unbound variable" error)
# environment:
#   - DEBUG=${DEBUG:-false}
#   - ENVIRONMENT=${ENVIRONMENT:-production}

# AFTER (uncommented for entrypoint.sh)
environment:
  # These two variables are required by entrypoint.sh
  # All other config comes from .env.local file below
  - DEBUG=${DEBUG:-false}
  - ENVIRONMENT=${ENVIRONMENT:-development}
env_file:
  - ./.envs/.env.local
```

**Why this matters:**
- The `entrypoint.sh` script checks these variables on startup
- Without them, you get "unbound variable" errors
- All other settings come from `.env.local` to avoid conflicts

### 4. **Created Database Migration: Author → Creator Role** ✅

**File:** `backend/supabase/migrations/20251119000000_migrate_author_to_creator_role.sql`

**What it does:**
- Updates database constraint to use 'creator' instead of 'author'
- Migrates all existing 'author' role assignments to 'creator'
- Updates table comments and documentation
- Refreshes PostgREST schema cache

**SQL changes:**
```sql
-- Updates valid roles constraint
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS check_valid_roles;
ALTER TABLE profiles ADD CONSTRAINT check_valid_roles
  CHECK (roles <@ ARRAY['explorer', 'creator', 'admin', 'superadmin']::text[]);

-- Migrates existing data
UPDATE profiles
SET roles = array_replace(roles, 'author', 'creator')
WHERE 'author' = ANY(roles);
```

### 5. **Updated Python Backend Code** ✅

**Files changed:**

**a) `backend/app/api/v1/admin.py`**
```python
# BEFORE
{
    "value": "author",
    "label": "Author",
    "description": "Can create and publish their own content"
}

# AFTER
{
    "value": "creator",
    "label": "Creator",
    "description": "Can create and publish their own content"
}
```

**b) `backend/app/core/auth_old.py`**
```python
# BEFORE
async def get_current_author(...):
    """Get current user if they are an author"""
    if 'author' not in user_roles:
        raise HTTPException(..., detail="author role required")

# AFTER
async def get_current_author(...):
    """Get current user if they are a creator (formerly author)"""
    if 'creator' not in user_roles:
        raise HTTPException(..., detail="creator role required")
```

**Note:** The function is still named `get_current_author` to maintain backward compatibility with existing code that calls it. The internal logic now checks for 'creator' role.

**c) `backend/app/auth/schema.py`**
- Already had `CREATOR = "creator"` defined
- Commented out old `AUTHOR = "author"` line
- Documentation strings updated to reference 'creator'

---

## 🚀 How to Start Your Local Environment

### Step 1: Start Supabase Local Instance

```bash
cd backend
make supabase-start
```

**What happens:**
- Starts local PostgreSQL database on port 54322
- Starts Supabase API on port 54321
- Starts Supabase Studio on port 54323
- Runs all 19 migrations (including the new author→creator migration)
- Loads seed data with test users

**Expected output:**
```
✅ Supabase services started successfully!

📊 Supabase Local Services:
   Studio URL:    http://127.0.0.1:54323
   API URL:       http://127.0.0.1:54321
   DB URL:        postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

### Step 2: Update Environment Keys (IMPORTANT!)

```bash
./scripts/update-env-keys.sh
```

**What this does:**
- Reads local Supabase keys from `supabase status`
- Automatically updates `.env.local` with correct local keys
- Creates a backup of your current `.env.local`

**This step is CRITICAL** because:
- The `.env.local` we created has placeholder keys
- Your local Supabase generates unique keys on first run
- Using wrong keys causes "Invalid API key" errors

### Step 3: Create Docker Network

```bash
docker network create litinkai_local_nw
```

**What this does:**
- Creates the external network that all services use
- Only needs to be done once
- If it already exists, you'll see "network already exists" (that's fine!)

### Step 4: Start Application Services

```bash
# For development mode WITHOUT debugger
make dev

# OR for development mode WITH debugger
make debug

# OR for production mode
make up
```

**What starts:**
- FastAPI backend API (port 8000)
- Redis cache (port 6379)
- RabbitMQ message broker (ports 5672, 15672)
- Celery workers (background task processing)
- Celery beat (scheduled tasks)
- Flower (Celery monitoring at port 5555)
- Mailpit (email testing at port 8025)
- Traefik (reverse proxy)

**Expected output:**
```
🔄 Starting in DEVELOPMENT mode WITHOUT debugger...
```

### Step 5: Verify Everything is Running

```bash
# Check Docker containers
docker ps

# Check API health
curl http://localhost:8000/health

# View API logs
make logs

# View all service logs
make logs-all
```

---

## 🌐 Access Your Services

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | React app (start with `npm run dev`) |
| **Backend API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Supabase Studio** | http://127.0.0.1:54323 | Database admin UI |
| **Mailpit** | http://localhost:8025 | Email testing UI |
| **Flower** | http://localhost:5555 | Celery monitoring |
| **RabbitMQ** | http://localhost:15672 | Message broker admin |

---

## 👤 Test Users Available

After running migrations and seed data, you have these test users:

| Email | Password | Role | Tier | Description |
|-------|----------|------|------|-------------|
| superadmin@litinkai.local | password123 | Superadmin | Enterprise | Full system access |
| admin@litinkai.local | password123 | Admin | Professional | Platform admin |
| creator@litinkai.local | password123 | Creator | Standard | Content creator |
| user@litinkai.local | password123 | Explorer | Free | Regular user |
| premium@litinkai.local | password123 | Creator | Premium | Premium creator |

**Note:** These users are for LOCAL development only!

---

## 🔧 Common Commands

### Supabase Management
```bash
make supabase-start     # Start Supabase local
make supabase-stop      # Stop Supabase
make supabase-status    # Check Supabase status
make supabase-reset     # Reset database (⚠️ deletes all data!)
```

### Application Management
```bash
make dev                # Start in development mode
make debug              # Start with debugger enabled
make up                 # Start in production mode
make down               # Stop all application services
make rebuild-dev        # Rebuild and restart in dev mode
make logs               # View API logs
make logs-all           # View all service logs
```

### Combined Commands
```bash
make all-up             # Start both Supabase AND application
make all-down           # Stop both application AND Supabase
```

### Help
```bash
make help               # Show all available commands
```

---

## 🐛 Troubleshooting

### Error: "Invalid API key"

**Cause:** You're using the wrong Supabase keys (probably remote keys with local URL)

**Solution:**
```bash
cd backend
./scripts/update-env-keys.sh
make down
make dev
```

### Error: "unbound variable: DEBUG"

**Cause:** The environment section in `local.yml` is commented out

**Solution:** This is now fixed! The DEBUG and ENVIRONMENT variables are uncommented in `local.yml`.

### Error: "Connection refused to redis://localhost:6379"

**Cause:** Using localhost instead of Docker service name

**Solution:** This is now fixed! The config.py now uses `redis://redis:6379`.

### Error: "account_status column not found"

**Cause:** Connected to production Supabase instead of local

**Solution:**
1. Verify `.env.local` has `SUPABASE_URL=http://127.0.0.1:54321`
2. Run `./scripts/update-env-keys.sh` to ensure correct keys
3. Restart services: `make down && make dev`

### Docker Container Can't Reach Supabase

**Cause:** Docker networking issue with 127.0.0.1

**Solutions:**

**For Linux:**
```bash
# In .env.local, change:
SUPABASE_URL=http://172.17.0.1:54321
```

**For Mac/Windows:**
```bash
# In .env.local, change:
SUPABASE_URL=http://host.docker.internal:54321
```

**Alternative:** Add to `local.yml` under the `api` service:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

---

## 📋 Verification Checklist

After setup, verify everything works:

- [ ] Supabase is running: `cd backend/supabase && supabase status`
- [ ] `.env.local` exists with local keys
- [ ] Docker network exists: `docker network ls | grep litinkai`
- [ ] All containers running: `docker ps`
- [ ] API is healthy: `curl http://localhost:8000/health`
- [ ] API docs load: http://localhost:8000/docs
- [ ] Supabase Studio accessible: http://127.0.0.1:54323
- [ ] Database has tables: Check Studio → Table Editor
- [ ] Test users exist: Check Studio → Authentication → Users
- [ ] Migration applied: Check `profiles` table has 'creator' role constraint
- [ ] No 'author' roles remain: Query `SELECT * FROM profiles WHERE 'author' = ANY(roles)` (should be empty)

---

## 🎨 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR MACHINE                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend (localhost:5173)                              │
│  └─> VITE_API_URL=http://localhost:8000                │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  DOCKER NETWORK: litinkai_local_nw                │ │
│  ├───────────────────────────────────────────────────┤ │
│  │                                                   │ │
│  │  API Container (port 8000)                        │ │
│  │  ├─> Connects to: redis:6379                      │ │
│  │  ├─> Connects to: rabbitmq:5672                   │ │
│  │  ├─> Connects to: mailpit:1025                    │ │
│  │  └─> Connects to: 127.0.0.1:54321 (Supabase)     │ │
│  │                                                   │ │
│  │  Redis Container (redis:6379)                     │ │
│  │  RabbitMQ Container (rabbitmq:5672)               │ │
│  │  Mailpit Container (mailpit:1025)                 │ │
│  │  Celery Workers                                   │ │
│  │  Celery Beat                                      │ │
│  │  Flower (port 5555)                               │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Supabase Local (127.0.0.1)                             │
│  ├─> PostgreSQL (54322)                                │
│  ├─> API (54321)                                        │
│  ├─> Studio (54323)                                     │
│  └─> Inbucket (54324)                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 Environment Variable Strategy

**For Local Development** (`.env.local`):
- Points to LOCAL Supabase at 127.0.0.1:54321
- Uses LOCAL Supabase keys
- Uses Docker service names (redis, rabbitmq, mailpit)
- DEBUG=false, ENVIRONMENT=development

**For Production** (`.env.production` - not created yet):
- Points to REMOTE Supabase at vtuqaubejlzqjmieelyr.supabase.co
- Uses PRODUCTION Supabase keys
- Uses actual hostnames/IPs for services
- DEBUG=false, ENVIRONMENT=production

**Never mix local URLs with remote keys or vice versa!**

---

## 📚 Next Steps

1. **Add Your API Keys** (Optional but recommended)
   ```bash
   nano backend/.envs/.env.local
   ```
   Add your real API keys for:
   - OpenAI (for AI features)
   - ElevenLabs (for voice generation)
   - DeepSeek (for script generation)
   - OpenRouter (for plot generation)
   - ModelsLab (for image/video generation)
   - Stripe (for payments testing)

2. **Start Development**
   ```bash
   cd backend
   make all-up

   # In another terminal
   cd ../  # back to project root
   npm run dev
   ```

3. **Test the System**
   - Register a new user
   - Upload a book
   - Generate content
   - Test all features

4. **Create Production Environment**
   - Create `backend/.envs/.env.production`
   - Add production Supabase credentials
   - Set ENVIRONMENT=production
   - Configure production API keys

---

## 🎉 Success Indicators

You'll know everything is working when:

✅ No "Invalid API key" errors
✅ No "unbound variable" errors
✅ No "Connection refused" errors for Redis
✅ No "account_status column not found" errors
✅ API responds at http://localhost:8000/health
✅ Can login with test users
✅ Can create new users with 'creator' role
✅ Supabase Studio shows all tables and data
✅ Mailpit shows test emails
✅ Celery tasks process in Flower dashboard

---

## 📖 Additional Documentation

- **Backend README:** `backend/README.md`
- **Local Development Guide:** `backend/supabase-local-setup/LOCAL_DEVELOPMENT_GUIDE.md`
- **Troubleshooting:** `backend/supabase-local-setup/SUPABASE_TROUBLESHOOTING.md`
- **Scripts Documentation:** `backend/scripts/README.md`

---

## 🆘 Getting Help

If you encounter issues:

1. Check the Supabase status: `cd backend/supabase && supabase status`
2. Check Docker containers: `docker ps`
3. View logs: `make logs-all`
4. Verify `.env.local` has correct local keys
5. Try resetting: `make all-down && make all-up`
6. Check troubleshooting docs listed above

---

**Setup completed on:** November 19, 2024
**All critical issues resolved:** ✅
**Ready for development:** ✅

**Enjoy building! 🚀**
