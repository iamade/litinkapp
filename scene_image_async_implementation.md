# Scene Image Generation - Async Celery Implementation

## Overview
Successfully converted scene image generation from synchronous to asynchronous Celery-based architecture, matching the pattern used for character image generation.

## Problem Statement
- Scene generation was using async methods instead of synchronous Celery tasks
- Images were disappearing from frontend after generation completed
- Scene 2 failed with "Images cannot be generated at the moment, try use another model" error
- Architectural inconsistency between scene and character image generation

## Solution Implemented

### 1. Backend Changes

#### A. Celery Task (`/backend/app/tasks/image_tasks.py`)
Created `generate_scene_image_task` Celery task with:
- **Asynchronous execution**: Task queues scene image generation in background
- **Database tracking**: Creates and updates records in `image_generations` table
- **Retry logic**: Implements exponential backoff with jitter for retryable errors
- **Error handling**: Distinguishes between retryable and non-retryable errors
- **Metadata storage**: Preserves chapter_id, scene_number, script_id for retrieval
- **Status updates**: Tracks progress through pending → in_progress → completed/failed

Key features:
```python
@celery_app.task(bind=True)
def generate_scene_image_task(
    self,
    record_id: str,
    scene_description: str,
    scene_number: int,
    user_id: str,
    chapter_id: Optional[str] = None,
    script_id: Optional[str] = None,
    style: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    user_tier: Optional[str] = None,
    retry_count: int = 0
) -> None
```

#### B. API Endpoint (`/backend/app/api/v1/chapters.py`)
Updated `generate_scene_image` endpoint (lines 174-300):
- Creates pending record in `image_generations` table
- Queues Celery task with all required parameters
- Returns `ImageGenerationQueuedResponse` with task_id and record_id
- Handles errors gracefully with database rollback

#### C. Status Polling Endpoint (`/backend/app/api/v1/chapters.py`)
Created `get_scene_image_status` endpoint (lines 792-914):
- Endpoint: `GET /chapters/{chapter_id}/images/scenes/{scene_number}/status`
- Queries by chapter_id and scene_number (with metadata fallback)
- Returns current status, image_url, retry_count, error_message
- Verifies user authorization before returning data

#### D. Database Schema (`/backend/supabase/migrations/20251015_add_scene_fields_to_generations.sql`)
Added columns to `image_generations` table:
- `chapter_id` (uuid) - Links image to chapter
- `script_id` (uuid) - Links image to script
- `scene_number` (integer) - Scene number for retrieval
- `image_type` (text) - Distinguishes between scene/character images
- `retry_count` (integer) - Tracks retry attempts

Created indexes for efficient queries:
- `idx_image_generations_chapter_id`
- `idx_image_generations_scene_number_meta`
- `idx_image_generations_image_type`

### 2. Frontend Changes

#### A. Hook Updates (`/src/hooks/useImageGeneration.ts`)
Updated `generateSceneImage` function:
- Now handles async response with `record_id`
- Initiates polling via `startPollingSceneImage`
- No longer expects immediate image_url in response

Added `startPollingSceneImage` function:
- Polls status endpoint every 3 seconds
- Updates scene image state when completed/failed
- Clears polling interval on completion
- 5-minute timeout to prevent infinite polling
- Reloads all images from database for consistency

#### B. Service Updates (`/src/services/userService.ts`)
Updated `generateSceneImage` return type:
- Changed from `ImageGenerationResponse` to `ImageGenerationQueuedResponse`

Added `getSceneImageStatus` method:
```typescript
async getSceneImageStatus(
  chapterId: string,
  sceneNumber: number
): Promise<ImageStatusResponse>
```

### 3. Data Flow

#### Generation Flow:
1. User triggers scene image generation
2. Frontend calls `generateSceneImage` with scene data
3. Backend creates pending record in database
4. Backend queues Celery task with record_id
5. Backend returns immediately with task_id and record_id
6. Frontend starts polling status endpoint

#### Polling Flow:
1. Frontend polls status endpoint every 3 seconds
2. Backend queries database for latest status
3. When completed:
   - Frontend updates local state with image_url
   - Frontend reloads all images from database
   - Polling interval cleared
4. When failed:
   - Frontend marks as failed
   - Error message displayed
   - Polling interval cleared

#### Background Processing:
1. Celery worker picks up task from queue
2. Updates status to 'in_progress'
3. Calls ModelsLab V7 Image Service
4. On success:
   - Stores image_url in database
   - Updates metadata with generation details
   - Sets status to 'completed'
5. On failure:
   - Checks if error is retryable
   - If retryable and retry_count < 3:
     - Increments retry_count
     - Re-queues task with exponential backoff
   - Otherwise sets status to 'failed'

### 4. Error Handling

#### Retryable Errors:
- Network errors (timeout, connection)
- Rate limit errors (429)
- Service unavailable (503, 504)
- Temporary API failures

#### Non-Retryable Errors:
- Invalid parameters
- Authentication failures
- Permission errors
- Invalid scene descriptions

#### Retry Strategy:
- Max 3 retries
- Exponential backoff: 5s, 10s, 20s (with jitter)
- Retry count tracked in database
- Error details preserved in error_message field

### 5. Key Benefits

1. **Architectural Consistency**: Scene generation now matches character generation pattern
2. **Better Error Recovery**: Automatic retry for transient failures
3. **Improved Reliability**: Background processing prevents timeout issues
4. **Better UX**: Users see immediate feedback and progress updates
5. **Data Persistence**: All generation attempts tracked in database
6. **Frontend Resilience**: Polling ensures images don't "disappear"

### 6. Testing Checklist

- [x] Celery task executes successfully
- [x] Database records created and updated correctly
- [x] Status polling endpoint returns correct data
- [x] Frontend hook handles async responses
- [x] Retry logic works for transient failures
- [x] Error handling for non-retryable errors
- [x] Images persist and reload correctly
- [x] Metadata includes chapter_id, scene_number, script_id
- [x] Build succeeds without errors

## Files Modified

### Backend:
1. `/backend/app/tasks/image_tasks.py` - Added `generate_scene_image_task`
2. `/backend/app/api/v1/chapters.py` - Updated `generate_scene_image` and `get_scene_image_status` endpoints
3. `/backend/supabase/migrations/20251015_add_scene_fields_to_generations.sql` - Database schema updates

### Frontend:
1. `/src/hooks/useImageGeneration.ts` - Updated `generateSceneImage` and added `startPollingSceneImage`
2. `/src/services/userService.ts` - Updated return types and added `getSceneImageStatus`

### Schemas:
1. `/backend/app/schemas/image.py` - Schema definitions already in place

## Migration Notes

### Database Migration:
Run the migration to add required columns:
```sql
ALTER TABLE image_generations
  ADD COLUMN IF NOT EXISTS chapter_id uuid,
  ADD COLUMN IF NOT EXISTS script_id uuid,
  ADD COLUMN IF NOT EXISTS scene_number integer,
  ADD COLUMN IF NOT EXISTS image_type text NOT NULL DEFAULT 'scene',
  ADD COLUMN IF NOT EXISTS retry_count integer NOT NULL DEFAULT 0;
```

### Celery Workers:
Ensure Celery workers are running to process the new task:
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

## Future Enhancements

1. **Batch Generation**: Support generating multiple scenes in one request
2. **Priority Queue**: Allow priority scenes to be processed first
3. **Progress Tracking**: Report generation progress (0-100%)
4. **Webhook Support**: Notify external systems on completion
5. **Cost Tracking**: Track ModelsLab API costs per generation
6. **A/B Testing**: Compare different prompt strategies

## Notes

- The implementation fixes the "images disappearing" issue by properly storing chapter_id and scene_number
- The retry logic addresses the "Scene 2 failed" error by automatically retrying transient API failures
- The async architecture prevents timeout issues and provides better scalability
- All existing character image generation functionality remains unchanged
