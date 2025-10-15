# Celery Setup Instructions for Scene Image Generation

## Problem

Scene image generation is returning 500 errors because Celery workers are not running. The code has been updated to use Celery tasks, but the workers need to be started for the async architecture to work.

## Current Status

### ✅ Completed Implementation
1. **Celery Task Created** (`/backend/app/tasks/image_tasks.py`)
   - `generate_scene_image_task` function created with proper error handling
   - Retry logic with exponential backoff implemented
   - Database status tracking in place

2. **API Endpoint Updated** (`/backend/app/api/v1/chapters.py`)
   - `generate_scene_image` endpoint now queues Celery tasks
   - Returns `ImageGenerationQueuedResponse` immediately
   - Error handling and logging added

3. **Status Polling Endpoint** (`/backend/app/api/v1/chapters.py`)
   - `get_scene_image_status` endpoint created
   - Queries by chapter_id and scene_number
   - Returns real-time status updates

4. **Database Schema** (`/backend/supabase/migrations/20251015_add_scene_fields_to_generations.sql`)
   - Added `chapter_id`, `script_id`, `scene_number`, `image_type`, `retry_count` columns
   - Created indexes for efficient queries

5. **Frontend Integration**
   - `useImageGeneration.ts` hook updated with polling logic
   - `userService.ts` updated with new API methods
   - Async status tracking implemented

### ❌ Missing: Celery Workers Not Running

The 500 errors occur because Celery workers are not started. When the API tries to queue a task with `generate_scene_image_task.delay()`, it fails because there's no Celery broker connection or the workers aren't running.

## How to Fix: Start Celery Workers

### Option 1: Using Docker Compose (Recommended)

The `docker-compose.yml` already has Celery configured. Start all services:

```bash
cd /tmp/cc-agent/50548081/project/backend
docker-compose up -d
```

This will start:
- `api` - FastAPI application (port 8000)
- `redis` - Message broker (port 6379)
- `celery` - Celery worker
- `flower` - Celery monitoring UI (port 5555)

To view Celery worker logs:
```bash
docker-compose logs -f celery
```

To restart just the Celery worker:
```bash
docker-compose restart celery
```

### Option 2: Manual Celery Worker Start

If not using Docker Compose, start Celery manually:

```bash
cd /tmp/cc-agent/50548081/project/backend

# Make sure Redis is running first
# If using Docker:
docker run -d -p 6379:6379 redis:7-alpine

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info
```

### Option 3: Development Mode

For development, you can run the worker in a separate terminal:

```bash
# Terminal 1: Start FastAPI
cd /tmp/cc-agent/50548081/project/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
cd /tmp/cc-agent/50548081/project/backend
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 3 (Optional): Start Flower monitoring
celery -A app.tasks.celery_app flower
```

## Verifying Celery is Working

### 1. Check Celery Worker Logs

When Celery starts successfully, you should see:
```
[INFO/MainProcess] Connected to redis://redis:6379/0
[INFO/MainProcess] mingle: searching for neighbors
[INFO/MainProcess] mingle: all alone
[INFO/MainProcess] celery@hostname ready.
```

### 2. Check Registered Tasks

Celery should list all available tasks:
```
[tasks]
  . app.tasks.image_tasks.generate_character_image_task
  . app.tasks.image_tasks.generate_scene_image_task
```

### 3. Test Scene Generation

When you trigger scene image generation from the frontend, you should see:

**FastAPI logs:**
```
[DEBUG] [generate_scene_image] About to queue task for record_id=xxx, scene=1
[DEBUG] [generate_scene_image] Task queued successfully with task_id=xxx
```

**Celery worker logs:**
```
[INFO/MainProcess] Received task: app.tasks.image_tasks.generate_scene_image_task[xxx]
[INFO] [SceneImageTask] Starting generation for scene 1
[INFO] [SceneImageTask] Task completed successfully for record xxx
```

### 4. Check Flower Dashboard

Open http://localhost:5555 to see:
- Active tasks
- Worker status
- Task history
- Success/failure rates

## Troubleshooting

### Error: "Cannot connect to redis"

**Cause:** Redis is not running or not accessible

**Fix:**
```bash
# Check if Redis is running
docker ps | grep redis

# Or start Redis manually
docker run -d -p 6379:6379 redis:7-alpine

# Or in docker-compose
docker-compose up -d redis
```

### Error: "No module named 'app.tasks'"

**Cause:** Python path not set correctly

**Fix:**
```bash
# Make sure you're in the backend directory
cd /tmp/cc-agent/50548081/project/backend

# Set PYTHONPATH if needed
export PYTHONPATH=/tmp/cc-agent/50548081/project/backend:$PYTHONPATH

# Then start Celery
celery -A app.tasks.celery_app worker --loglevel=info
```

### Error: "Task was called with invalid signature"

**Cause:** Task signature doesn't match the delay() call

**Fix:** Check that all parameters passed to `generate_scene_image_task.delay()` match the task function signature. The current implementation should work correctly.

### 500 Errors Continue After Starting Celery

**Possible causes:**
1. Celery worker crashed - check logs
2. Redis connection issues - verify Redis is accessible
3. Database connection issues - check Supabase credentials
4. ModelsLab API key missing - verify MODELSLAB_API_KEY in .env

**Debug steps:**
```bash
# Check Celery worker status
docker-compose ps celery

# View recent logs
docker-compose logs --tail=100 celery

# Restart Celery worker
docker-compose restart celery

# Check Redis connectivity
redis-cli -h localhost -p 6379 ping
# Should respond: PONG
```

## Environment Variables Required

Ensure these are set in `/tmp/cc-agent/50548081/project/backend/.env`:

```bash
# Redis/Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
REDIS_URL=redis://redis:6379

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# ModelsLab API
MODELSLAB_API_KEY=your-modelslab-api-key

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
```

## Production Deployment

### Using Docker Compose

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build

# Start services
docker-compose up -d

# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f
```

### Using Systemd (Linux Servers)

Create `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker for LitInk
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/litink/backend
Environment="PATH=/var/www/litink/venv/bin"
ExecStart=/var/www/litink/venv/bin/celery -A app.tasks.celery_app worker --loglevel=info --detach
ExecStop=/var/www/litink/venv/bin/celery -A app.tasks.celery_app control shutdown
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

## Monitoring and Maintenance

### Check Task Queue Length

```bash
# Connect to Redis
redis-cli -h localhost -p 6379

# Check queue length
LLEN celery

# View pending tasks
LRANGE celery 0 -1
```

### Clear Failed Tasks

```bash
# Using Flower UI
# Go to http://localhost:5555/tasks
# Filter by "FAILED" status
# Select and purge

# Or using Celery command
celery -A app.tasks.celery_app purge
```

### Scale Workers

```bash
# Start multiple workers
docker-compose up -d --scale celery=3

# Or manually
celery -A app.tasks.celery_app worker --concurrency=4
```

## Next Steps

1. **Start Celery workers** using one of the methods above
2. **Verify workers are running** by checking logs
3. **Test scene generation** from the frontend
4. **Monitor with Flower** at http://localhost:5555
5. **Check database records** in `image_generations` table to verify status updates

Once Celery workers are running, the scene image generation should work exactly like character image generation:
- Immediate response with task_id
- Background processing
- Status polling
- Automatic retries on failure
- No more 500 errors

## Summary

The implementation is complete. The 500 errors occur because Celery workers need to be started. Use Docker Compose to start all services including Celery workers, then scene image generation will work asynchronously as designed.
