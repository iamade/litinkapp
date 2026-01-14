from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional
from app.core.database import async_session, engine
import json
import logging

# from app.core.services.modelslab_image import ModelsLabImageService
from app.core.services.pipeline import PipelineManager, PipelineStep
from app.core.services.modelslab_v7_image import ModelsLabV7ImageService
from app.core.services.standalone_image import StandaloneImageService
from app.api.services.subscription import SubscriptionManager
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def generate_all_images_for_video(self, video_generation_id: str):
    """Main task to generate all images for a video generation with pipeline support"""
    return asyncio.run(async_generate_all_images_for_video(video_generation_id))


async def async_generate_all_images_for_video(video_generation_id: str):
    """Async implementation of image generation task"""
    async with async_session() as session:
        pipeline_manager = PipelineManager()

        try:
            print(
                f"[IMAGE GENERATION] Starting image generation for video: {video_generation_id}"
            )

            # Mark image step as started
            pipeline_manager.mark_step_started(
                video_generation_id, PipelineStep.IMAGE_GENERATION, session
            )

            # Get video generation data
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            video_gen = dict(video_gen_record)
            user_id = video_gen.get("user_id")

            if not user_id:
                raise Exception(
                    f"Video generation {video_generation_id} has no user_id"
                )

            # Get user tier for model selection
            subscription_manager = SubscriptionManager(session)
            usage_check = await subscription_manager.check_usage_limits(
                user_id, "image"
            )
            user_tier = usage_check["tier"]

            print(
                f"[IMAGE GENERATION] User {user_id} has {user_tier} tier - will use tier-based model selection"
            )

            # ✅ FIXED: Proper validation of existing images
            existing_image_data = video_gen.get("image_data") or {}
            existing_character_images = (
                existing_image_data.get("character_images") or []
            )
            existing_scene_images = existing_image_data.get("scene_images") or []

            # Count ACTUAL successful images with URLs
            successful_character_count = len(
                [
                    img
                    for img in existing_character_images
                    if img and img.get("image_url")
                ]
            )
            successful_scene_count = len(
                [img for img in existing_scene_images if img and img.get("image_url")]
            )

            # Get script data to know how many images we need
            script_data = video_gen.get("script_data") or {}
            scene_descriptions = script_data.get("scene_descriptions") or []
            characters = script_data.get("characters") or []
            video_style = script_data.get("video_style", "realistic")

            needed_character_images = len(characters)
            needed_scene_images = len(scene_descriptions)

            # ✅ FIXED: Only skip if we have ALL needed successful images
            if (
                successful_character_count >= needed_character_images
                and successful_scene_count >= needed_scene_images
                and needed_character_images > 0
                and needed_scene_images > 0
            ):

                print(f"[IMAGE GENERATION] ✅ All images already exist and are valid:")
                print(
                    f"  - Character images: {successful_character_count}/{needed_character_images}"
                )
                print(
                    f"  - Scene images: {successful_scene_count}/{needed_scene_images}"
                )
                print(
                    f"[IMAGE GENERATION] Skipping generation and proceeding to next step"
                )

                # Mark as completed and move to next step
                pipeline_manager.mark_step_completed(
                    video_generation_id,
                    PipelineStep.IMAGE_GENERATION,
                    {
                        "message": "All images already existed",
                        "image_data": existing_image_data,
                    },
                )

                # Update status and trigger next step
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'images_completed' 
                    WHERE id = :id
                """
                )
                await session.execute(update_query, {"id": video_generation_id})
                await session.commit()

                # Trigger next step
                print(f"[PIPELINE] Starting video generation after image skip")
                from app.tasks.video_tasks import generate_all_videos_for_generation

                generate_all_videos_for_generation.delay(video_generation_id)

                return {
                    "status": "success",
                    "message": "All images already existed - skipped to video generation",
                    "existing_images": True,
                    "character_images_count": successful_character_count,
                    "scene_images_count": successful_scene_count,
                    "next_step": "video_generation",
                }

            # ✅ NEW: Clear partial/failed image data before regenerating
            if existing_character_images or existing_scene_images:
                print(f"[IMAGE GENERATION] ⚠️ Found incomplete image data:")
                print(
                    f"  - Character images: {successful_character_count}/{needed_character_images} valid"
                )
                print(
                    f"  - Scene images: {successful_scene_count}/{needed_scene_images} valid"
                )
                print(
                    f"[IMAGE GENERATION] Clearing partial data and regenerating all images"
                )

                # Clear the partial data
                clear_query = text(
                    """
                    UPDATE video_generations 
                    SET image_data = NULL 
                    WHERE id = :id
                """
                )
                await session.execute(clear_query, {"id": video_generation_id})
                await session.commit()

            # Check if audio generation is completed (unless we're in retry mode)
            current_status = video_gen.get("generation_status")
            if (
                current_status not in ["generating_images", "retrying"]
                and current_status != "audio_completed"
            ):
                raise Exception(
                    f"Audio generation must be completed before image generation. Current status: {current_status}"
                )

            # Update status
            status_query = text(
                """
                UPDATE video_generations 
                SET generation_status = 'generating_images' 
                WHERE id = :id
            """
            )
            await session.execute(status_query, {"id": video_generation_id})
            await session.commit()

            print(f"[IMAGE GENERATION] Processing:")
            print(f"- Characters: {len(characters)}")
            print(f"- Scenes: {len(scene_descriptions)}")
            print(f"- Video Style: {video_style}")

            if not scene_descriptions and not characters:
                raise Exception(
                    "No scene descriptions or characters found in script data"
                )

            # ✅ FIXED: Generate images using asyncio.run() instead of await
            image_service = ModelsLabV7ImageService()

            # 1. Generate character reference images
            character_images = []
            if characters:
                print(
                    f"[IMAGE GENERATION] Generating {len(characters)} character images..."
                )
                character_images = await generate_character_images_optimized(
                    image_service,
                    video_generation_id,
                    characters,
                    video_style,
                    user_tier,
                    session,
                )

            # 2. Generate scene images
            scene_images = []
            if scene_descriptions:
                print(
                    f"[IMAGE GENERATION] Generating {len(scene_descriptions)} scene images..."
                )
                scene_images = await generate_scene_images_optimized(
                    image_service,
                    video_generation_id,
                    scene_descriptions,
                    video_style,
                    user_tier,
                    session,
                )

            # Compile results
            successful_character_images = len(
                [img for img in character_images if img is not None]
            )
            successful_scene_images = len(
                [img for img in scene_images if img is not None]
            )
            total_images = successful_character_images + successful_scene_images
            total_needed = len(characters) + len(scene_descriptions)

            success_rate = (
                (total_images / total_needed * 100) if total_needed > 0 else 0
            )

            # ✅ CRITICAL: Ensure we have some successful images before proceeding
            if total_images == 0:
                raise Exception(
                    f"No images were successfully generated! Character: {successful_character_images}, Scene: {successful_scene_images}"
                )

            # Update video generation with image data
            image_data = {
                "character_images": character_images,
                "scene_images": scene_images,
                "statistics": {
                    "total_scenes": len(scene_descriptions),
                    "total_characters": len(characters),
                    "images_needed_per_scene": 1,
                    "character_images_generated": successful_character_images,
                    "scene_images_generated": successful_scene_images,
                    "total_images_generated": total_images,
                    "success_rate": round(success_rate, 1),
                },
            }

            print(f"[IMAGE DEBUG] Final image_data structure:")
            print(
                f"  - Character images: {len(character_images)} items ({successful_character_images} successful)"
            )
            print(
                f"  - Scene images: {len(scene_images)} items ({successful_scene_images} successful)"
            )

            # Debug scene images specifically
            for i, img in enumerate(scene_images):
                if img:
                    print(
                        f"  - Scene {i+1}: scene_id={img.get('scene_id')}, has_url={bool(img.get('image_url'))}, url={img.get('image_url', 'NO_URL')[:50]}..."
                    )
                else:
                    print(f"  - Scene {i+1}: NULL/FAILED")

            final_update_query = text(
                """
                UPDATE video_generations 
                SET image_data = :image_data, 
                    generation_status = 'images_completed' 
                WHERE id = :id
            """
            )
            await session.execute(
                final_update_query,
                {"image_data": json.dumps(image_data), "id": video_generation_id},
            )
            await session.commit()

            # Mark step as completed
            pipeline_manager.mark_step_completed(
                video_generation_id,
                PipelineStep.IMAGE_GENERATION,
                {"total_images": total_images, "image_data": image_data},
            )

            success_message = f"Image generation completed! {total_images} images created ({successful_character_images} characters, {successful_scene_images} scenes)"
            print(f"[IMAGE GENERATION SUCCESS] {success_message}")

            # Log statistics
            print(f"[IMAGE STATISTICS]")
            print(f"- Total characters: {len(characters)}")
            print(f"- Total scenes in script: {len(scene_descriptions)}")
            print(
                f"- Character images generated: {successful_character_images}/{len(characters)}"
            )
            print(
                f"- Scene images generated: {successful_scene_images}/{len(scene_descriptions)}"
            )
            print(f"- Success rate: {success_rate:.1f}%")

            # For split workflow, video generation starts independently
            # Image generation completion doesn't trigger video generation anymore

            return {
                "status": "success",
                "message": success_message,
                "statistics": image_data["statistics"],
                "character_images": character_images,
                "scene_images": scene_images,
            }

        except Exception as e:
            error_message = f"Image generation failed: {str(e)}"
            print(f"[IMAGE GENERATION ERROR] {error_message}")

            # Mark step as failed
            try:
                pipeline_manager.mark_step_failed(
                    video_generation_id,
                    PipelineStep.IMAGE_GENERATION,
                    error_message,
                    session,
                )
            except Exception as pm_error:
                print(f"[PIPELINE] Warning - Failed to mark step failed: {pm_error}")

            # Update status to failed
            try:
                error_update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'failed', 
                        error_message = :error_message, 
                        can_resume = true, 
                        failed_at_step = 'image_generation' 
                    WHERE id = :id
                """
                )
                await session.execute(
                    error_update_query,
                    {"error_message": error_message, "id": video_generation_id},
                )
                await session.commit()
            except Exception as db_error:
                print(f"[IMAGE GENERATION] Database update error: {str(db_error)}")

            raise Exception(error_message)


# ✅ NEW: Optimized async function for character images
async def generate_character_images_optimized(
    image_service: ModelsLabV7ImageService,
    video_gen_id: str,
    characters: List[str],
    style: str = "realistic",
    user_tier: str = "free",
    session: AsyncSession = None,
) -> List[Dict[str, Any]]:
    """Generate character images with optimizations"""

    print(
        f"[CHARACTER IMAGES OPTIMIZED] Generating images for {len(characters)} characters..."
    )
    character_results = []

    for i, character in enumerate(characters):
        try:
            print(f"[CHARACTER IMAGE {i+1}] Processing: {character}")

            character_description = (
                f"Detailed character portrait, {style} style, expressive features"
            )

            result = await image_service.generate_character_image(
                character_name=character,
                character_description=character_description,
                style=style,
                aspect_ratio="3:4",
                user_tier=user_tier,
            )

            if result.get("status") == "success":
                image_url = result.get("image_url")

                if not image_url:
                    raise Exception("No image URL in V7 response")

                # Store in database
                image_record_data = {
                    "video_generation_id": video_gen_id,
                    "image_type": "character",
                    "prompt": f"Character: {character}, {character_description}",
                    "image_url": image_url,
                    "character_name": character,
                    "style": style,
                    "status": "completed",
                    "sequence_order": i + 1,
                    "model_id": result.get("model_used", "gen4_image"),
                    "aspect_ratio": "3:4",
                    "service_provider": "modelslab_v7",
                    "generation_time_seconds": result.get("generation_time", 0),
                    "metadata": json.dumps(
                        {
                            "service": "modelslab_v7",
                            "model_used": result.get("model_used", "gen4_image"),
                            "generation_time": result.get("generation_time", 0),
                        }
                    ),
                }

                insert_query = text(
                    """
                    INSERT INTO image_generations (
                        video_generation_id, image_type, prompt, image_url, character_name, style, status,
                        sequence_order, model_id, aspect_ratio, service_provider, generation_time_seconds, metadata
                    ) VALUES (
                        :video_generation_id, :image_type, :prompt, :image_url, :character_name, :style, :status,
                        :sequence_order, :model_id, :aspect_ratio, :service_provider, :generation_time_seconds, :metadata
                    ) RETURNING id
                """
                )

                db_result = await session.execute(insert_query, image_record_data)
                await session.commit()
                record_id = db_result.scalar()

                character_results.append(
                    {
                        "id": record_id,
                        "character": character,
                        "image_url": image_url,
                        "style": style,
                        "status": "success",
                    }
                )

                print(f"[CHARACTER IMAGE {i+1}] ✅ Success: {character}")

            else:
                raise Exception(
                    f"V7 Image generation failed: {result.get('error', 'Unknown error')}"
                )

            # Brief pause between requests
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[CHARACTER IMAGE {i+1}] ❌ Failed {character}: {str(e)}")

            # Store failed record
            failed_record_data = {
                "video_generation_id": video_gen_id,
                "image_type": "character",
                "character_name": character,
                "style": style,
                "status": "failed",
                "error_message": str(e),
                "sequence_order": i + 1,
                "prompt": f"Character: {character}, {character_description}",
                "model_id": "gen4_image",
                "aspect_ratio": "3:4",
                "service_provider": "modelslab_v7",
                "metadata": json.dumps({"service": "modelslab_v7", "error": str(e)}),
            }

            fail_insert_query = text(
                """
                INSERT INTO image_generations (
                    video_generation_id, image_type, character_name, style, status, error_message,
                    sequence_order, prompt, model_id, aspect_ratio, service_provider, metadata
                ) VALUES (
                    :video_generation_id, :image_type, :character_name, :style, :status, :error_message,
                    :sequence_order, :prompt, :model_id, :aspect_ratio, :service_provider, :metadata
                )
            """
            )
            await session.execute(fail_insert_query, failed_record_data)
            await session.commit()

            character_results.append(
                {"character": character, "status": "failed", "error": str(e)}
            )

    successful_count = len(
        [r for r in character_results if r.get("status") == "success"]
    )
    print(
        f"[CHARACTER IMAGES OPTIMIZED] Completed: {successful_count}/{len(characters)} characters"
    )
    return character_results


async def generate_scene_images_optimized(
    image_service: ModelsLabV7ImageService,
    video_gen_id: str,
    scene_descriptions: List[Dict[str, Any]],
    style: str = "cinematic",
    user_tier: str = "free",
    session: AsyncSession = None,
) -> List[Dict[str, Any]]:
    """Generate scene images sequentially with optimizations"""

    print(
        f"[SCENE IMAGES OPTIMIZED] Generating images for {len(scene_descriptions)} scenes..."
    )
    scene_results = []

    for i, scene in enumerate(scene_descriptions):
        try:
            # Handle different scene description formats
            if isinstance(scene, dict):
                scene_text = scene.get("description", scene.get("text", str(scene)))
                scene_number = scene.get("scene_number", i + 1)
            else:
                scene_text = str(scene)
                scene_number = i + 1

            print(f"[SCENE IMAGE {i+1}] Processing: {scene_text[:50]}...")

            # ✅ OPTIMIZATION: Try with shorter timeout first
            result = await image_service.generate_scene_image(
                scene_description=scene_text,
                style=style,
                aspect_ratio="16:9",
                user_tier=user_tier,
            )

            if result.get("status") == "success":
                image_url = result.get("image_url")

                if not image_url:
                    raise Exception("No image URL in V7 response")

                # Store in database
                image_record_data = {
                    "video_generation_id": video_gen_id,
                    "image_type": "scene",
                    "prompt": f"Scene: {scene_text}",
                    "image_url": image_url,
                    "scene_number": scene_number,
                    "style": style,
                    "status": "completed",
                    "sequence_order": i + 1,
                    "model_id": result.get("model_used", "gen4_image"),
                    "aspect_ratio": "16:9",
                    "service_provider": "modelslab_v7",
                    "generation_time_seconds": result.get("generation_time", 0),
                    "metadata": json.dumps(
                        {
                            "service": "modelslab_v7",
                            "model_used": result.get("model_used", "gen4_image"),
                            "generation_time": result.get("generation_time", 0),
                        }
                    ),
                }

                insert_query = text(
                    """
                    INSERT INTO image_generations (
                        video_generation_id, image_type, prompt, image_url, scene_number, style, status,
                        sequence_order, model_id, aspect_ratio, service_provider, generation_time_seconds, metadata
                    ) VALUES (
                        :video_generation_id, :image_type, :prompt, :image_url, :scene_number, :style, :status,
                        :sequence_order, :model_id, :aspect_ratio, :service_provider, :generation_time_seconds, :metadata
                    ) RETURNING id
                """
                )

                db_result = await session.execute(insert_query, image_record_data)
                await session.commit()
                record_id = db_result.scalar()

                scene_results.append(
                    {
                        "id": record_id,
                        "scene_number": scene_number,
                        "image_url": image_url,
                        "description": scene_text,
                        "style": style,
                        "status": "success",
                    }
                )

                print(f"[SCENE IMAGE {i+1}] ✅ Success: {image_url[:50]}...")

            else:
                raise Exception(
                    f"V7 Image generation failed: {result.get('error', 'Unknown error')}"
                )

            # ✅ OPTIMIZATION: Brief pause between requests
            await asyncio.sleep(2)

        except Exception as e:
            print(f"[SCENE IMAGE {i+1}] ❌ Failed: {str(e)}")

            # Store failed record
            failed_record_data = {
                "video_generation_id": video_gen_id,
                "image_type": "scene",
                "scene_number": scene_number if "scene_number" in locals() else i + 1,
                "prompt": scene_text if "scene_text" in locals() else "Unknown scene",
                "style": style,
                "status": "failed",
                "error_message": str(e),
                "sequence_order": i + 1,
                "model_id": "gen4_image",
                "aspect_ratio": "16:9",
                "service_provider": "modelslab_v7",
                "metadata": json.dumps({"service": "modelslab_v7", "error": str(e)}),
            }

            fail_insert_query = text(
                """
                INSERT INTO image_generations (
                    video_generation_id, image_type, scene_number, prompt, style, status, error_message,
                    sequence_order, model_id, aspect_ratio, service_provider, metadata
                ) VALUES (
                    :video_generation_id, :image_type, :scene_number, :prompt, :style, :status, :error_message,
                    :sequence_order, :model_id, :aspect_ratio, :service_provider, :metadata
                )
            """
            )
            await session.execute(fail_insert_query, failed_record_data)
            await session.commit()

            scene_results.append(
                {
                    "scene_number": (
                        scene_number if "scene_number" in locals() else i + 1
                    ),
                    "status": "failed",
                    "error": str(e),
                }
            )

    successful_count = len([r for r in scene_results if r.get("status") == "success"])
    print(
        f"[SCENE IMAGES OPTIMIZED] Completed: {successful_count}/{len(scene_descriptions)} scenes"
    )
    return scene_results


def create_character_image_prompt(character: str, style: str) -> str:
    """Create detailed prompt for character image generation"""

    style_modifiers = {
        "realistic": "photorealistic, high-resolution portrait, professional lighting, detailed features",
        "cinematic": "cinematic lighting, dramatic composition, film-like quality, professional cinematography",
        "animated": "animated character design, stylized features, vibrant colors, cartoon style",
        "fantasy": "fantasy art style, magical atmosphere, mystical lighting, detailed fantasy character",
        "comic": "comic book style, bold lines, vibrant colors, superhero aesthetic",
        "artistic": "artistic rendering, painterly style, creative composition, artistic flair",
    }

    base_prompt = f"Character portrait of {character}, "
    style_prompt = style_modifiers.get(style.lower(), style_modifiers["realistic"])
    technical_prompt = ", 16:9 aspect ratio, high quality, detailed, professional"

    return base_prompt + style_prompt + technical_prompt


@celery_app.task(bind=True)
def generate_character_image_task(
    self,
    character_name: str,
    character_description: str,
    user_id: str,
    chapter_id: Optional[str] = None,
    character_id: Optional[str] = None,
    style: str = "realistic",
    aspect_ratio: str = "3:4",
    custom_prompt: Optional[str] = None,
    record_id: Optional[str] = None,
    user_tier: str = "free",
):
    """
    Unified asynchronous Celery task for generating character images.
    Supports both standalone character images (chapter-based) and character record images (plot-based).

    Args:
        character_name: Name of the character
        character_description: Description of the character
        user_id: User ID for database association
        chapter_id: Optional chapter ID for metadata association
        character_id: Optional character record ID - if provided, updates characters table
        style: Visual style (realistic, cinematic, animated, fantasy)
        aspect_ratio: Image aspect ratio
        custom_prompt: Optional custom prompt additions
        record_id: Image generation record ID for tracking
        user_tier: User subscription tier for model selection

    Returns:
        Dict containing task result with record_id and status
    """
    return asyncio.run(
        async_generate_character_image_task(
            self.request.id,
            character_name,
            character_description,
            user_id,
            chapter_id,
            character_id,
            style,
            aspect_ratio,
            custom_prompt,
            record_id,
            user_tier,
        )
    )


async def async_generate_character_image_task(
    task_id: str,
    character_name: str,
    character_description: str,
    user_id: str,
    chapter_id: Optional[str] = None,
    character_id: Optional[str] = None,
    style: str = "realistic",
    aspect_ratio: str = "3:4",
    custom_prompt: Optional[str] = None,
    record_id: Optional[str] = None,
    user_tier: str = "free",
):
    """Async implementation of character image generation task"""
    async with async_session() as session:
        try:
            logger.info(
                f"[CharacterImageTask] Starting generation for {character_name}"
            )
            logger.info(
                f"[CharacterImageTask] Parameters: user={user_id}, chapter={chapter_id}, character={character_id}, record={record_id}, tier={user_tier}"
            )

            # Update character status to 'generating' if character_id provided
            if character_id:
                try:
                    update_query = text(
                        """
                        UPDATE characters
                        SET image_generation_status = 'generating',
                            image_generation_task_id = :task_id,
                            updated_at = NOW()
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        update_query, {"task_id": task_id, "id": character_id}
                    )
                    await session.commit()
                    logger.info(
                        f"[CharacterImageTask] Updated character {character_id} status to 'generating'"
                    )
                except Exception as char_update_error:
                    logger.warning(
                        f"[CharacterImageTask] Failed to update character status: {char_update_error}"
                    )

            # Create standalone image service instance
            image_service = StandaloneImageService(session)

            # Generate the character image using the existing service
            result = await image_service.generate_character_image(
                character_name=character_name,
                character_description=character_description,
                user_id=user_id,
                style=style,
                aspect_ratio=aspect_ratio,
                custom_prompt=custom_prompt,
                user_tier=user_tier,
            )

            # Check for error in result (fallback manager returns dict on error)
            if result.get("status") == "error":
                raise Exception(result.get("error", "Unknown error from image service"))

            image_url = result.get("image_url")
            generation_time = result.get("generation_time", 0)
            model_used = result.get("model_used", "gen4_image")

            # Update the image_generations record with the result
            update_query = text(
                """
                UPDATE image_generations 
                SET status = 'completed', 
                    image_url = :image_url, 
                    generation_time_seconds = :generation_time, 
                    updated_at = NOW(), 
                    character_id = :character_id, 
                    model_id = :model_id 
                WHERE id = :id
            """
            )
            await session.execute(
                update_query,
                {
                    "image_url": image_url,
                    "generation_time": generation_time,
                    "character_id": character_id,
                    "model_id": model_used,
                    "id": record_id,
                },
            )
            await session.commit()
            logger.info(
                f"[CharacterImageTask] Updated image_generations record {record_id}"
            )

            # If character_id provided, also update the characters table
            if character_id and image_url:
                try:
                    image_metadata = {
                        "model_used": model_used,
                        "generation_time": generation_time,
                        "aspect_ratio": aspect_ratio,
                        "style": style,
                        "service": "modelslab_v7",
                        "task_id": task_id,
                        "image_generation_record_id": record_id,
                    }

                    char_update_query = text(
                        """
                        UPDATE characters 
                        SET image_url = :image_url, 
                            image_generation_status = 'completed', 
                            image_generation_prompt = :prompt, 
                            image_metadata = :metadata, 
                            generation_method = 'async_celery', 
                            model_used = :model_used, 
                            updated_at = NOW() 
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        char_update_query,
                        {
                            "image_url": image_url,
                            "prompt": result.get(
                                "prompt_used",
                                custom_prompt
                                or f"Character portrait: {character_name}",
                            ),
                            "metadata": json.dumps(image_metadata),
                            "model_used": model_used,
                            "id": character_id,
                        },
                    )
                    await session.commit()
                    logger.info(
                        f"[CharacterImageTask] Updated character {character_id} with image URL: {image_url}"
                    )

                except Exception as char_update_error:
                    logger.error(
                        f"[CharacterImageTask] Failed to update character record: {char_update_error}"
                    )

            logger.info(
                f"[CharacterImageTask] Successfully generated character image: {record_id}"
            )

            return {
                "status": "success",
                "record_id": record_id,
                "character_id": character_id,
                "character_name": character_name,
                "image_url": image_url,
                "message": "Character image generated successfully",
                "generation_time": generation_time,
                "model_used": model_used,
            }

        except Exception as e:
            error_details = str(e) if str(e) else repr(e)
            error_message = f"Character image generation failed: {error_details}"
            logger.error(f"[CharacterImageTask] {error_message}")

            # Update image_generations record with error
            try:
                if record_id:
                    error_update_query = text(
                        """
                        UPDATE image_generations 
                        SET status = 'failed', 
                            error_message = :error_message, 
                            updated_at = NOW() 
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        error_update_query,
                        {"error_message": error_message, "id": record_id},
                    )
                    await session.commit()
            except Exception as db_error:
                logger.error(
                    f"[CharacterImageTask] Failed to update image_generations with error: {db_error}"
                )

            # Update character record with failed status if character_id provided
            try:
                if character_id:
                    char_error_query = text(
                        """
                        UPDATE characters 
                        SET image_generation_status = 'failed', 
                            updated_at = NOW() 
                        WHERE id = :id
                    """
                    )
                    await session.execute(char_error_query, {"id": character_id})
                    await session.commit()
            except Exception as char_error:
                logger.error(
                    f"[CharacterImageTask] Failed to update character with error status: {char_error}"
                )

            raise Exception(error_message)


def create_scene_image_prompt(scene_description: str, style: str) -> str:
    """Create detailed prompt for scene image generation"""

    style_modifiers = {
        "realistic": "photorealistic scene, natural lighting, high detail, realistic environment",
        "cinematic": "cinematic composition, dramatic lighting, film-like atmosphere, professional cinematography",
        "animated": "animated scene, stylized environment, vibrant colors, cartoon background",
        "fantasy": "fantasy landscape, magical atmosphere, mystical environment, fantasy art style",
        "comic": "comic book scene, bold composition, dynamic angles, comic art style",
        "artistic": "artistic scene, painterly environment, creative composition, artistic style",
    }

    base_prompt = f"Scene: {scene_description}, "
    style_prompt = style_modifiers.get(style.lower(), style_modifiers["realistic"])
    technical_prompt = (
        ", 16:9 aspect ratio, high quality, detailed background, cinematic framing"
    )

    return base_prompt + style_prompt + technical_prompt


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
    retry_count: int = 0,
    character_ids: Optional[List[str]] = None,
    character_image_urls: Optional[List[str]] = None,
) -> None:
    """
    Asynchronous Celery task for generating scene images with retry mechanism.

    Args:
        record_id: Image generation record ID for tracking
        scene_description: Description of the scene to generate
        scene_number: Scene number in the sequence
        user_id: User ID for database association
        chapter_id: Optional chapter ID for metadata
        script_id: Optional script ID for metadata
        style: Visual style (cinematic, realistic, animated, fantasy)
        aspect_ratio: Image aspect ratio (default: 16:9)
        custom_prompt: Optional custom prompt additions
        user_tier: User subscription tier for model selection
        retry_count: Current retry count for exponential backoff
        character_ids: Optional list of character image IDs to use as style references
        character_image_urls: Optional list of direct character image URLs
    """
    return asyncio.run(
        async_generate_scene_image_task(
            record_id,
            scene_description,
            scene_number,
            user_id,
            chapter_id,
            script_id,
            style,
            aspect_ratio,
            custom_prompt,
            user_tier,
            retry_count=retry_count,
            character_ids=character_ids,
            character_image_urls=character_image_urls,
            task_instance=self,
        )
    )


async def async_generate_scene_image_task(
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
    retry_count: int = 0,
    character_ids: Optional[List[str]] = None,
    character_image_urls: Optional[List[str]] = None,
    task_instance: Any = None,
):
    """Async implementation of scene image generation task"""
    import random
    from datetime import datetime

    async with async_session() as session:
        try:
            logger.info(
                f"[SceneImageTask] Starting generation for scene {scene_number}"
            )
            logger.info(
                f"[SceneImageTask] Parameters: user={user_id}, chapter={chapter_id}, characters={len(character_ids) if character_ids else 0}, direct_urls={len(character_image_urls) if character_image_urls else 0}"
            )

            # Verify record exists
            try:
                check_query = text("SELECT id FROM image_generations WHERE id = :id")
                result = await session.execute(check_query, {"id": record_id})
                record_check = result.scalar()
                if not record_check:
                    logger.error(f"[SceneImageTask] Record {record_id} not found")
                    return
            except Exception as e:
                logger.error(f"[SceneImageTask] Failed to verify record: {e}")
                return

            # Update status to in_progress with transaction safety
            try:
                # Fetch existing meta to update safely
                meta_query = text("SELECT meta FROM image_generations WHERE id = :id")
                meta_result = await session.execute(meta_query, {"id": record_id})
                meta_row = meta_result.mappings().first()
                current_meta = meta_row.get("meta") if meta_row else {}
                if current_meta is None:
                    current_meta = {}

                # Update meta in Python
                current_meta["last_attempted_at"] = datetime.utcnow().isoformat()
                current_meta["retry_count"] = retry_count

                # Update with full JSON object
                status_update_query = text(
                    """
                    UPDATE image_generations 
                    SET status = 'in_progress', 
                        progress = 0,
                        meta = :meta
                    WHERE id = :id
                """
                )
                await session.execute(
                    status_update_query,
                    {
                        "meta": json.dumps(current_meta),
                        "id": record_id,
                    },
                )
                await session.commit()
                logger.info(
                    f"[SceneImageTask] Updated record {record_id} status to 'in_progress'"
                )
            except Exception as db_error:
                logger.error(f"[SceneImageTask] Failed to update status: {db_error}")
                raise

            # Generate the scene image using ModelsLab service
            # ✅ FIX: Combine scene_description with custom_prompt instead of replacing it
            # custom_prompt should enhance the description (e.g., "Lighting mood: natural")
            # NOT replace the actual scene content from the book
            if custom_prompt:
                final_description = f"{scene_description}. {custom_prompt}"
            else:
                final_description = scene_description

            logger.info(f"[SceneImageTask] Final prompt: {final_description[:100]}...")

            # Fetch character image URLs if IDs are provided
            resolved_character_urls = []
            if character_ids and len(character_ids) > 0:
                try:
                    # Construct query to get image URLs for the character IDs
                    # Ensure we claim types properly for list parameter if needed,
                    # but easiest is to pass tuple or list depending on driver support.
                    # SQLModel/SQLAlchemy async usually handles list for IN clause with efficient binding.
                    # Or we can loop if few. Given strict tiers, max is likely small (1-2).

                    # Safer: fetch one by one or construct safe query
                    char_query_text = "SELECT image_url FROM image_generations WHERE id = ANY(:ids) AND status = 'completed'"
                    char_result = await session.execute(
                        text(char_query_text), {"ids": character_ids}
                    )
                    resolved_character_urls = [
                        row[0] for row in char_result.fetchall() if row[0]
                    ]

                    logger.info(
                        f"[SceneImageTask] Resolved {len(resolved_character_urls)} character URLs from {len(character_ids)} IDs"
                    )
                except Exception as e:
                    logger.warning(
                        f"[SceneImageTask] Failed to resolve character images: {e}"
                    )
                    # Proceed without resolved characters rather than failing completely
                    resolved_character_urls = []

            # Combine resolved URLs with direct URLs
            final_character_urls = list(resolved_character_urls)
            if character_image_urls:
                final_character_urls.extend(character_image_urls)

            # Remove duplicates while preserving order
            final_character_urls = list(dict.fromkeys(final_character_urls))

            if final_character_urls:
                logger.info(
                    f"[SceneImageTask] Using {len(final_character_urls)} total character references (Resolved: {len(resolved_character_urls)}, Direct: {len(character_image_urls) if character_image_urls else 0})"
                )

            image_service = ModelsLabV7ImageService()
            result = await image_service.generate_scene_image(
                scene_description=final_description,
                style=style or "cinematic",
                aspect_ratio=aspect_ratio or "16:9",
                user_tier=user_tier,
                character_image_urls=final_character_urls,
            )

            # Extract result data
            # Check for error in result (fallback manager returns dict on error)
            if result.get("status") == "error":
                raise Exception(result.get("error", "Unknown error from image service"))

            image_url = result.get("image_url")
            generation_time = result.get("generation_time", 0)
            model_used = result.get("model_used", "gen4_image")

            if not image_url:
                raise Exception("No image URL returned from ModelsLab service")

            # Prepare metadata with scene info
            existing_metadata = {}
            try:
                meta_query = text("SELECT meta FROM image_generations WHERE id = :id")
                meta_result = await session.execute(meta_query, {"id": record_id})
                meta_row = meta_result.mappings().first()
                if meta_row and meta_row.get("meta"):
                    existing_metadata = meta_row["meta"]
            except Exception as meta_error:
                logger.warning(
                    f"[SceneImageTask] Could not fetch existing metadata: {meta_error}"
                )

            # Merge metadata (note: task_id is not available in async function, remove it)
            merged_metadata = {
                **existing_metadata,
                "scene_number": scene_number,
                "script_id": script_id,
                "chapter_id": chapter_id,
                "image_type": "scene",
                "model_used": model_used,
                "generation_time": generation_time,
                "service": "modelslab_v7",
                "prompt_used": final_description,
                "style": style or "cinematic",
                "aspect_ratio": aspect_ratio or "16:9",
            }

            # Update record with success data using transaction
            try:
                success_update_query = text(
                    """
                    UPDATE image_generations 
                    SET status = 'completed', 
                        progress = 100, 
                        image_url = :image_url, 
                        updated_at = :updated_at, 
                        error_message = NULL, 
                        generation_time_seconds = :generation_time, 
                        model_id = :model_id, 
                        chapter_id = :chapter_id, 
                        script_id = :script_id, 
                        scene_number = :scene_number, 
                        image_type = 'scene', 
                        meta = :meta,
                        image_prompt = :image_prompt
                    WHERE id = :id
                """
                )

                await session.execute(
                    success_update_query,
                    {
                        "image_url": image_url,
                        "updated_at": datetime.utcnow(),
                        "generation_time": generation_time,
                        "model_id": model_used,
                        "chapter_id": chapter_id,
                        "script_id": script_id,
                        "scene_number": scene_number,
                        "scene_number": scene_number,
                        "meta": json.dumps(merged_metadata),
                        "image_prompt": final_description,
                        # Store retry count in meta via jsonb_set logic if needed, but since we are replacing metadata,
                        # we can just assume it's part of the merged_metadata if we want.
                        # However, the previous query structure used `metadata = :metadata`.
                        # Let's ensure retry_count is in metadata if we want it preserved.
                        # For now, just remove the explicit column update.
                        "id": record_id,
                    },
                )
                await session.commit()
                logger.info(
                    f"[SceneImageTask] Successfully generated scene image: {record_id}"
                )
                logger.info(f"[SceneImageTask] Image URL: {image_url}")

            except Exception as db_error:
                logger.error(
                    f"[SceneImageTask] Failed to update record with success: {db_error}"
                )
                raise

            logger.info(
                f"[SceneImageTask] Task completed successfully for record {record_id}"
            )

        except Exception as e:
            error_details = str(e) if str(e) else repr(e)
            error_message = f"Scene image generation failed: {error_details}"
            logger.error(f"[SceneImageTask] {error_message}")

            # Determine if error is retryable
            retryable_keywords = [
                "timeout",
                "connection",
                "network",
                "rate limit",
                "service unavailable",
                "temporary",
                "retry",
                "429",
                "503",
                "504",
            ]
            is_retryable = any(
                keyword in error_details.lower() for keyword in retryable_keywords
            )

            # Determine error code if available
            error_code = "UNKNOWN_ERROR"
            if "timeout" in error_details.lower():
                error_code = "TIMEOUT_ERROR"
            elif "rate limit" in error_details.lower() or "429" in error_details:
                error_code = "RATE_LIMIT_ERROR"
            elif (
                "connection" in error_details.lower()
                or "network" in error_details.lower()
            ):
                error_code = "NETWORK_ERROR"
            elif "503" in error_details or "504" in error_details:
                error_code = "SERVICE_UNAVAILABLE"

            # Update record with error before retry attempt
            try:
                # Fetch existing meta
                meta_query = text("SELECT meta FROM image_generations WHERE id = :id")
                meta_result = await session.execute(meta_query, {"id": record_id})
                meta_row = meta_result.mappings().first()
                current_meta = meta_row.get("meta") if meta_row else {}
                if current_meta is None:
                    current_meta = {}

                # Update meta in Python
                current_meta["retry_count"] = retry_count

                # Only set status to failed if not retryable or max retries exceeded
                if not is_retryable or retry_count >= 3:
                    error_update_query = text(
                        """
                        UPDATE image_generations 
                        SET error_message = :error_message, 
                            updated_at = :updated_at, 
                            status = 'failed',
                            meta = :meta
                        WHERE id = :id
                    """
                    )
                    logger.info(
                        f"[SceneImageTask] Setting status to 'failed' (retryable={is_retryable}, retry_count={retry_count})"
                    )
                else:
                    error_update_query = text(
                        """
                        UPDATE image_generations 
                        SET error_message = :error_message, 
                            updated_at = :updated_at,
                            status = 'failed',
                            meta = :meta
                        WHERE id = :id
                    """
                    )

                await session.execute(
                    error_update_query,
                    {
                        "error_message": error_message,
                        "updated_at": datetime.utcnow(),
                        "meta": json.dumps(current_meta),
                        "id": record_id,
                    },
                )
                await session.commit()

            except Exception as db_error:
                await session.rollback()
                logger.error(
                    f"[SceneImageTask] Failed to update record with error: {db_error}"
                )

            # Retry logic with exponential backoff
            if is_retryable and retry_count < 3:
                # Calculate backoff with jitter
                base_backoff = min(60, 5 * (2**retry_count))
                jitter = random.uniform(0.5, 1.5)
                backoff_seconds = int(base_backoff * jitter)

                logger.info(
                    f"[SceneImageTask] Retrying in {backoff_seconds}s (attempt {retry_count + 1}/3)"
                )

                # Increment retry count in DB before retrying
                try:
                    # Fetch existing meta
                    meta_query = text(
                        "SELECT meta FROM image_generations WHERE id = :id"
                    )
                    meta_result = await session.execute(meta_query, {"id": record_id})
                    meta_row = meta_result.mappings().first()
                    current_meta = meta_row.get("meta") if meta_row else {}
                    if current_meta is None:
                        current_meta = {}

                    # Update meta in Python
                    current_meta["retry_count"] = retry_count + 1
                    current_meta["last_attempted_at"] = datetime.utcnow().isoformat()

                    retry_update_query = text(
                        """
                        UPDATE image_generations 
                        SET meta = :meta
                        WHERE id = :id
                    """
                    )

                    await session.execute(
                        retry_update_query,
                        {
                            "meta": json.dumps(current_meta),
                            "id": record_id,
                        },
                    )
                    await session.commit()

                    # Retry the task
                    if task_instance:
                        raise task_instance.retry(exc=e, countdown=backoff_seconds)
                    else:
                        logger.warning(
                            "[SceneImageTask] No task instance available for retry"
                        )
                except Exception as db_error:
                    logger.error(f"Error updating retry count: {db_error}")
                    # Still retry even if DB update fails
                    if task_instance:
                        raise task_instance.retry(exc=e, countdown=backoff_seconds)

            logger.error(
                f"[SceneImageTask] Final failure for record {record_id}: {error_message}"
            )
            raise Exception(error_message)
