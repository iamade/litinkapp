from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional

from app.api.services.video import VideoService
from app.core.database import async_session, engine
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.videos.models import VideoGeneration, VideoSegment
from app.subscriptions.models import UserSubscription
from app.core.model_config import get_model_config, ModelConfig
import json
import subprocess
import os
import requests
import tempfile
import uuid
from app.core.services.file import FileService

from app.core.services.modelslab_v7_video import ModelsLabV7VideoService


# Removed image generation logic


# Removed scene image generation logic


async def extract_scene_dialogue_and_generate_audio(
    video_gen_id: str,
    scene_id: str,
    scene_description: str,
    script_data: Dict[str, Any],
    user_id: str = None,
    session: AsyncSession = None,
) -> Dict[str, Any]:
    """Extract dialogue for a specific scene and generate audio"""

    try:
        # Get the full script from script_data
        script = script_data.get("script", "")
        if not script:
            print(
                f"[DIALOGUE EXTRACTION] No script found for video generation {video_gen_id}"
            )
            return {"dialogue_audio": []}

        # Get scene descriptions for context
        scene_descriptions = script_data.get("scene_descriptions", [])

        # Initialize video service for dialogue extraction
        if not session:
            raise Exception(
                "Session required for extract_scene_dialogue_and_generate_audio"
            )
        video_service = VideoService(session)

        # Extract dialogue per scene
        dialogue_data = await video_service.extract_dialogue_per_scene(
            script=script, scene_descriptions=scene_descriptions, user_id=user_id
        )

        # Get dialogue for this specific scene
        scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1
        scene_dialogues = dialogue_data.get("scene_dialogues", {}).get(scene_number, [])
        scene_audio_files = dialogue_data.get("scene_audio_files", {}).get(
            scene_number, []
        )

        print(
            f"[DIALOGUE EXTRACTION] Scene {scene_number}: {len(scene_dialogues)} dialogues, {len(scene_audio_files)} audio files"
        )

        # Store dialogue audio in database for tracking
        # Store dialogue audio in database for tracking
        for audio_file in scene_audio_files:
            try:
                # Using raw SQL for insert if VideoSegment model usage is complex or to match existing pattern
                # But better to use model if possible.
                # Let's use raw SQL insert for now to be safe with existing schema

                insert_query = text(
                    """
                    INSERT INTO video_segments (
                        video_generation_id, scene_id, segment_index, scene_description,
                        audio_url, character_name, dialogue_text, generation_method,
                        status, processing_service, metadata
                    ) VALUES (
                        :video_generation_id, :scene_id, :segment_index, :scene_description,
                        :audio_url, :character_name, :dialogue_text, :generation_method,
                        :status, :processing_service, :metadata
                    )
                """
                )

                await session.execute(
                    insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "segment_index": scene_number,
                        "scene_description": scene_description,
                        "audio_url": audio_file.get("audio_url"),
                        "character_name": audio_file.get("character"),
                        "dialogue_text": audio_file.get("text"),
                        "generation_method": "character_dialogue_audio",
                        "status": "completed",
                        "processing_service": "elevenlabs",
                        "metadata": json.dumps(
                            {
                                "character_profile": audio_file.get(
                                    "character_profile", {}
                                ),
                                "scene_number": scene_number,
                                "dialogue_type": "character_voice",
                            }
                        ),
                    },
                )
                await session.commit()
            except Exception as db_error:
                print(f"[DIALOGUE EXTRACTION] Error storing dialogue audio: {db_error}")

        return {
            "dialogue_audio": scene_audio_files,
            "dialogue_count": len(scene_dialogues),
            "audio_count": len(scene_audio_files),
            "scene_number": scene_number,
        }

    except Exception as e:
        print(
            f"[DIALOGUE EXTRACTION] Error extracting dialogue for scene {scene_id}: {e}"
        )
        return {"dialogue_audio": [], "error": str(e)}


async def extract_last_frame(
    video_url: str, user_id: Optional[str] = None
) -> Optional[str]:
    """
    Extract the last frame from a video for use as the starting image of the next scene.
    This helps maintain visual continuity between scenes.

    Args:
        video_url: URL of the video to extract frame from
        user_id: Optional user ID for storage organization

    Returns:
        URL of the extracted frame image, or None if extraction fails
    """
    import tempfile
    import subprocess
    import os
    import httpx
    from app.core.services.supabase_storage import SupabaseStorageService

    try:
        print(f"[LAST FRAME] Extracting last frame from video: {video_url[:50]}...")

        # Download video to temp file
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            if response.status_code != 200:
                print(f"[LAST FRAME] Failed to download video: {response.status_code}")
                return None

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_file.write(response.content)
            video_path = video_file.name

        frame_path = video_path.replace(".mp4", "_last_frame.jpg")

        try:
            # Extract last frame using ffmpeg
            # First, get video duration
            probe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 5.0

            # Extract frame at last second
            seek_time = max(0, duration - 0.1)  # 0.1 seconds before end
            extract_cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(seek_time),
                "-i",
                video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",
                frame_path,
            ]
            subprocess.run(extract_cmd, capture_output=True, check=True)

            if not os.path.exists(frame_path):
                print("[LAST FRAME] Frame extraction failed - no output file")
                return None

            # Upload to storage
            storage_service = SupabaseStorageService()
            with open(frame_path, "rb") as f:
                frame_data = f.read()

            # Generate unique filename
            import uuid as uuid_lib

            frame_filename = f"frames/{user_id or 'system'}/last_frame_{uuid_lib.uuid4().hex[:8]}.jpg"

            frame_url = await storage_service.upload_file(
                file_data=frame_data,
                file_path=frame_filename,
                content_type="image/jpeg",
            )

            print(f"[LAST FRAME] ✅ Extracted and uploaded frame: {frame_url[:50]}...")
            return frame_url

        finally:
            # Clean up temp files
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(frame_path):
                os.unlink(frame_path)

    except Exception as e:
        print(f"[LAST FRAME] ❌ Error extracting frame: {e}")
        return None


async def upscale_frame(
    image_url: str, user_tier: str = "BASIC", user_id: Optional[str] = None
) -> str:
    """
    Upscale an extracted frame before using it as video input.
    Uses tier-based upscaling models from UPSCALE_MODEL_CONFIG.

    Args:
        image_url: URL of the image to upscale
        user_tier: User's subscription tier for model selection
        user_id: Optional user ID for storage organization

    Returns:
        URL of the upscaled image, or original URL if upscaling fails
    """
    from app.core.model_config import UPSCALE_MODEL_CONFIG, ModelTier

    try:
        print(f"[UPSCALE] Upscaling frame for tier: {user_tier}")

        # Get model config based on tier
        tier_enum = ModelTier[user_tier.upper()] if user_tier else ModelTier.BASIC
        upscale_config = UPSCALE_MODEL_CONFIG.get(
            tier_enum, UPSCALE_MODEL_CONFIG[ModelTier.BASIC]
        )
        model_id = upscale_config.primary

        # Use ModelsLab upscaling service
        from app.core.services.modelslab_upscale import ModelsLabUpscaleService

        upscale_service = ModelsLabUpscaleService()
        result = await upscale_service.upscale_image(
            image_url=image_url,
            model_id=model_id,
            scale=2,  # 2x upscaling is usually sufficient
        )

        if result.get("status") == "success" and result.get("upscaled_url"):
            print(f"[UPSCALE] ✅ Frame upscaled successfully")
            return result["upscaled_url"]
        else:
            print(
                f"[UPSCALE] ⚠️ Upscaling failed, using original: {result.get('error')}"
            )
            return image_url

    except Exception as e:
        print(f"[UPSCALE] ❌ Error upscaling frame: {e}, using original")
        return image_url


def find_scene_audio(
    scene_id: str, audio_files: Dict[str, Any], script_style: str = None
) -> Optional[Dict[str, Any]]:
    """Find audio for a scene with progressive fallback.

    Priority: exact scene match (character > narrator > any type) > any available audio.
    """

    scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1

    # Collect all audio across all types
    all_audio = []
    for audio_type in ["characters", "narrator", "sound_effects", "background_music"]:
        all_audio.extend(audio_files.get(audio_type, []))

    print(
        f"[FIND AUDIO] Looking for audio for {scene_id} (scene_number={scene_number}), total audio files: {len(all_audio)}"
    )

    # Priority 1: Exact scene match in character audio
    for audio in audio_files.get("characters", []):
        if audio.get("scene") == scene_number and audio.get("audio_url"):
            print(f"[FIND AUDIO] Found character audio for {scene_id}")
            return audio

    # Priority 2: Exact scene match in narrator audio
    for audio in audio_files.get("narrator", []):
        if audio.get("scene") == scene_number and audio.get("audio_url"):
            print(f"[FIND AUDIO] Found narrator audio for {scene_id}")
            return audio

    # Priority 3: Exact scene match in any type
    for audio in all_audio:
        if audio.get("scene") == scene_number and audio.get("audio_url"):
            print(
                f"[FIND AUDIO] Found audio (type={audio.get('audio_type')}) for {scene_id}"
            )
            return audio

    # Priority 4: Any audio with a URL (fallback when sequence_order doesn't match scene)
    for audio in all_audio:
        if audio.get("audio_url"):
            print(
                f"[AUDIO FALLBACK] Using audio id={audio.get('id')} (scene={audio.get('scene')}) for {scene_id}"
            )
            return audio

    print(f"[FIND AUDIO] No audio found for {scene_id}")
    return None


async def update_pipeline_step(
    video_generation_id: str,
    step_name: str,
    status: str,
    error_message: str = None,
    session: AsyncSession = None,
):
    """Update pipeline step status"""
    try:
        if not session:
            print(
                f"[PIPELINE ERROR] No session provided for update_pipeline_step {step_name}"
            )
            return

        update_data = {
            "status": status,
            "video_generation_id": video_generation_id,
            "step_name": step_name,
        }

        set_clauses = ["status = :status"]

        if status == "processing":
            set_clauses.append("started_at = NOW()")
        elif status in ["completed", "failed"]:
            set_clauses.append("completed_at = NOW()")

        if error_message:
            set_clauses.append("error_message = :error_message")
            update_data["error_message"] = error_message

        set_clause_str = ", ".join(set_clauses)

        update_query = text(
            f"""
            UPDATE pipeline_steps 
            SET {set_clause_str}
            WHERE video_generation_id = :video_generation_id AND step_name = :step_name
        """
        )

        await session.execute(update_query, update_data)
        await session.commit()

        print(f"[PIPELINE] Updated step {step_name} to {status}")

    except Exception as e:
        print(f"[PIPELINE] Error updating step {step_name}: {e}")
        if session:
            try:
                await session.rollback()
            except Exception:
                pass


@celery_app.task(bind=True)
def generate_all_videos_for_generation(self, video_generation_id: str):
    """Main task to generate all videos for a video generation with automatic retry"""
    return asyncio.run(async_generate_all_videos_for_generation(video_generation_id))


async def async_generate_all_videos_for_generation(video_generation_id: str):
    """Async implementation of video generation task"""
    async with async_session() as session:
        try:
            print(
                f"[VIDEO GENERATION] Starting video generation for: {video_generation_id}"
            )

            # ✅ Update pipeline step to processing
            await update_pipeline_step(
                video_generation_id, "video_generation", "processing", session=session
            )

            # Get video generation data
            # Using raw SQL
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            # Convert to dict for easier access (and compatibility with existing code)
            video_gen = dict(video_gen_record)
            user_id = video_gen.get("user_id")

            # Update status and initialize retry tracking
            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'generating_video',
                    retry_count = 0,
                    can_resume = true
                WHERE id = :id
            """
            )
            await session.execute(update_query, {"id": video_generation_id})
            await session.commit()

            # Get user subscription tier for model config
            user_tier = "free"
            async with session.begin_nested():  # Use nested transaction or just query
                # Re-using session within transaction is fine
                pass

            # Simple query for subscription
            sub_query = text(
                "SELECT tier FROM user_subscriptions WHERE user_id = :user_id"
            )
            sub_result = await session.execute(sub_query, {"user_id": user_id})
            sub_record = sub_result.first()
            if sub_record:
                user_tier = sub_record[0]

            # Get Video Model Config
            video_config = get_model_config("video", user_tier)
            print(f"[VIDEO CONFIG] Tier: {user_tier}, Config: {video_config}")

            # Get script data and generated assets
            script_data = video_gen.get("script_data", {})
            audio_files = video_gen.get("audio_files", {})
            image_data = video_gen.get("image_data", {})

            scene_descriptions = script_data.get("scene_descriptions", [])
            characters = script_data.get("characters", [])
            video_style = script_data.get("video_style", "realistic")

            # Read task_meta for selection filters
            task_meta = video_gen.get("task_meta", {}) or {}
            print(f"[VIDEO GENERATION] task_meta keys: {list(task_meta.keys())}")
            if task_meta.get("selected_shot_ids"):
                print(
                    f"[VIDEO GENERATION] selected_shot_ids: {task_meta['selected_shot_ids']}"
                )
            if task_meta.get("selected_audio_ids"):
                print(
                    f"[VIDEO GENERATION] selected_audio_ids: {task_meta['selected_audio_ids']}"
                )

            # Save original scene_descriptions before any filtering
            # (needed for correct indexing when building target lists)
            original_scene_descriptions = list(scene_descriptions)

            # Filter scene_descriptions by selected scenes from task_meta
            if task_meta.get("selected_shot_ids"):
                selected_shot_ids = task_meta["selected_shot_ids"]
                # Parse scene numbers from composite frontend IDs
                # Format: "scene-{timestamp}-{index}-{scriptId}" where index is 0-based
                selected_scene_indices = []
                for shot_id in selected_shot_ids:
                    try:
                        if isinstance(shot_id, str) and shot_id.startswith("scene-"):
                            parts = shot_id.split("-")
                            if len(parts) >= 3:
                                scene_index = int(parts[2])  # 0-based index
                                selected_scene_indices.append(scene_index)
                    except (ValueError, IndexError) as e:
                        print(
                            f"[VIDEO GENERATION] Could not parse shot ID {shot_id}: {e}"
                        )

                if selected_scene_indices:
                    # Filter scene_descriptions to only selected scenes
                    filtered_descriptions = []
                    for idx in sorted(set(selected_scene_indices)):
                        if idx < len(original_scene_descriptions):
                            filtered_descriptions.append(
                                original_scene_descriptions[idx]
                            )

                    print(
                        f"[VIDEO GENERATION] Filtered scenes: {len(filtered_descriptions)} of {len(original_scene_descriptions)} (indices: {selected_scene_indices})"
                    )
                    scene_descriptions = filtered_descriptions
                else:
                    print(
                        f"[VIDEO GENERATION] No valid scene indices parsed, using all {len(scene_descriptions)} scenes"
                    )
            else:
                print(
                    f"[VIDEO GENERATION] No selected_shot_ids in task_meta, using all {len(scene_descriptions)} scenes"
                )

            print(f"[VIDEO GENERATION] Processing:")
            print(f"- Scenes: {len(scene_descriptions)}")
            print(f"- Characters: {len(characters)}")
            print(f"- Video Style: {video_style}")

            # Detailed audio logging
            narrator_count = len(audio_files.get("narrator", []))
            character_count = len(audio_files.get("characters", []))
            sfx_count = len(audio_files.get("sound_effects", []))
            music_count = len(audio_files.get("background_music", []))
            print(
                f"- Audio Files: narrator={narrator_count}, characters={character_count}, sfx={sfx_count}, music={music_count}"
            )
            for audio_type, items in audio_files.items():
                for item in items:
                    print(
                        f"  [{audio_type}] id={item.get('id', 'N/A')}, scene={item.get('scene_number', '?')}, url={'yes' if item.get('url') or item.get('audio_url') else 'NO'}"
                    )

            # Log image data and prompts
            img_images = image_data.get("images", {})
            scene_imgs = img_images.get(
                "scene_images", image_data.get("scene_images", [])
            )
            print(f"- Scene Images: {len(scene_imgs)}")
            for img in scene_imgs:
                prompt_preview = (img.get("prompt", "") or "")[:80]
                print(
                    f"  [scene] id={img.get('id', 'N/A')}, scene_num={img.get('scene_number', '?')}, prompt={prompt_preview!r}"
                )

            # Use pre-generated scene images directly from image_data
            # (images were already stored by routes.py from ImageGeneration records)
            img_images = image_data.get("images", {})
            pre_gen_scene_images = img_images.get("scene_images", [])
            pre_gen_character_images = img_images.get("character_images", [])

            print(
                f"[IMAGE SELECTION] Pre-generated scene images: {len(pre_gen_scene_images)}"
            )
            print(
                f"[IMAGE SELECTION] Pre-generated character images: {len(pre_gen_character_images)}"
            )

            # Build scene_images list from pre-generated images
            # Map by scene_number for easy lookup
            scene_image_map = {}
            for img in pre_gen_scene_images:
                scene_num = img.get("scene_number", 0)
                scene_image_map[scene_num] = img

            print(f"[IMAGE MAPPING] Map keys: {list(scene_image_map.keys())}")

            # If we have selected scene indices, build images matching the filtered scene_descriptions
            target_scene_descriptions = []
            target_scene_numbers = []

            if task_meta.get("selected_shot_ids"):
                # Use the same selected_scene_indices we computed earlier
                final_scene_images = []
                sorted_indices = sorted(set(selected_scene_indices))

                for idx in sorted_indices:
                    scene_num = idx + 1  # Convert 0-based index to 1-based scene_number

                    # Add description and number for generation targets
                    # Use original_scene_descriptions (not the filtered one) since idx is an index into the original list
                    if idx < len(original_scene_descriptions):
                        target_scene_descriptions.append(
                            original_scene_descriptions[idx]
                        )
                        target_scene_numbers.append(scene_num)

                    # Handle image selection - Try exact match (1-based), then 0-based
                    if scene_num in scene_image_map:
                        final_scene_images.append(scene_image_map[scene_num])
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: using pre-generated image (1-based match)"
                        )
                    elif idx in scene_image_map:  # Try 0-based index match
                        final_scene_images.append(scene_image_map[idx])
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: using pre-generated image (0-based match with {idx})"
                        )
                    elif pre_gen_scene_images:
                        # Fallback to first available image
                        # Intelligent fallback: try to find any image that hasn't been used, or just cycle
                        fallback_img = pre_gen_scene_images[
                            idx % len(pre_gen_scene_images)
                        ]
                        final_scene_images.append(fallback_img)
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: using fallback image (index match)"
                        )
                    else:
                        final_scene_images.append(None)
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: ⚠️ no image available"
                        )
                image_data["scene_images"] = final_scene_images
            else:
                # No selection filter: assign images by order or scene_number
                target_scene_descriptions = scene_descriptions
                target_scene_numbers = list(range(1, len(scene_descriptions) + 1))

                final_scene_images = []
                for i in range(len(scene_descriptions)):
                    scene_num = i + 1

                    if scene_num in scene_image_map:
                        final_scene_images.append(scene_image_map[scene_num])
                        print(f"[IMAGE SELECTION] Scene {scene_num}: 1-based match")
                    elif i in scene_image_map:
                        final_scene_images.append(scene_image_map[i])
                        print(f"[IMAGE SELECTION] Scene {scene_num}: 0-based match")
                    elif i < len(pre_gen_scene_images):
                        final_scene_images.append(pre_gen_scene_images[i])
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: sequential fallback"
                        )
                    elif pre_gen_character_images:
                        char_img = pre_gen_character_images[
                            i % len(pre_gen_character_images)
                        ]
                        final_scene_images.append(char_img)
                        print(
                            f"[IMAGE SELECTION] Scene {scene_num}: character image fallback"
                        )
                    else:
                        # Fallback to ANY generated image if list exists but indices don't match
                        if pre_gen_scene_images:
                            final_scene_images.append(pre_gen_scene_images[0])
                            print(
                                f"[IMAGE SELECTION] Scene {scene_num}: desperate fallback to first image"
                            )
                        else:
                            final_scene_images.append(None)
                            print(
                                f"[IMAGE SELECTION] Scene {scene_num}: ⚠️ no image available"
                            )

                image_data["scene_images"] = final_scene_images

            scene_count = len(
                [img for img in image_data.get("scene_images", []) if img is not None]
            )
            print(f"[IMAGE SELECTION SUMMARY]")
            print(
                f"- Total scene images assigned: {scene_count} / {len(target_scene_descriptions)} target scenes"
            )

            # Generate videos
            modelslab_service = ModelsLabV7VideoService()

            # Generate scene videos sequentially with key scene shots
            video_results = await generate_scene_videos(
                modelslab_service,
                video_generation_id,
                target_scene_descriptions,
                audio_files,
                image_data,
                video_style,
                script_data,
                user_id,
                model_config=video_config,
                session=session,
                scene_numbers=target_scene_numbers,
            )

            # Compile results
            successful_videos = len([r for r in video_results if r is not None])
            total_scenes = len(scene_descriptions)
            success_rate = (
                (successful_videos / total_scenes * 100) if total_scenes > 0 else 0
            )

            # Calculate total video duration
            total_duration = sum(
                [v.get("duration", 0) for v in video_results if v is not None]
            )

            # Get the first successful video URL for the video_url column
            first_video_url = None
            for vr in video_results:
                if vr is not None and vr.get("video_url"):
                    first_video_url = vr["video_url"]
                    break

            # Update video generation with video data
            video_data_result = {
                "scene_videos": video_results,
                "statistics": {
                    "total_scenes": total_scenes,
                    "videos_generated": successful_videos,
                    "total_duration": total_duration,
                    "success_rate": round(success_rate, 2),
                },
            }

            update_query = text(
                """
                UPDATE video_generations
                SET video_data = :video_data,
                    generation_status = :status,
                    error_message = :error_message,
                    video_url = :video_url
                WHERE id = :id
            """
            )

            # If 0 videos were generated, this is a failure — no video_url will be produced
            if successful_videos == 0:
                final_status = "failed"
                error_msg = f"Video generation failed: 0 out of {total_scenes} scene videos were created. Check image availability and ModelsLab API."
                print(f"[VIDEO GENERATION FAILED] {error_msg}")
            else:
                final_status = "video_completed"
                error_msg = None
                print(
                    f"[VIDEO URL] Saving video_url={first_video_url} to video_generation {video_generation_id}"
                )

            await session.execute(
                update_query,
                {
                    "video_data": json.dumps(video_data_result),
                    "status": final_status,
                    "error_message": error_msg,
                    "video_url": first_video_url,
                    "id": video_generation_id,
                },
            )
            await session.commit()

            # Update pipeline step based on result
            if successful_videos > 0:
                await update_pipeline_step(
                    video_generation_id,
                    "video_generation",
                    "completed",
                    session=session,
                )
            else:
                await update_pipeline_step(
                    video_generation_id,
                    "video_generation",
                    "failed",
                    error_msg,
                    session=session,
                )

            success_message = f"Video generation completed! {successful_videos} videos created for {total_scenes} scenes"
            print(
                f"[VIDEO GENERATION {'SUCCESS' if successful_videos > 0 else 'FAILED'}] {success_message}"
            )

            # Log detailed breakdown
            print(f"[VIDEO STATISTICS]")
            print(
                f"- Scene-by-scene generation status: {successful_videos}/{total_scenes}"
            )
            print(f"- Total video duration: {total_duration:.1f} seconds")
            print(f"- Success rate: {success_rate:.1f}%")

            # Video generation complete — merging is handled separately in the Merge tab
            print(
                f"[PIPELINE] Video generation complete. User can merge in the Merge tab."
            )

            return {
                "status": final_status,
                "message": success_message
                + (" - Videos ready for review." if final_status != "failed" else ""),
                "statistics": video_data_result["statistics"],
                "video_results": video_results,
                "next_step": None,
            }

        except Exception as e:
            error_message = f"Video generation failed: {str(e)}"
            print(f"[VIDEO GENERATION ERROR] {error_message}")

            # Rollback any failed transaction before attempting error updates
            try:
                await session.rollback()
            except Exception:
                pass

            # ✅ Update pipeline step to failed
            await update_pipeline_step(
                video_generation_id,
                "video_generation",
                "failed",
                error_message,
                session=session,
            )

            # Check if this is a video retrieval failure that can be retried
            is_retrieval_failure = any(
                keyword in str(e).lower()
                for keyword in [
                    "retrieval",
                    "download",
                    "url",
                    "video_url",
                    "future_links",
                    "fetch_result",
                ]
            )

            if is_retrieval_failure:
                print(
                    f"[VIDEO GENERATION] Video retrieval failure detected, scheduling automatic retry"
                )

                # Update status to indicate retry will be attempted
                # Update status to indicate retry will be attempted
                try:
                    update_query = text(
                        """
                        UPDATE video_generations 
                        SET generation_status = 'retrieval_failed', 
                            error_message = :error_message, 
                            can_resume = true 
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        update_query,
                        {
                            "error_message": f"Video retrieval failed, automatic retry scheduled: {str(e)}",
                            "id": video_generation_id,
                        },
                    )
                    await session.commit()

                    # Schedule automatic retry with initial delay
                    automatic_video_retry_task.apply_async(
                        args=[video_generation_id],
                        countdown=30,  # 30 seconds initial delay
                    )

                    print(
                        f"[VIDEO GENERATION] ✅ Automatic retry scheduled for video generation {video_generation_id}"
                    )

                    return {
                        "status": "retry_scheduled",
                        "message": "Video retrieval failed, automatic retry scheduled",
                        "video_generation_id": video_generation_id,
                        "retry_delay": 30,
                    }

                except Exception as retry_error:
                    print(
                        f"[VIDEO GENERATION] Failed to schedule automatic retry: {retry_error}"
                    )
                    # Fall through to regular error handling

        # Regular error handling for non-retrieval failures
        try:
            await session.rollback()
            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'failed',
                    error_message = :error_message
                WHERE id = :id
            """
            )
            await session.execute(
                update_query,
                {"error_message": error_message, "id": video_generation_id},
            )
            await session.commit()
        except:
            pass

        raise Exception(error_message)


async def extract_last_frame(video_url: str, user_id: str) -> Optional[str]:
    """
    Extract the last frame from a video URL and upload it to storage.
    Returns the URL of the extracted image.
    """
    try:
        print(f"[FRAME EXTRACTION] Extracting last frame from {video_url}")

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            video_path = temp_video.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
            image_path = temp_image.name

        # Download video
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract last frame using ffmpeg
        # -sseof -3: seek to 3 seconds before end (to ensure we locate valid frames)
        # -update 1: overwrite output
        # -q:v 2: high quality
        cmd = [
            "ffmpeg",
            "-sseof",
            "-1",  # Look at the very end
            "-i",
            video_path,
            "-update",
            "1",
            "-q:v",
            "2",
            "-y",
            image_path,
        ]

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )

        # Upload extracted frame
        file_service = FileService()
        result = await file_service.upload_file(
            file_path=image_path,
            file_name=f"last_frame_{uuid.uuid4()}.jpg",
            content_type="image/jpeg",
            user_id=user_id,
            folder="video_frames",
        )

        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(image_path):
            os.remove(image_path)

        return result.get("url")

    except Exception as e:
        print(f"[FRAME EXTRACTION ERROR] {e}")
        # Cleanup on error
        if "video_path" in locals() and os.path.exists(video_path):
            os.remove(video_path)
        if "image_path" in locals() and os.path.exists(image_path):
            os.remove(image_path)
        return None


async def generate_scene_videos(
    modelslab_service: ModelsLabV7VideoService,  # ✅ Updated type hint
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str,
    script_data: Dict[str, Any] = None,
    user_id: str = None,
    model_config: Optional[ModelConfig] = None,
    session: AsyncSession = None,
    scene_numbers: List[int] = None,
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using V7 Veo 2 image-to-video with sequential processing and key scene shots"""

    print(
        f"[SCENE VIDEOS V7] Generating scene videos sequentially with key scene shots..."
    )
    video_results = []
    if not session:
        raise Exception("Session required for generate_scene_videos")

    scene_images = image_data.get("scene_images", [])  # Fixed key mismatch

    # Determine Model ID from Config or fallback
    primary_model_id = "seedance-1-5-pro"  # Default fallback
    if model_config and model_config.primary:
        primary_model_id = model_config.primary

    print(f"[SCENE VIDEOS] Using Primary Model: {primary_model_id}")

    # Parse script for enhanced prompt generation if script data is available
    parsed_components = None
    if script_data and script_data.get("script"):
        try:
            from app.api.services.script_parser import ScriptParser

            script_parser = ScriptParser()
            characters = script_data.get("characters", [])
            parsed_components = script_parser.parse_script_for_video_prompt(
                script=script_data["script"], characters=characters
            )
            print(f"[SCENE VIDEOS V7] ✅ Parsed script for enhanced prompt generation:")
            print(
                f"- Camera movements: {len(parsed_components.get('camera_movements', []))}"
            )
            print(
                f"- Character actions: {len(parsed_components.get('character_actions', []))}"
            )
            print(
                f"- Character dialogues: {len(parsed_components.get('character_dialogues', []))}"
            )
        except Exception as e:
            print(
                f"[SCENE VIDEOS V7] ⚠️ Failed to parse script for enhanced prompts: {e}"
            )

    # Track the previous scene's key scene shot for continuity
    previous_key_scene_shot = None

    for i, scene_description in enumerate(scene_descriptions):
        try:
            # Determine correct scene ID (1-based)
            if scene_numbers and i < len(scene_numbers):
                scene_num = scene_numbers[i]
                scene_id = f"scene_{scene_num}"
            else:
                scene_id = f"scene_{i+1}"

            print(
                f"[SCENE VIDEOS V7] Processing {scene_id} ({i+1}/{len(scene_descriptions)})"
            )

            # Determine the starting image for this scene
            starting_image_url = None

            if i == 0:
                # First scene: use the original scene image
                scene_image = None
                if i < len(scene_images) and scene_images[i] is not None:
                    scene_image = scene_images[i]

                if not scene_image or not scene_image.get("image_url"):
                    print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                    video_results.append(None)
                    continue

                starting_image_url = scene_image["image_url"]
                print(f"[SCENE VIDEOS V7] Using original scene image for {scene_id}")
            else:
                # Subsequent scenes: use the previous scene's key scene shot
                if previous_key_scene_shot:
                    starting_image_url = previous_key_scene_shot
                    print(
                        f"[SCENE VIDEOS V7] Using previous key scene shot for {scene_id}: {starting_image_url}"
                    )
                else:
                    # Fallback to original scene image if no previous key scene shot
                    scene_image = None
                    if i < len(scene_images) and scene_images[i] is not None:
                        scene_image = scene_images[i]

                    if scene_image and scene_image.get("image_url"):
                        starting_image_url = scene_image["image_url"]
                        print(
                            f"[SCENE VIDEOS V7] Using fallback scene image for {scene_id} (no previous key scene shot)"
                        )
                    else:
                        print(
                            f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}"
                        )
                        video_results.append(None)
                        continue

            # Determine model ID before audio check (needed for duration limits)
            current_model_id = primary_model_id

            # Find audio for lip sync / audio-reactive
            scene_audio = find_scene_audio(scene_id, audio_files)
            init_audio_url = None

            if scene_audio:
                audio_duration = scene_audio.get("duration", 0)
                max_audio = modelslab_service.get_max_audio_duration(current_model_id)

                if max_audio and audio_duration > 0 and audio_duration > max_audio:
                    print(
                        f"[SCENE AUDIO] {scene_id}: audio duration ({audio_duration}s) exceeds "
                        f"{current_model_id} limit ({max_audio}s), skipping init_audio"
                    )
                else:
                    init_audio_url = scene_audio.get("audio_url")
                    print(
                        f"[SCENE AUDIO] {scene_id}: using audio id={scene_audio.get('id')}, "
                        f"type={scene_audio.get('audio_type')}, duration={audio_duration}s, "
                        f"model={current_model_id} (limit={max_audio}s)"
                    )
            else:
                print(
                    f"[SCENE AUDIO] {scene_id}: no audio selected, generating without init_audio"
                )

            # Decide on Model: Dialogue (Audio) vs Narration (Visual Only)
            # If we have init_audio, we MIGHT want to use a specific lip-sync capable model if the primary isn't one
            # But per plan, tiers like Standard+ use Omni/Wan which support it.
            # Free/Basic might use seedance (no lip sync) or wan2.5 (lip sync).

            logger_msg = f"[SCENE VIDEOS V7] Generating video for {scene_id} using {current_model_id}"
            if init_audio_url:
                logger_msg += " with Audio Reactive/Lip Sync"
            print(logger_msg)

            # Build enhanced video prompt using image generation prompt if available
            scene_image_for_prompt = None
            if i < len(scene_images) and scene_images[i] is not None:
                scene_image_for_prompt = scene_images[i]

            image_prompt = (
                scene_image_for_prompt.get("prompt", "")
                if scene_image_for_prompt
                else ""
            )

            if image_prompt and image_prompt.strip():
                # Combine scene description with image prompt for richer video generation
                enhanced_prompt = f"{scene_description}. Visual style: {image_prompt}"
                print(
                    f"[SCENE VIDEOS V7] Using enhanced prompt with image prompt for {scene_id}"
                )
            else:
                enhanced_prompt = scene_description
                print(
                    f"[SCENE VIDEOS V7] No image prompt available, using scene description for {scene_id}"
                )

            # ✅ Generate video using ModelsLab Service
            result = await modelslab_service.generate_image_to_video(
                image_url=starting_image_url,
                prompt=enhanced_prompt,
                model_id=current_model_id,
                negative_prompt="",
                init_audio=init_audio_url if init_audio_url else None,
            )

            # Process result (Adapt old verify logic to new direct call result)
            # generate_image_to_video returns dict with status/video_url or error

            if result.get("status") == "success":
                video_url = result.get("video_url")
                has_lipsync = bool(init_audio_url)

                if video_url:
                    # Extract the last frame as key scene shot for the next scene
                    key_scene_shot_url = None
                    try:
                        key_scene_shot_url = await extract_last_frame(
                            video_url, user_id
                        )

                        if key_scene_shot_url:
                            print(
                                f"[SCENE VIDEOS V7] ✅ Extracted key scene shot for {scene_id}: {key_scene_shot_url}"
                            )
                            previous_key_scene_shot = (
                                key_scene_shot_url  # Update for next scene
                            )
                        else:
                            print(
                                f"[SCENE VIDEOS V7] ⚠️ Failed to extract key scene shot for {scene_id}"
                            )
                    except Exception as frame_error:
                        print(
                            f"[SCENE VIDEOS V7] ⚠️ Error extracting key scene shot for {scene_id}: {frame_error}"
                        )

                    # Store in database
                    try:
                        insert_query = text(
                            """
                            INSERT INTO video_segments (
                                video_generation_id, scene_id, scene_number, scene_description,
                                video_url, status, target_duration
                            ) VALUES (
                                :video_generation_id, :scene_id, :scene_number, :scene_description,
                                :video_url, :status, :target_duration
                            ) RETURNING id
                        """
                        )

                        result = await session.execute(
                            insert_query,
                            {
                                "video_generation_id": video_gen_id,
                                "scene_id": scene_id,
                                "scene_number": i + 1,
                                "scene_description": scene_description,
                                "video_url": video_url,
                                "status": "completed",
                                "target_duration": 5.0,
                            },
                        )
                        await session.commit()
                        video_record_id = result.scalar()
                    except Exception as e:
                        print(f"[SCENE VIDEOS V7] Error inserting video segment: {e}")
                        await session.rollback()
                        video_record_id = None

                    video_results.append(
                        {
                            "id": video_record_id,
                            "scene_id": scene_id,
                            "video_url": video_url,
                            "key_scene_shot_url": key_scene_shot_url,
                            "duration": 5.0,
                            "source_image": starting_image_url,
                            "method": "veo2_image_to_video_sequential",
                            "model": current_model_id,
                            "has_lipsync": has_lipsync,
                            "scene_sequence": i + 1,
                        }
                    )

                    print(
                        f"[SCENE VIDEOS V7] ✅ Generated {scene_id} - Lip sync: {has_lipsync}, Key scene shot: {key_scene_shot_url is not None}"
                    )
                else:
                    raise Exception("No video URL in V7 response")
            else:
                raise Exception(
                    f"V7 Video generation failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"[SCENE VIDEOS V7] ❌ Failed {scene_id}: {str(e)}")

            # Store failed record

            try:
                fail_insert_query = text(
                    """
                    INSERT INTO video_segments (
                        video_generation_id, scene_id, scene_number, scene_description,
                        status
                    ) VALUES (
                        :video_generation_id, :scene_id, :scene_number, :scene_description,
                        :status
                    )
                """
                )

                await session.execute(
                    fail_insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "scene_number": i + 1,
                        "scene_description": scene_description,
                        "status": "failed",
                    },
                )
                await session.commit()
            except Exception as insert_err:
                print(f"[SCENE VIDEOS V7] Error inserting failed record: {insert_err}")
                await session.rollback()

            video_results.append(None)

    successful_videos = len([r for r in video_results if r is not None])
    print(
        f"[SCENE VIDEOS V7] Sequential generation completed: {successful_videos}/{len(scene_descriptions)} videos"
    )
    return video_results


@celery_app.task(bind=True)
def retry_video_retrieval_task(self, video_generation_id: str, video_url: str = None):
    """Celery task to retry video retrieval for a failed video generation"""
    return asyncio.run(async_retry_video_retrieval_task(video_generation_id, video_url))


async def async_retry_video_retrieval_task(
    video_generation_id: str, video_url: str = None
):
    """Async implementation of retry video retrieval task"""
    async with async_session() as session:
        try:
            print(
                f"[VIDEO RETRY TASK] Starting video retrieval retry for: {video_generation_id}"
            )

            # Get video generation data
            # Using raw SQL
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            video_gen = dict(video_gen_record)
            user_id = video_gen.get("user_id")
            current_status = video_gen.get("generation_status")

            # Check if this task is eligible for retry
            if current_status not in ["video_completed", "failed", "retrieval_failed"]:
                raise Exception(
                    f"Cannot retry video retrieval. Current status: {current_status}"
                )

            # Check retry count
            retry_count = video_gen.get("retry_count", 0)
            max_retries = 3

            if retry_count >= max_retries:
                raise Exception(f"Maximum retry attempts ({max_retries}) exceeded")

            # Get video URL from parameter or task data
            if not video_url:
                task_meta = video_gen.get("task_meta", {})
                video_url = task_meta.get("future_links_url") or task_meta.get(
                    "video_url"
                )

                if not video_url:
                    raise Exception("No video URL available for retry")

            print(
                f"[VIDEO RETRY TASK] Attempting video retrieval from URL: {video_url}"
            )

            # Import and use the video service for retry
            from app.core.services.modelslab_v7_video import ModelsLabV7VideoService

            video_service = ModelsLabV7VideoService()

            # Attempt video retrieval
            retry_result = await video_service.retry_video_retrieval(video_url)

            if not retry_result.get("success"):
                # Update retry count and status
                new_retry_count = retry_count + 1

                update_query = text(
                    """
                    UPDATE video_generations
                    SET retry_count = :retry_count,
                        generation_status = :status,
                        error_message = :error_message,
                        can_resume = :can_resume
                    WHERE id = :id
                """
                )

                status = (
                    "retrieval_failed" if new_retry_count < max_retries else "failed"
                )

                await session.execute(
                    update_query,
                    {
                        "retry_count": new_retry_count,
                        "status": status,
                        "error_message": retry_result.get(
                            "error", "Video retrieval failed"
                        ),
                        "can_resume": new_retry_count < max_retries,
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                raise Exception(
                    f"Video retrieval failed: {retry_result.get('error', 'Unknown error')}"
                )

            # Success - update task with video URL and mark as completed
            video_url = retry_result.get("video_url")
            video_duration = retry_result.get("duration", 0)

            task_meta = video_gen.get("task_meta", {})
            task_meta.update(
                {
                    "retry_success": True,
                    "retry_video_url": video_url,
                    "video_duration": video_duration,
                    "final_retrieval_time": "now()",
                }
            )

            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'completed',
                    video_url = :video_url,
                    retry_count = :retry_count,
                    error_message = NULL,
                    can_resume = false,
                    task_meta = :task_meta
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_meta": json.dumps(task_meta),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            print(
                f"[VIDEO RETRY TASK] ✅ Video retrieval retry successful for: {video_generation_id}"
            )

            return {
                "status": "success",
                "message": "Video retrieval successful",
                "video_url": video_url,
                "duration": video_duration,
                "retry_count": retry_count + 1,
                "video_generation_id": video_generation_id,
            }

        except Exception as e:
            error_message = f"Video retrieval retry failed: {str(e)}"
            print(f"[VIDEO RETRY TASK] ❌ {error_message}")

            # Update status to failed
            try:
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'failed', 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {"error_message": error_message, "id": video_generation_id},
                )
                await session.commit()
            except:
                pass

            raise Exception(error_message)


@celery_app.task(bind=True)
def automatic_video_retry_task(self, video_generation_id: str):
    """Automatic retry task with exponential backoff for failed video retrievals"""
    return asyncio.run(async_automatic_video_retry_task(video_generation_id))


async def async_automatic_video_retry_task(video_generation_id: str):
    """Async implementation of automatic retry task"""
    async with async_session() as session:
        try:
            print(
                f"[AUTO RETRY TASK] Starting automatic retry for: {video_generation_id}"
            )

            # Get video generation data
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            video_gen = dict(video_gen_record)
            current_status = video_gen.get("generation_status")

            # Only retry if in a retryable state
            if current_status not in ["video_completed", "failed", "retrieval_failed"]:
                print(
                    f"[AUTO RETRY TASK] Skipping - current status {current_status} not retryable"
                )
                return {
                    "status": "skipped",
                    "message": f"Current status {current_status} not eligible for automatic retry",
                }

            # Check retry count
            retry_count = video_gen.get("retry_count", 0)
            max_automatic_retries = (
                2  # Maximum automatic retries before manual intervention
            )

            if retry_count >= max_automatic_retries:
                print(
                    f"[AUTO RETRY TASK] Maximum automatic retries ({max_automatic_retries}) reached"
                )
                # Update status to indicate manual retry is needed
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'retrieval_failed', 
                        can_resume = true, 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {
                        "error_message": f"Automatic retries exhausted. Please try manual retry.",
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                return {
                    "status": "max_retries_reached",
                    "message": f"Maximum automatic retries ({max_automatic_retries}) reached",
                }

            # Calculate exponential backoff delay
            base_delay = 30  # 30 seconds
            exponential_delay = base_delay * (2**retry_count)  # 30s, 60s, 120s, etc.
            max_delay = 300  # 5 minutes maximum

            actual_delay = min(exponential_delay, max_delay)

            print(
                f"[AUTO RETRY TASK] Retry {retry_count + 1}/{max_automatic_retries}, waiting {actual_delay}s"
            )

            # Wait for exponential backoff
            await asyncio.sleep(actual_delay)

            # Get video URL from task meta
            task_meta_data = video_gen.get("task_meta", {})
            video_url = task_meta_data.get("future_links_url") or task_meta_data.get(
                "video_url"
            )

            if not video_url:
                print(f"[AUTO RETRY TASK] No video URL available for retry")
                return {
                    "status": "no_url",
                    "message": "No video URL available for automatic retry",
                }

            print(
                f"[AUTO RETRY TASK] Attempting automatic video retrieval from URL: {video_url}"
            )

            # Import and use the video service for retry
            from app.core.services.modelslab_v7_video import ModelsLabV7VideoService

            video_service = ModelsLabV7VideoService()

            # Attempt video retrieval
            retry_result = await video_service.retry_video_retrieval(video_url)

            if not retry_result.get("success"):
                # Update retry count and status
                new_retry_count = retry_count + 1

                update_query = text(
                    """
                    UPDATE video_generations
                    SET retry_count = :retry_count,
                        generation_status = :status,
                        error_message = :error_message,
                        can_resume = :can_resume
                    WHERE id = :id
                """
                )

                status = (
                    "retrieval_failed"
                    if new_retry_count < max_automatic_retries
                    else "failed"
                )

                await session.execute(
                    update_query,
                    {
                        "retry_count": new_retry_count,
                        "status": status,
                        "error_message": retry_result.get(
                            "error", "Video retrieval failed"
                        ),
                        "can_resume": new_retry_count < max_automatic_retries,
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                # Schedule next automatic retry if we haven't reached max
                if new_retry_count < max_automatic_retries:
                    print(f"[AUTO RETRY TASK] Scheduling next automatic retry")
                    automatic_video_retry_task.apply_async(
                        args=[video_generation_id],
                        countdown=actual_delay * 2,  # Double the delay for next retry
                    )

                return {
                    "status": "failed",
                    "message": f'Automatic retry failed: {retry_result.get("error", "Unknown error")}',
                    "retry_count": new_retry_count,
                    "next_retry_scheduled": new_retry_count < max_automatic_retries,
                }

            # Success - update task with video URL and mark as completed
            video_url = retry_result.get("video_url")
            video_duration = retry_result.get("duration", 0)

            task_meta = video_gen.get("task_meta", {})
            task_meta.update(
                {
                    "retry_success": True,
                    "retry_video_url": video_url,
                    "video_duration": video_duration,
                    "final_retrieval_time": "now()",
                }
            )

            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'completed',
                    video_url = :video_url,
                    retry_count = :retry_count,
                    error_message = NULL,
                    can_resume = false,
                    task_meta = :task_meta
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_meta": json.dumps(task_meta),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            print(
                f"[AUTO RETRY TASK] ✅ Automatic video retrieval successful for: {video_generation_id}"
            )

            return {
                "status": "success",
                "message": "Automatic video retrieval successful",
                "video_url": video_url,
                "duration": video_duration,
                "retry_count": retry_count + 1,
                "video_generation_id": video_generation_id,
            }

        except Exception as e:
            error_message = f"Automatic retry failed: {str(e)}"
            print(f"[AUTO RETRY TASK] ❌ {error_message}")

            # Update status to failed
            try:
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'failed', 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {"error_message": error_message, "id": video_generation_id},
                )
                await session.commit()
            except:
                pass

            raise Exception(error_message)
