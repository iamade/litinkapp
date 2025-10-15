# Scene Image Generation Fix - Applied

## Issue Summary
Scene images were generating generic wilderness/nature scenes instead of actual scenes from the book content. The generated images showed random landscapes rather than the specific scenes described in the book with the characters.

## Root Cause
The Celery task `generate_scene_image_task` was prioritizing the `custom_prompt` parameter (which contained only "Lighting mood: natural") over the actual `scene_description` parameter (which contained the full scene details from the book).

**Problem Code (line 928):**
```python
final_description = custom_prompt or scene_description
```

This meant that when `custom_prompt` was set, it completely replaced the scene description, causing the AI to generate images based only on "Lighting mood: natural" instead of the actual book content.

## Fix Applied
**File:** `/tmp/cc-agent/50548081/project/backend/app/tasks/image_tasks.py`
**Lines:** 926-942

Changed the logic to properly combine both parameters:

```python
# Generate the scene image using ModelsLab service
# ✅ FIX: Combine scene_description with custom_prompt instead of replacing it
# custom_prompt should enhance the description (e.g., "Lighting mood: natural")
# NOT replace the actual scene content from the book
if custom_prompt:
    final_description = f"{scene_description}. {custom_prompt}"
else:
    final_description = scene_description

logger.info(f"[SceneImageTask] Final prompt: {final_description[:100]}...")

result = asyncio.run(ModelsLabV7ImageService().generate_scene_image(
    scene_description=final_description,
    style=style or "cinematic",
    aspect_ratio=aspect_ratio or "16:9",
    user_tier=user_tier
))
```

## What This Fix Does

1. **Preserves Scene Content**: The actual scene description from the book is now always used as the primary content
2. **Enhances with Modifiers**: The custom_prompt (lighting mood) is appended to enhance the scene, not replace it
3. **Maintains Flexibility**: If no custom_prompt is provided, it uses just the scene description
4. **Better Logging**: Added logging to show the final prompt being used for debugging

## Expected Behavior After Fix

**Before Fix:**
- Prompt sent to AI: "Lighting mood: natural"
- Result: Generic nature/wilderness scene

**After Fix:**
- Prompt sent to AI: "[Actual scene from book describing characters, setting, action]. Lighting mood: natural"
- Result: Scene matching the book content with appropriate lighting mood applied

## Next Steps

1. **Restart Celery Worker**: The Celery worker needs to be restarted to pick up the code changes
   ```bash
   cd backend
   docker-compose restart celery_worker
   # OR
   docker compose restart celery_worker
   ```

2. **Test Scene Generation**: Generate a new scene image and verify:
   - The Celery logs show the full scene description in the prompt
   - The generated image matches the book's scene content
   - Characters and settings from the book are visible
   - Lighting mood preferences are applied but don't override the content

3. **Monitor Logs**: Check the Celery logs for the new log line:
   ```
   [SceneImageTask] Final prompt: [full scene description]...
   ```

## Technical Details

### Data Flow
1. **Frontend** (`useImageGeneration.ts`):
   - Sends `scene_description`: Full scene text from book
   - Sends `custom_prompt`: "Lighting mood: {mood}"

2. **Backend API** (`chapters.py`):
   - Receives both parameters
   - Creates database record
   - Queues Celery task with both parameters

3. **Celery Task** (`image_tasks.py`):
   - ✅ **FIXED**: Now combines scene_description + custom_prompt
   - Sends enhanced prompt to ModelsLab V7 service

4. **ModelsLab V7** (`modelslab_v7_image_service.py`):
   - Receives full prompt with scene details
   - Generates image matching the description

## Verification

After restarting the Celery worker, the logs should show:
```
[SceneImageTask] Starting generation for scene {N}
[SceneImageTask] Parameters: user={id}, chapter={id}, script={id}, record={id}, tier=free, retry=0
[SceneImageTask] Final prompt: {Full scene description from book}. Lighting mood: natural...
[MODELSLAB V7 IMAGE] Prompt: Scene: {Full scene description from book}. Lighting mood: natural...
```

Instead of the previous incorrect logs:
```
[SCENE IMAGE] Generating cinematic scene: Lighting mood: natural...
[MODELSLAB V7 IMAGE] Prompt: Scene: Lighting mood: natural...
```

## Impact
- ✅ Scene images will now match the book content
- ✅ Characters from the book will appear in scenes
- ✅ Settings and environments will match the book descriptions
- ✅ Lighting preferences are still respected but as enhancements
- ✅ No breaking changes to API or frontend
