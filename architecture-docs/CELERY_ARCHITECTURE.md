# Celery Architecture - How It Works

## Overview

This project uses Celery for asynchronous task processing (image generation, video generation, audio processing, etc.). This document explains the architecture and how to work with it.

## ✅ Files That Matter

### 1. **app/tasks/celery_app.py** (Configuration)
- Defines the Celery application instance
- Configures broker (Redis) and result backend
- Registers task modules (image_tasks, video_tasks, audio_tasks, etc.)
- Sets worker configuration (timeouts, concurrency, etc.)

### 2. **app/tasks/image_tasks.py** (Task Definitions)
- Contains `@celery_app.task` decorated functions
- Defines actual work: `generate_character_image_task()`, `generate_scene_image_task()`, etc.
- These are the functions that workers execute

### 3. **app/tasks/*.py** (Other Task Modules)
- `video_tasks.py` - Video generation tasks
- `audio_tasks.py` - Audio generation tasks
- `merge_tasks.py` - Video merge operations
- `ai_tasks.py` - AI processing tasks
- `blockchain_tasks.py` - NFT minting tasks
- `lipsync_tasks.py` - Lipsync processing

### 4. **docker-compose.yml** (Worker Launcher)
- Defines the `celery` service that runs workers
- Command: `celery -A app.tasks.celery_app worker --loglevel=info`
- This is what actually starts the worker processes

## How Tasks Are Executed

```
┌─────────────────┐
│   API Request   │
│  (FastAPI)      │
└────────┬────────┘
         │
         │ task.delay(...)  # Queue task
         ↓
┌─────────────────┐
│   Redis Queue   │ ← Task stored here
└────────┬────────┘
         │
         │ Workers poll for tasks
         ↓
┌─────────────────┐
│  Celery Worker  │ ← Started by docker-compose
│  (Container)    │
└────────┬────────┘
         │
         │ Executes function from image_tasks.py
         ↓
┌─────────────────┐
│  Task Result    │
│  (Supabase DB)  │
└─────────────────┘
```

## Starting Workers

### Production (Docker Compose - Recommended)

```bash
# Start all services including Celery worker
docker-compose up -d

# Start only Celery worker
docker-compose up -d celery

# View Celery worker logs
docker-compose logs -f celery

# Restart Celery worker after code changes
docker-compose restart celery
```

### Development (Manual)

```bash
# From backend directory
celery -A app.tasks.celery_app worker --loglevel=info
```

## Monitoring Workers

### Flower (Web UI)
```bash
# Start Flower dashboard
docker-compose up -d flower

# Access at http://localhost:5555
```

### Logs
```bash
# View worker logs
docker-compose logs -f celery

# View all logs
docker-compose logs -f
```

## How Code Calls Tasks

### From API Endpoints
```python
from app.tasks.image_tasks import generate_character_image_task

# Queue task (returns immediately)
task = generate_character_image_task.delay(
    character_name="John",
    character_description="A hero",
    user_id=user_id,
    # ... other params
)

# Return task ID to client
return {"task_id": task.id, "status": "queued"}
```

### From Services
```python
from app.tasks.image_tasks import generate_scene_image_task

# Queue task asynchronously
task = generate_scene_image_task.delay(
    record_id=record_id,
    scene_description=description,
    scene_number=1,
    user_id=user_id
)
```

## Task Status Tracking

Tasks update their status in the `image_generations` table:

1. **pending** - Task created, not yet picked up
2. **in_progress** - Worker is executing the task
3. **completed** - Task finished successfully
4. **failed** - Task encountered an error

## Common Operations

### Add a New Task

1. Define function in appropriate tasks file (e.g., `image_tasks.py`):
```python
@celery_app.task(bind=True)
def my_new_task(self, param1, param2):
    # Your logic here
    pass
```

2. Import and call from API/service:
```python
from app.tasks.image_tasks import my_new_task
task = my_new_task.delay(param1, param2)
```

3. Restart worker to pick up changes:
```bash
docker-compose restart celery
```

### Debug Task Execution

1. Check worker logs:
```bash
docker-compose logs -f celery
```

2. Check Flower dashboard:
```
http://localhost:5555
```

3. Check task status in database:
```sql
SELECT * FROM image_generations
WHERE status = 'failed'
ORDER BY created_at DESC;
```

## Important Notes

- **Workers must be running** for tasks to execute
- Tasks are queued in Redis, executed by workers
- Workers can run on same or different machines
- Multiple workers can process tasks in parallel
- Failed tasks can be retried automatically (configured in task decorator)

## Troubleshooting

### Tasks Not Executing
```bash
# Check if workers are running
docker-compose ps celery

# Check worker logs for errors
docker-compose logs celery

# Restart worker
docker-compose restart celery
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Worker Crashes
```bash
# View crash logs
docker-compose logs celery

# Restart with fresh logs
docker-compose restart celery
docker-compose logs -f celery
```

## Configuration

All Celery configuration is in `app/tasks/celery_app.py`:

- Task timeout: 30 minutes
- Soft timeout: 25 minutes
- Broker: Redis
- Result backend: Redis
- Task serialization: JSON
- Timezone: UTC

## Task Modules Registered

Current task modules loaded by Celery:
- `app.tasks.ai_tasks`
- `app.tasks.blockchain_tasks`
- `app.tasks.audio_tasks`
- `app.tasks.image_tasks`
- `app.tasks.video_tasks`
- `app.tasks.merge_tasks`
- `app.tasks.lipsync_tasks`

Add new modules to the `include` list in `celery_app.py`.
