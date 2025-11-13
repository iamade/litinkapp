# Local Development Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     LITINKAI LOCAL DEVELOPMENT                          │
│                                                                         │
│  Developer's Machine (Docker Desktop)                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  DEVELOPER WORKSTATION                                                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ SUPABASE LOCAL STACK (Ports 543xx)                                    │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │ │
│  │  │  PostgreSQL DB   │    │   Auth Service   │    │  Storage API   │ │ │
│  │  │                  │    │                  │    │                │ │ │
│  │  │  Port: 54322     │    │  JWT tokens      │    │  File uploads  │ │ │
│  │  │  postgres/       │    │  User mgmt       │    │  books bucket  │ │ │
│  │  │  postgres        │    │                  │    │                │ │ │
│  │  └────────┬─────────┘    └────────┬─────────┘    └────────┬───────┘ │ │
│  │           │                       │                       │         │ │
│  │           └───────────────────────┴───────────────────────┘         │ │
│  │                                   │                                 │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │             Supabase REST API (Port 54321)                    │ │ │
│  │  │  /rest/v1/* - Database operations                             │ │ │
│  │  │  /auth/v1/* - Authentication endpoints                        │ │ │
│  │  │  /storage/v1/* - File storage operations                      │ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │ │
│  │                                                                       │ │
│  │  ┌──────────────────┐    ┌──────────────────┐                       │ │
│  │  │ Supabase Studio  │    │    Inbucket      │                       │ │
│  │  │ Port: 54323      │    │    Port: 54324   │                       │ │
│  │  │ Web UI for DB    │    │    Email Testing │                       │ │
│  │  └──────────────────┘    └──────────────────┘                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                   ▲                                         │
│                                   │ http://127.0.0.1:54321                  │
│                                   │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ APPLICATION STACK (Docker Compose)                                    │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  FastAPI Backend (Port 8000)                                 │   │ │
│  │  │  ┌────────────────────────────────────────────────────────┐  │   │ │
│  │  │  │  API Routes                                            │  │   │ │
│  │  │  │  /api/v1/*                                             │  │   │ │
│  │  │  └────────────────────────────────────────────────────────┘  │   │ │
│  │  │  ┌────────────────────────────────────────────────────────┐  │   │ │
│  │  │  │  Supabase Client                                       │  │   │ │
│  │  │  │  - Connects to LOCAL Supabase (127.0.0.1:54321)        │  │   │ │
│  │  │  │  - Database operations                                 │  │   │ │
│  │  │  │  - Auth operations                                     │  │   │ │
│  │  │  │  - Storage operations                                  │  │   │ │
│  │  │  └────────────────────────────────────────────────────────┘  │   │ │
│  │  │  ┌────────────────────────────────────────────────────────┐  │   │ │
│  │  │  │  Services                                              │  │   │ │
│  │  │  │  - AI Service (OpenAI, etc)                            │  │   │ │
│  │  │  │  - Image Generation                                    │  │   │ │
│  │  │  │  - Audio Generation                                    │  │   │ │
│  │  │  │  - Video Generation                                    │  │   │ │
│  │  │  └────────────────────────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                      │                                               │ │
│  │                      │ Enqueues tasks                                │ │
│  │                      ▼                                               │ │
│  │  ┌─────────────────────────────────────────────┐                    │ │
│  │  │  Redis (Port 6379)                          │                    │ │
│  │  │  - Cache                                    │                    │ │
│  │  │  - Celery broker                            │                    │ │
│  │  │  - Session storage                          │                    │ │
│  │  └─────────────────────────────────────────────┘                    │ │
│  │                      │                                               │ │
│  │  ┌───────────────────┴──────────────────────┐                       │ │
│  │  │                                           │                       │ │
│  │  ▼                                           ▼                       │ │
│  │  ┌──────────────────────┐      ┌────────────────────────┐           │ │
│  │  │  Celery Worker       │      │  Celery Beat           │           │ │
│  │  │  - Process tasks     │      │  - Schedule tasks      │           │ │
│  │  │  - AI processing     │      │  - Periodic jobs       │           │ │
│  │  │  - Image generation  │      │                        │           │ │
│  │  │  - Audio generation  │      │                        │           │ │
│  │  └──────────────────────┘      └────────────────────────┘           │ │
│  │            │                                                         │ │
│  │            └──────────────┐                                          │ │
│  │                           ▼                                          │ │
│  │  ┌────────────────────────────────────────┐                         │ │
│  │  │  Flower (Port 5555)                    │                         │ │
│  │  │  - Monitor Celery tasks                │                         │ │
│  │  │  - View task history                   │                         │ │
│  │  └────────────────────────────────────────┘                         │ │
│  │                                                                       │ │
│  │  ┌─────────────────────────────────────────┐                        │ │
│  │  │  RabbitMQ (Ports 5672, 15672)           │                        │ │
│  │  │  - Message broker                       │                        │ │
│  │  │  - Task queue                           │                        │ │
│  │  └─────────────────────────────────────────┘                        │ │
│  │                                                                       │ │
│  │  ┌─────────────────────────────────────────┐                        │ │
│  │  │  Mailpit (Ports 8025, 1025)             │                        │ │
│  │  │  - Email testing (backup)               │                        │ │
│  │  │  - SMTP server                          │                        │ │
│  │  └─────────────────────────────────────────┘                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                   ▲                                         │
│                                   │ http://localhost:8000                   │
│                                   │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ FRONTEND (Vite Dev Server - Port 5173)                               │ │
│  │ - React Application                                                  │ │
│  │ - Hot Module Replacement                                             │ │
│  │ - Connects to API at http://localhost:8000                           │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### User Request Flow

```
┌──────────┐
│  Browser │
└─────┬────┘
      │ 1. HTTP Request
      ▼
┌─────────────────┐
│  Frontend App   │
│  (Port 5173)    │
└─────┬───────────┘
      │ 2. API Call (axios)
      ▼
┌─────────────────┐
│  FastAPI        │
│  (Port 8000)    │
└─────┬───────────┘
      │ 3. Supabase Client Call
      ▼
┌─────────────────┐
│  Supabase API   │
│  (Port 54321)   │
└─────┬───────────┘
      │ 4. SQL Query
      ▼
┌─────────────────┐
│  PostgreSQL     │
│  (Port 54322)   │
└─────┬───────────┘
      │ 5. Data
      │
      ▼
     ...returns back up the chain
```

### Background Task Flow

```
┌─────────────────┐
│  API Endpoint   │
└─────┬───────────┘
      │ 1. Enqueue task
      ▼
┌─────────────────┐
│  Redis/RabbitMQ │
└─────┬───────────┘
      │ 2. Task queued
      ▼
┌─────────────────┐
│  Celery Worker  │
└─────┬───────────┘
      │ 3. Process task
      │    (AI, Image Gen, etc)
      ▼
┌─────────────────┐
│  External APIs  │
│  (OpenAI, etc)  │
└─────┬───────────┘
      │ 4. Results
      ▼
┌─────────────────┐
│  Supabase DB    │
│  (Save results) │
└─────────────────┘
```

### File Upload Flow

```
┌──────────┐
│  Browser │
└─────┬────┘
      │ 1. Upload file
      ▼
┌─────────────────┐
│  Frontend       │
└─────┬───────────┘
      │ 2. POST to API
      ▼
┌─────────────────┐
│  FastAPI        │
│  Validate file  │
└─────┬───────────┘
      │ 3. Upload to storage
      ▼
┌─────────────────┐
│  Supabase       │
│  Storage API    │
└─────┬───────────┘
      │ 4. Store file
      ▼
┌─────────────────┐
│  Local Disk     │
│  supabase/      │
│  storage/books/ │
└─────────────────┘
```

## Port Map

| Service | Port(s) | Access |
|---------|---------|--------|
| **Supabase** |
| PostgreSQL | 54322 | psql only |
| REST API | 54321 | http://127.0.0.1:54321 |
| Studio | 54323 | http://127.0.0.1:54323 |
| Inbucket | 54324 | http://127.0.0.1:54324 |
| **Application** |
| FastAPI | 8000 | http://localhost:8000 |
| Redis | 6379 | Internal only |
| RabbitMQ AMQP | 5672 | Internal only |
| RabbitMQ Web | 15672 | http://localhost:15672 |
| Flower | 5555 | http://localhost:5555 |
| Mailpit Web | 8025 | http://localhost:8025 |
| Mailpit SMTP | 1025 | Internal only |
| **Frontend** |
| Vite Dev | 5173 | http://localhost:5173 |

## Environment Switching

### Local Development

```python
# .envs/.env.local
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_SERVICE_ROLE_KEY=<local_key>

# Result:
app/core/database.py detects:
"Initializing Supabase client for LOCAL environment"
```

### Production

```python
# .envs/.env.production
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<production_key>

# Result:
app/core/database.py detects:
"Initializing Supabase client for CLOUD environment"
```

## Storage Structure

### Local Filesystem

```
backend/
├── supabase/
│   ├── storage/
│   │   └── books/           # All uploaded files
│   │       ├── users/
│   │       │   ├── {user_id}/
│   │       │   │   ├── books/
│   │       │   │   ├── covers/
│   │       │   │   ├── audio/
│   │       │   │   └── videos/
│   ├── migrations/          # Schema changes
│   └── seed.sql            # Test data
└── .envs/
    └── .env.local          # Local config
```

## Database Schema

### Main Tables

```
┌─────────────────┐
│    auth.users   │  (Supabase managed)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    profiles     │  User profiles
└────────┬────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ subscriptions│  │    books     │  │  characters  │
└─────────────┘  └──────┬───────┘  └──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   chapters   │
                 └──────┬───────┘
                        │
                        ├──────────────┬──────────────┐
                        ▼              ▼              ▼
                 ┌──────────┐  ┌──────────┐  ┌──────────┐
                 │ scripts  │  │  audio   │  │  images  │
                 └──────────┘  └──────────┘  └──────────┘
```

## Security

### Local Environment

- ✅ All services run on localhost
- ✅ Not accessible from internet
- ✅ Default credentials for testing only
- ✅ No SSL required
- ✅ CORS allows localhost

### Production Environment

- ✅ Supabase Cloud with SSL
- ✅ Row Level Security (RLS) enabled
- ✅ JWT authentication
- ✅ Environment-specific credentials
- ✅ CORS restricted to production domains

## Network Isolation

```
┌────────────────────────────────────┐
│  Docker Network: litinkai_local_nw │
├────────────────────────────────────┤
│                                    │
│  All application containers        │
│  communicate internally            │
│                                    │
│  ┌──────┐  ┌──────┐  ┌──────┐    │
│  │ API  │←→│Redis │←→│Celery│    │
│  └──────┘  └──────┘  └──────┘    │
│      ▲                             │
│      │                             │
│      └──────────┐                  │
│                 │                  │
└─────────────────┼──────────────────┘
                  │
                  ▼ (host network)
         ┌────────────────┐
         │ Supabase Local │
         │ (separate)     │
         └────────────────┘
```

## Development Benefits

### Local Development

✅ **Fast**: No network latency
✅ **Safe**: Production data untouched
✅ **Complete**: All features work
✅ **Testable**: Easy to reset
✅ **Offline**: Works without internet
✅ **Debuggable**: Full access to logs

### vs Cloud Development

❌ Slow: Network latency
❌ Risky: Can affect production
❌ Limited: Some features restricted
❌ Permanent: Hard to undo mistakes
❌ Online: Requires internet
❌ Opaque: Limited access to internals

---

For more details, see [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md)
