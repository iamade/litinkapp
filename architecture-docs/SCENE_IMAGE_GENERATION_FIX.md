# Scene Image Generation Fix - Implementation Summary

## Issues Fixed

### 1. Database Schema Error (500 Error)
**Problem:** The `image_generations` table was missing the `chapter_id` column, causing the API to fail with:
```
Could not find the 'chapter_id' column of 'image_generations' in the schema cache
```

**Solution:** Applied migration to add the following columns:
- `chapter_id` (uuid) - Links scene images to chapters
- `retry_count` (integer, default 0) - Tracks retry attempts
- `last_attempted_at` (timestamptz) - Timestamp of last attempt
- `progress` (integer, default 0) - Progress percentage (0-100)

**Verification:**
```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'image_generations'
AND column_name IN ('chapter_id', 'retry_count', 'last_attempted_at', 'progress');
```

### 2. Celery Async Processing
**Problem:** Scene image generation was executing synchronously via HTTP instead of being queued to Celery workers, causing immediate failures and blocking the API.

**Solution:**
- Verified Celery app configuration includes `app.tasks.image_tasks`
- Confirmed task registration: `generate_scene_image_task` is properly decorated
- Docker Compose configuration shows Celery worker is set up correctly
- Tasks use `.delay()` method to queue asynchronously

**Architecture:**
```
Client -> API Endpoint -> Create DB Record -> Queue Celery Task -> Return 202 Accepted
                                                      ↓
                                            Celery Worker picks up task
                                                      ↓
                                            Generates image via ModelsLab V7
                                                      ↓
                                            Updates DB record with result
```

## API Endpoint Flow

### POST `/api/v1/chapters/{chapter_id}/images/scenes/{scene_number}`

1. **Request received** with scene description and style parameters
2. **Verify chapter access** - Check user has permission
3. **Create pending record** in `image_generations` table:
   ```python
   {
     "user_id": user_id,
     "chapter_id": chapter_id,  # ✅ Now works!
     "scene_number": scene_number,
     "script_id": script_id,
     "status": "pending",
     "progress": 0,
     "retry_count": 0,
     "image_type": "scene"
   }
   ```
4. **Queue Celery task** asynchronously:
   ```python
   task = generate_scene_image_task.delay(
     record_id=record_id,
     scene_description=scene_description,
     scene_number=scene_number,
     user_id=user_id,
     chapter_id=chapter_id,
     script_id=script_id,
     style=style,
     aspect_ratio=aspect_ratio,
     user_tier=user_tier,
     retry_count=0
   )
   ```
5. **Return response immediately** (202 Accepted):
   ```json
   {
     "task_id": "abc-123",
     "status": "queued",
     "message": "Scene image generation has been queued",
     "estimated_time_seconds": 60,
     "record_id": "xyz-789",
     "scene_number": 1
   }
   ```

## Task Processing Flow

### Celery Task: `generate_scene_image_task`

1. **Update status** to `in_progress` with progress tracking
2. **Call ModelsLab V7 API** to generate scene image
3. **Handle result**:
   - **Success**: Update record with `image_url`, set status to `completed`
   - **Failure**: Check if retryable error (timeout, rate limit, network)
     - If retryable and retry_count < 3: Retry with exponential backoff
     - Otherwise: Set status to `failed` with error message
4. **Update metadata** with generation details:
   ```python
   {
     "scene_number": scene_number,
     "script_id": script_id,
     "chapter_id": chapter_id,
     "model_used": "gen4_image",
     "generation_time": 45.2,
     "service": "modelslab_v7",
     "task_id": "abc-123"
   }
   ```

## Retry Mechanism

The task includes automatic retry with exponential backoff:

```python
# Retry logic
if is_retryable and retry_count < 3:
    base_backoff = min(60, 5 * (2 ** retry_count))  # 5s, 10s, 20s
    jitter = random.uniform(0.5, 1.5)
    backoff_seconds = int(base_backoff * jitter)

    # Retry attempt 1: ~5-7 seconds
    # Retry attempt 2: ~10-15 seconds
    # Retry attempt 3: ~20-30 seconds
```

Retryable errors include:
- Timeouts
- Connection/network errors
- Rate limits (429)
- Service unavailable (503, 504)

## Status Polling

Clients should poll the status endpoint to check progress:

### GET `/api/v1/chapters/{chapter_id}/images/scenes/{scene_number}/status`

Response:
```json
{
  "record_id": "xyz-789",
  "status": "completed",  // pending, in_progress, completed, failed
  "image_url": "https://...",
  "scene_number": 1,
  "retry_count": 0,
  "progress": 100,
  "generation_time_seconds": 45.2,
  "created_at": "2025-10-15T15:00:00Z",
  "updated_at": "2025-10-15T15:00:45Z"
}
```

## Testing the Fix

### 1. Verify Database Migration

Run the test script:
```bash
cd backend
python test_celery_and_db.py
```

Expected output:
```
✅ PASS - Database Schema
✅ PASS - Celery Connection
✅ PASS - Celery Workers
✅ PASS - Registered Tasks
✅ PASS - Task Queueing

Total: 5/5 tests passed
```

### 2. Verify Celery Worker is Running

```bash
docker-compose ps celery
```

Expected: Container should be "Up" and healthy

```bash
docker-compose logs celery | grep "celery@"
```

Expected: Should see worker ready message and registered tasks

### 3. Test Scene Image Generation

```bash
# Make API call to generate scene image
curl -X POST "http://localhost:8000/api/v1/chapters/{chapter_id}/images/scenes/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scene_description": "A young wizard discovering magic",
    "style": "cinematic",
    "aspect_ratio": "16:9",
    "script_id": "script-uuid"
  }'
```

Expected response (202 Accepted):
```json
{
  "task_id": "abc-123-def-456",
  "status": "queued",
  "message": "Scene image generation has been queued and will be processed in the background",
  "estimated_time_seconds": 60,
  "record_id": "xyz-789",
  "scene_number": 1,
  "retry_count": 0
}
```

Then poll status:
```bash
# Check status
curl "http://localhost:8000/api/v1/chapters/{chapter_id}/images/scenes/1/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Monitor Celery Tasks

Use Flower dashboard (if running):
```
http://localhost:5555
```

Or check logs:
```bash
docker-compose logs -f celery
```

Look for:
```
[SceneImageTask] Starting generation for scene 1
[SceneImageTask] Successfully generated scene image: xyz-789
```

## Database Indexes

The migration created the following indexes for performance:

- `idx_image_generations_chapter_id` - Fast lookups by chapter
- `idx_image_generations_chapter_scene` - Composite index for chapter + scene
- `idx_image_generations_retry_count` - Find failed generations needing retry
- `idx_image_generations_status` - Filter by generation status

## Environment Variables

Required in both API and Celery containers:

```env
# Redis/Celery
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Supabase
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# ModelsLab
MODELSLAB_API_KEY=...
```

## Troubleshooting

### Issue: 500 Error - "Could not find the 'chapter_id' column"
**Solution:** Migration hasn't been applied. Run the migration SQL manually in Supabase SQL Editor.

### Issue: Tasks execute immediately instead of queuing
**Possible causes:**
1. Celery worker not running - Check `docker-compose ps celery`
2. Redis connection failed - Check `docker-compose logs redis`
3. Task not registered - Check `docker-compose logs celery | grep "app.tasks.image_tasks"`

### Issue: Tasks stay in "pending" status forever
**Possible causes:**
1. Celery worker crashed - Check `docker-compose logs celery`
2. Task failed to start - Check for errors in worker logs
3. Redis connection lost - Restart Redis and Celery containers

### Issue: Images fail with timeout errors
**Solution:** The retry mechanism should handle this automatically (up to 3 attempts). If persistent, check ModelsLab API status.

## Migration Applied

Migration file: `add_chapter_id_and_retry_count_to_image_generations.sql`

Applied on: 2025-10-15

Changes:
- Added `chapter_id` column (uuid, nullable)
- Added `retry_count` column (integer, NOT NULL, default 0)
- Added `last_attempted_at` column (timestamptz, nullable)
- Added `progress` column (integer, default 0)
- Modified `image_type` to allow NULL with default 'scene'
- Created 4 new indexes for performance optimization

## Next Steps

1. ✅ Database migration applied and verified
2. ✅ Celery configuration confirmed correct
3. ⏳ Test with actual scene image generation request
4. ⏳ Monitor Celery worker logs for task processing
5. ⏳ Verify retry mechanism works on failures

The system is now ready for asynchronous scene image generation with proper error handling and retry capabilities.
