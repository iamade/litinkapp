from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional

from app.api.services.video import VideoService
from app.core.database import async_session, engine
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.videos.models import VideoGeneration, VideoSegment
from app.subscription.models import UserSubscription
from app.core.model_config import get_model_config, ModelConfig
import json

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


# Update the service initialization in generate_all_videos_for_generation
async def generate_scene_videos(
    modelslab_service: ModelsLabV7VideoService,  # ✅ Updated type hint
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str,
    user_id: Optional[str] = None,  # Added for storage organization
    user_tier: str = "BASIC",  # Added for upscaling tier selection
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using V7 Veo 2 image-to-video

    Enhanced with last-frame extraction for visual continuity between scenes.
    After generating each scene's video, the last frame is extracted and can be
    used as the starting point for the next scene.
    """

    print(f"[SCENE VIDEOS V7] Generating scene videos with Veo 2...")
    video_results = []

    scene_images = image_data.get("scene_images", [])  # Fixed key mismatch
    model_id = modelslab_service.get_video_model_for_style(video_style)

    # Track the last frame from the previous scene for visual continuity
    previous_scene_last_frame: Optional[str] = None

    for i, scene_description in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE VIDEOS V7] Processing {scene_id}/{len(scene_descriptions)}")

            # Find scene image - prefer last frame from previous scene for continuity
            scene_image_url = None
            used_previous_frame = False

            # For scenes after the first, try to use the extracted last frame
            if i > 0 and previous_scene_last_frame:
                print(
                    f"[SCENE VIDEOS V7] 🔗 Using previous scene's last frame for visual continuity"
                )
                scene_image_url = previous_scene_last_frame
                used_previous_frame = True
            else:
                # Use the storyboard image
                scene_image = None
                if i < len(scene_images) and scene_images[i] is not None:
                    scene_image = scene_images[i]

                if scene_image and scene_image.get("image_url"):
                    scene_image_url = scene_image["image_url"]

            if not scene_image_url:
                print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                video_results.append(None)
                continue

            # Find audio for lip sync
            scene_audio = find_scene_audio(scene_id, audio_files)

            # ✅ Generate video using V7 Veo 2
            result = await modelslab_service.enhance_video_for_scene(
                scene_description=scene_description,
                image_url=scene_image_url,  # Use extracted frame or storyboard image
                audio_url=scene_audio.get("audio_url") if scene_audio else None,
                style=video_style,
                include_lipsync=bool(scene_audio),
            )

            if result.get("status") == "success":
                enhanced_video = result.get("enhanced_video", {})
                video_url = enhanced_video.get("video_url")
                has_lipsync = enhanced_video.get("has_lipsync", False)

                if video_url:
                    # Store in database
                    video_record_data = {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "segment_index": i + 1,
                        "scene_description": scene_description,
                        "source_image_url": scene_image_url,
                        "video_url": video_url,
                        "duration_seconds": 5.0,  # Veo 2 default
                        "generation_method": "veo2_image_to_video",
                        "status": "completed",
                        "processing_service": "modelslab_v7",
                        "processing_model": model_id,
                        "metadata": json.dumps(
                            {
                                "model_id": model_id,
                                "video_style": video_style,
                                "service": "modelslab_v7",
                                "has_lipsync": has_lipsync,
                                "veo2_enhanced": True,
                            }
                        ),
                    }

                    insert_query = text(
                        """
                        INSERT INTO video_segments (
                            video_generation_id, scene_id, segment_index, scene_description,
                            source_image_url, video_url, duration_seconds, generation_method,
                            status, processing_service, processing_model, metadata
                        ) VALUES (
                            :video_generation_id, :scene_id, :segment_index, :scene_description,
                            :source_image_url, :video_url, :duration_seconds, :generation_method,
                            :status, :processing_service, :processing_model, :metadata
                        ) RETURNING id
                    """
                    )

                    db_result = await session.execute(insert_query, video_record_data)
                    await session.commit()
                    record_id = db_result.scalar()

                    video_results.append(
                        {
                            "id": record_id,
                            "scene_id": scene_id,
                            "video_url": video_url,
                            "duration": 5.0,
                            "source_image": scene_image_url,
                            "method": "veo2_image_to_video",
                            "model": model_id,
                            "has_lipsync": has_lipsync,
                            "used_previous_frame": used_previous_frame,
                        }
                    )

                    print(
                        f"[SCENE VIDEOS V7] ✅ Generated {scene_id} - Lip sync: {has_lipsync}"
                    )

                    # Extract last frame for visual continuity with next scene
                    if i < len(scene_descriptions) - 1:  # Not the last scene
                        print(
                            f"[SCENE VIDEOS V7] Extracting last frame for next scene continuity..."
                        )
                        extracted_frame = await extract_last_frame(video_url, user_id)
                        if extracted_frame:
                            # Optionally upscale the frame before using it
                            previous_scene_last_frame = await upscale_frame(
                                extracted_frame, user_tier, user_id
                            )
                            print(f"[SCENE VIDEOS V7] 🎬 Frame ready for scene {i+2}")
                        else:
                            print(
                                f"[SCENE VIDEOS V7] ⚠️ Could not extract frame, next scene will use storyboard image"
                            )
                            previous_scene_last_frame = None
                else:
                    raise Exception("No video URL in V7 response")
            else:
                raise Exception(
                    f"V7 Video generation failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"[SCENE VIDEOS V7] ❌ Failed {scene_id}: {str(e)}")

            # Store failed record
            # Store failed record
            try:
                fail_insert_query = text(
                    """
                    INSERT INTO video_segments (
                        video_generation_id, scene_id, segment_index, scene_description,
                        generation_method, status, error_message, processing_service, processing_model, metadata
                    ) VALUES (
                        :video_generation_id, :scene_id, :segment_index, :scene_description,
                        :generation_method, :status, :error_message, :processing_service, :processing_model, :metadata
                    )
                """
                )

                await session.execute(
                    fail_insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "segment_index": i + 1,
                        "scene_description": scene_description,
                        "generation_method": "veo2_image_to_video_sequential",
                        "status": "failed",
                        "error_message": str(e),
                        "processing_service": "modelslab_v7",
                        "processing_model": model_id,
                        "metadata": json.dumps(
                            {"service": "modelslab_v7", "veo2_enhanced": False}
                        ),
                    },
                )
                await session.commit()
            except Exception as insert_err:
                print(f"[SCENE VIDEOS V7] Error inserting failed record: {insert_err}")

            video_results.append(None)

    successful_videos = len([r for r in video_results if r is not None])
    print(
        f"[SCENE VIDEOS V7] Completed: {successful_videos}/{len(scene_descriptions)} videos"
    )
    return video_results


def find_scene_audio(
    scene_id: str, audio_files: Dict[str, Any], script_style: str = None
) -> Optional[Dict[str, Any]]:
    """Find the primary audio file for a scene (for lip sync)"""

    # Priority: Character dialogue > Narrator > None
    character_audio = audio_files.get("characters", [])
    narrator_audio = audio_files.get("narrator", [])

    scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1

    # Look for character dialogue first
    for audio in character_audio:
        if audio.get("scene") == scene_number and audio.get("audio_url"):
            return audio

    # For cinematic scripts, don't fall back to narrator audio
    if script_style == "cinematic":
        return None

    # Fall back to narrator audio
    for audio in narrator_audio:
        if audio.get("scene") == scene_number and audio.get("audio_url"):
            return audio

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
                    can_resume = true, 
                    last_retry_at = NULL 
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

            print(f"[VIDEO GENERATION] Processing:")
            print(f"- Scenes: {len(scene_descriptions)}")
            print(f"- Characters: {len(characters)}")
            print(f"- Video Style: {video_style}")
            print(
                f"- Audio Files: {len(audio_files.get('narrator', [])) + len(audio_files.get('characters', []))}"
            )

            # Query existing character images from database
            character_images = await query_existing_character_images(
                user_id, characters
            )
            print(f"- Character Images: {len(character_images)} found in database")

            # Query existing scene images from database
            scene_images = await query_existing_scene_images(
                user_id, scene_descriptions
            )
            print(f"- Scene Images: {len(scene_images)} found in database")

            # For split workflow, prioritize scene images over character images
            if not image_data.get("scene_images"):
                image_data["scene_images"] = []
                for i, scene_description in enumerate(scene_descriptions):
                    scene_image = None

                    # First, try to find a matching scene image for this specific scene
                    for scene_img in scene_images:
                        if (
                            scene_img.get("scene_description")
                            and scene_description.lower()
                            in scene_img["scene_description"].lower()
                        ):
                            scene_image = {
                                "image_url": scene_img.get("image_url"),
                                "scene_description": scene_img.get("scene_description"),
                                "image_type": scene_img.get("image_type", "scene"),
                                "scene_number": i + 1,
                            }
                            print(
                                f"[SCENE IMAGE SELECTION] Using scene image for scene_{i+1}: {scene_img.get('scene_description')}"
                            )
                            break

                    # If no scene image found, fall back to character images
                    if not scene_image and character_images:
                        # Use character images in rotation for scenes
                        char_image = character_images[i % len(character_images)]
                        scene_image = {
                            "image_url": char_image.get("image_url"),
                            "character_name": char_image.get("name"),
                            "image_type": "character_fallback",
                            "scene_number": i + 1,
                        }
                        print(
                            f"[SCENE IMAGE SELECTION] ⚠️ Using character image as fallback for scene_{i+1}: {char_image.get('name')}"
                        )

                # If no images available at all, will use text-to-video fallback
                image_data["scene_images"].append(scene_image)

            # Log the final image selection breakdown
            scene_count = len(
                [img for img in image_data.get("scene_images", []) if img is not None]
            )
            scene_type_count = len(
                [
                    img
                    for img in image_data.get("scene_images", [])
                    if img and img.get("image_type") == "scene"
                ]
            )
            character_fallback_count = len(
                [
                    img
                    for img in image_data.get("scene_images", [])
                    if img and img.get("image_type") == "character_fallback"
                ]
            )

            print(f"[IMAGE SELECTION SUMMARY]")
            print(f"- Total scene images: {scene_count}")
            print(f"- Scene images (proper): {scene_type_count}")
            print(f"- Character fallback images: {character_fallback_count}")
            print(
                f"- No images (text-to-video fallback): {len(scene_descriptions) - scene_count}"
            )

            # Generate videos
            modelslab_service = ModelsLabV7VideoService()

            # Generate scene videos sequentially with key scene shots
            # Generate scene videos sequentially with key scene shots
            video_results = await generate_scene_videos(
                modelslab_service,
                video_generation_id,
                scene_descriptions,
                audio_files,
                image_data,
                video_style,
                video_style,
                script_data,
                user_id,
                model_config=video_config,
                session=session,
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
                    generation_status = 'video_completed',
                    error_message = NULL
                WHERE id = :id
            """
            )
            await session.execute(
                update_query,
                {
                    "video_data": json.dumps(video_data_result),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            # ✅ Update pipeline step to completed
            await update_pipeline_step(
                video_generation_id, "video_generation", "completed", session=session
            )

            success_message = f"Video generation completed! {successful_videos} videos created for {total_scenes} scenes"
            print(f"[VIDEO GENERATION SUCCESS] {success_message}")

            # Log detailed breakdown
            print(f"[VIDEO STATISTICS]")
            print(
                f"- Scene-by-scene generation status: {successful_videos}/{total_scenes}"
            )
            print(f"- Total video duration: {total_duration:.1f} seconds")
            print(f"- Success rate: {success_rate:.1f}%")

            # ✅ Trigger audio/video merge after video completion
            print(f"[PIPELINE] Starting audio/video merge after video completion")
            from app.tasks.merge_tasks import merge_audio_video_for_generation

            merge_audio_video_for_generation.delay(video_generation_id)

            return {
                "status": "success",
                "message": success_message + " - Starting audio/video merge...",
                "statistics": video_data_result["statistics"],
                "video_results": video_results,
                "next_step": "audio_video_merge",
            }

        except Exception as e:
            error_message = f"Video generation failed: {str(e)}"
            print(f"[VIDEO GENERATION ERROR] {error_message}")

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
            scene_id = f"scene_{i+1}"
            print(
                f"[SCENE VIDEOS V7] Processing {scene_id}/{len(scene_descriptions)} (Sequential)"
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

            # Find audio for lip sync / audio-reactive
            scene_audio = find_scene_audio(scene_id, audio_files)
            init_audio_url = scene_audio.get("audio_url") if scene_audio else None

            # Decide on Model: Dialogue (Audio) vs Narration (Visual Only)
            # If we have init_audio, we MIGHT want to use a specific lip-sync capable model if the primary isn't one
            # But per plan, tiers like Standard+ use Omni/Wan which support it.
            # Free/Basic might use seedance (no lip sync) or wan2.5 (lip sync).

            # Use the tier's primary model
            current_model_id = primary_model_id

            logger_msg = f"[SCENE VIDEOS V7] Generating video for {scene_id} using {current_model_id}"
            if init_audio_url:
                logger_msg += " with Audio Reactive/Lip Sync"
            print(logger_msg)

            # ✅ Generate video using ModelsLab Service
            result = await modelslab_service.generate_image_to_video(
                image_url=starting_image_url,
                prompt=scene_description,  # Could use enhanced prompt here if needed
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
                        from app.api.services.video import VideoService

                        video_service = VideoService(session)
                        frame_filename = f"key_scene_shot_{video_gen_id}_{scene_id}.jpg"
                        key_scene_shot_url = (
                            await video_service.extract_last_frame_from_video(
                                video_url, frame_filename, user_id
                            )
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
                                video_generation_id, scene_id, segment_index, scene_description,
                                source_image_url, video_url, key_scene_shot_url, duration_seconds,
                                generation_method, status, processing_service, processing_model, metadata
                            ) VALUES (
                                :video_generation_id, :scene_id, :segment_index, :scene_description,
                                :source_image_url, :video_url, :key_scene_shot_url, :duration_seconds,
                                :generation_method, :status, :processing_service, :processing_model, :metadata
                            ) RETURNING id
                        """
                        )

                        result = await session.execute(
                            insert_query,
                            {
                                "video_generation_id": video_gen_id,
                                "scene_id": scene_id,
                                "segment_index": i + 1,
                                "scene_description": scene_description,
                                "source_image_url": starting_image_url,
                                "video_url": video_url,
                                "key_scene_shot_url": key_scene_shot_url,
                                "duration_seconds": 5.0,
                                "generation_method": "veo2_image_to_video_sequential",
                                "status": "completed",
                                "processing_service": "modelslab_v7",
                                "processing_model": current_model_id,
                                "metadata": json.dumps(
                                    {
                                        "model_id": current_model_id,
                                        "video_style": video_style,
                                        "service": "modelslab_v7",
                                        "has_lipsync": has_lipsync,
                                        "veo2_enhanced": True,
                                        "character_dialogue_integrated": has_lipsync,
                                        "sequential_processing": True,
                                        "scene_sequence": i + 1,
                                        "used_previous_key_scene": i > 0,
                                        "key_scene_extraction_success": key_scene_shot_url
                                        is not None,
                                    }
                                ),
                            },
                        )
                        await session.commit()
                        video_record_id = result.scalar()
                    except Exception as e:
                        print(f"[SCENE VIDEOS V7] Error inserting video segment: {e}")
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
                        video_generation_id, scene_id, segment_index, scene_description,
                        generation_method, status, error_message, processing_service, processing_model, metadata
                    ) VALUES (
                        :video_generation_id, :scene_id, :segment_index, :scene_description,
                        :generation_method, :status, :error_message, :processing_service, :processing_model, :metadata
                    )
                """
                )

                await session.execute(
                    fail_insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "segment_index": i + 1,
                        "scene_description": scene_description,
                        "generation_method": "veo2_image_to_video_sequential",
                        "status": "failed",
                        "error_message": str(e),
                        "processing_service": "modelslab_v7",
                        "processing_model": model_id,
                        "metadata": json.dumps(
                            {
                                "service": "modelslab_v7",
                                "veo2_enhanced": False,
                                "sequential_processing": True,
                            }
                        ),
                    },
                )
                await session.commit()
            except Exception as insert_err:
                print(f"[SCENE VIDEOS V7] Error inserting failed record: {insert_err}")

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
                task_metadata = video_gen.get("task_metadata", {})
                video_url = task_metadata.get("future_links_url") or task_metadata.get(
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
                        last_retry_at = NOW(), 
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

            task_metadata = video_gen.get("task_metadata", {})
            task_metadata.update(
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
                    last_retry_at = NOW(), 
                    error_message = NULL, 
                    can_resume = false, 
                    task_metadata = :task_metadata 
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_metadata": json.dumps(task_metadata),
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

            # Get video URL from task metadata
            task_metadata = video_gen.get("task_metadata", {})
            video_url = task_metadata.get("future_links_url") or task_metadata.get(
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
                        last_retry_at = NOW(), 
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

            task_metadata = video_gen.get("task_metadata", {})
            task_metadata.update(
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
                    last_retry_at = NOW(), 
                    error_message = NULL, 
                    can_resume = false, 
                    task_metadata = :task_metadata 
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_metadata": json.dumps(task_metadata),
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
