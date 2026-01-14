from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional
from app.core.services.script_parser import ScriptParser
from app.core.database import get_session
from app.core.config import settings
from datetime import datetime
from app.core.services.pipeline import PipelineManager, PipelineStep
from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService
from app.videos.models import VideoGeneration, AudioGeneration, Script
from app.subscriptions.models import UserSubscription
from app.plots.models import Character  # For character description lookup
from sqlmodel import select
import uuid
from app.core.model_config import get_model_config, ModelConfig
from app.core.services.elevenlabs import ElevenLabsService
from contextlib import asynccontextmanager
from celery.utils.log import get_task_logger

# Use Celery's task logger - this is properly captured by worker processes
logger = get_task_logger(__name__)


@asynccontextmanager
async def session_scope():
    """Context manager wrapper for get_session generator"""
    async for session in get_session():
        yield session


@celery_app.task(bind=True)
def generate_all_audio_for_video(self, video_generation_id: str):
    """Main task to generate all audio for a video generation with pipeline support"""

    async def async_generate_audio():
        pipeline_manager = PipelineManager()

        try:
            print(
                f"[AUDIO GENERATION] Starting audio generation for video: {video_generation_id}"
            )

            async with session_scope() as session:
                # Mark audio step as started
                await pipeline_manager.mark_step_started(
                    video_generation_id, PipelineStep.AUDIO_GENERATION, session
                )

                # Get video generation data
                stmt = select(VideoGeneration).where(
                    VideoGeneration.id == uuid.UUID(video_generation_id)
                )
                result = await session.exec(stmt)
                video_gen = result.first()

                if not video_gen:
                    raise Exception(f"Video generation {video_generation_id} not found")

                script_data = video_gen.script_data or {}
                chapter_id = str(video_gen.chapter_id) if video_gen.chapter_id else None
                user_id = str(video_gen.user_id) if video_gen.user_id else None

                print(f"[VIDEO AUDIO DEBUG] Video generation ID: {video_generation_id}")

                # ... (rest of main logic implicitly included here by user request,
                # but since I must replace the WHOLE function to move the try/except,
                # I need to be careful. Providing the specific block to verify structure.)
                # WAIT. replacing the whole function body with `async for` will indent everything.
                # If I don't provide the *entire* content in `ReplacementContent`, I might truncate the logic.
                # Since I am limited in token output and want to be safe:

                # I will essentially "wrap" the existing logic.
                # But since `replace_file_content` replaces a specific range, I have to match correctly.
                # I see the previous edit changed lines 27 onwards.

                # RE-STRATEGIZING:
                # I will replace the start of the function up to the first logic block,
                # AND the exception handler at the end.
                # But I cannot easily "indent" the middle part without replacing it.
                # This dictates I SHOULD probably read the whole file content for that function or take a risk with a large replace.
                # Given the previous failure, I will try to be very precise or use `sed` / `run_command`? No, `replace_file_content` is safer.

                # The issue is indentation.
                # If I change `async with` to `async for`, the indentation level is the same!
                # `async with session_scope() as session:` -> `async for session in get_session():`
                # The body block is indented by 1 tab/4spaces relative to this line regardless.
                # So I just need to replace the line `async with session_scope() as session:` with `async for session in get_session():`

                # AND I need to handle the `UnboundLocalError` in the exception block.
                # The exception block is currently OUTSIDE the session context.
                # If I change to `async for`, I still need the exception block INSIDE to access `session`.
                # BUT if I just change the line 30, the exception block (lines 313+) is structurally *after* the loop,
                # so it would only run after the loop finishes (unlikely if exception raises inside).
                # Actually, `async for` raises exceptions out of the body just like `with`.

                # So to access `session` in `except`, the `try/except` MUST be inside the `async for`.
                # Currently structure is:
                # try:
                #    async with session:
                #       ...
                # except:
                #    use session (CRASH)

                # New structure needed:
                # async for session in get_session():
                #    try:
                #       ...
                #    except:
                #       use session (OK)
                #    return (break loop)

                # This requires re-indenting the entire `try` block or moving the `async for` outside.
                # Moving `async for` outside means `try` is inside `async for`.
                # But `try` is already indented at level 2 (inside function).
                # `async for` would be level 2.
                # So `try` body needs to be level 3.
                # Currently `async with` is level 3, and its body is level 4.

                # Code structure:
                # def async_generate_audio():
                #    pipeline = ...
                #    try: (Lv 2)
                #       async with ...: (Lv 3) - wait, my previous edit put async with at Lv 3?
                #       Line 30: `            async with session_scope() as session:` (Lv 3)

                # Yes.
                # So if I change:
                # 25: try:
                # ...
                # 30: async with ...
                # TO
                # 25: async for session in get_session():
                # 26:    try:
                # ...
                # I effectively have to shift lines 26+ (which are currently `print`, `async with`...)

                # This is messy for `replace_file_content` without re-writing the whole function.
                # Is there a simpler way?
                # Use `contextlib.asynccontextmanager` on a helper function?
                # Or just `session = async_session(); try: ... finally: await session.close()`?
                # This avoids indentation changes for the main logic if I just assign `session` and manage it manually.
                # Line 23: `pipeline_manager = PipelineManager()`
                # Line 24: `session = async_session()` (imported from db)
                # Line 25: `try:`
                # ... rewrite usage ...

                # But `get_session` has nice error handling / rollback logic I want to reuse.
                # Maybe I just import `asynccontextmanager` and wrap `get_session` locally?
                # `from contextlib import asynccontextmanager`
                # `@asynccontextmanager`
                # `async def get_session_context(): async for s in get_session(): yield s`

                # Then `async with get_session_context() as session:` works and I don't change indentation!
                # AND I can wrap the *entire* function body in a `try/except` inside that context?
                # No, I still have the issue that the `except` block is after the `try` block.
                # If `async with` wraps the `try`, then `except` is outside `async with`.
                # So `session` is closed.

                # Ideally, we want the `except` block to have access to the session *before* it closes.
                # So the `try/except` should be INSIDE the `async with`.
                # Which means I MUST indent the try/except block.
                # OR I define the session variable outside.

                # PROPOSAL:
                # Use explicit session management to avoid massive re-indentation risk.

                # from app.core.database import async_session
                # session = async_session()
                # try:
                #    # logic using session
                # except Exception as e:
                #    # handle error using session
                #    await session.rollback()
                # finally:
                #    await session.close()

                # This allows `session` to be available in explicit `except` and `finally`.
                # I just need to remove the `async with` line and un-indent the block inside it by one level
                # OR just leave it `if True:` to keep indentation (hacky).
                # OR just replace `async with ...` with `if True: # wrapper to keep indentation` ? No.

                # Let's try to do it right. I will replace the wrapper code.
                pass

                # Get video generation data
                stmt = select(VideoGeneration).where(
                    VideoGeneration.id == uuid.UUID(video_generation_id)
                )
                result = await session.exec(stmt)
                video_gen = result.first()

                if not video_gen:
                    raise Exception(f"Video generation {video_generation_id} not found")
                logger.warning(
                    f"[VIDEO AUDIO DEBUG] Video generation ID: {video_generation_id}"
                )
                logger.warning(
                    f"[VIDEO AUDIO DEBUG] Retrieved chapter_id from video_gen: {chapter_id}"
                )
                logger.warning(
                    f"[VIDEO AUDIO DEBUG] Retrieved user_id from video_gen: {user_id}"
                )

                if not script_data:
                    raise Exception("No script data found for audio generation")

                # Get script_style from the scripts table
                script_id = video_gen.script_id
                script_style = "cinematic_movie"  # Default fallback

                if script_id:
                    try:
                        script_stmt = select(Script).where(Script.id == script_id)
                        script_result = await session.exec(script_stmt)
                        script = script_result.first()
                        if script:
                            script_style = script.script_style or "cinematic_movie"
                            logger.info(
                                f"[SCRIPT STYLE] Fetched from scripts table: {script_style}"
                            )
                        else:
                            logger.warning(
                                f"[SCRIPT STYLE] Script {script_id} not found, using default: {script_style}"
                            )
                    except Exception as e:
                        logger.error(
                            f"[SCRIPT STYLE] Error fetching script style: {e}, using default: {script_style}"
                        )
                else:
                    logger.warning(
                        f"[SCRIPT STYLE] No script_id found, using default: {script_style}"
                    )

                video_gen.generation_status = "generating_audio"
                session.add(video_gen)
                await session.commit()

            # Get user subscription tier for model config
            user_tier = "free"
            async with session_scope() as session:
                sub_stmt = select(UserSubscription).where(
                    UserSubscription.user_id == uuid.UUID(user_id)
                )
                sub_result = await session.exec(sub_stmt)
                subscription = sub_result.first()
                if subscription:
                    user_tier = subscription.tier

            # Get Audio Model Config
            audio_config = get_model_config("audio", user_tier)
            logger.warning(f"[AUDIO CONFIG] Tier: {user_tier}, Config: {audio_config}")

            # Parse script for audio components
            parser = ScriptParser()
            audio_components = parser.parse_script_for_audio(
                script_data.get("script", ""),
                script_data.get("characters", []),
                script_data.get("scene_descriptions", []),
                script_style,
            )

            logger.warning(f"[AUDIO PARSER] Using script style: {script_style}")
            logger.warning(
                f"[AUDIO PARSER] Characters from script_data: {script_data.get('characters', [])}"
            )

            # --- SCENE FILTERING LOGIC ---
            task_meta = video_gen.task_meta or {}
            # Handle potential None or dict mismatch if field name varies (task_meta vs task_metadata in model)
            # Route sets 'task_meta', backend model likely maps it to task_metadata JSON field

            selected_scenes = task_meta.get("selected_scene_numbers")

            # --- DEBUG: Log parsed components BEFORE filtering ---
            logger.warning(f"[AUDIO DEBUG] Raw parsed components (before filtering):")
            logger.warning(
                f"  - Narrator segments: {len(audio_components.get('narrator_segments', []))}"
            )
            for i, seg in enumerate(audio_components.get("narrator_segments", [])[:3]):
                logger.warning(
                    f"    [{i}] scene={seg.get('scene')}, text={seg.get('text', '')[:50]}..."
                )
            logger.warning(
                f"  - Character dialogues: {len(audio_components.get('character_dialogues', []))}"
            )
            for i, seg in enumerate(
                audio_components.get("character_dialogues", [])[:3]
            ):
                logger.warning(
                    f"    [{i}] scene={seg.get('scene')}, char={seg.get('character')}, text={seg.get('text', '')[:50]}..."
                )
            logger.warning(
                f"  - Sound effects: {len(audio_components.get('sound_effects', []))}"
            )
            for i, seg in enumerate(audio_components.get("sound_effects", [])[:3]):
                logger.warning(
                    f"    [{i}] scene={seg.get('scene')}, desc={seg.get('description', '')[:50]}..."
                )
            logger.warning(
                f"  - Background music: {len(audio_components.get('background_music', []))}"
            )
            for i, seg in enumerate(audio_components.get("background_music", [])[:3]):
                logger.warning(
                    f"    [{i}] scene={seg.get('scene')}, desc={seg.get('description', '')[:50]}..."
                )
            logger.warning(f"[AUDIO DEBUG] Selected scenes filter: {selected_scenes}")

            if (
                selected_scenes
                and isinstance(selected_scenes, list)
                and len(selected_scenes) > 0
            ):
                logger.info(
                    f"[AUDIO FILTER] Filtering generation for scenes: {selected_scenes}"
                )

                # Helper function to check if a scene matches selected scenes
                # Handles sub-scene matching: Scene 1 matches 1.1, 1.2, 1.3 etc.
                def matches_selected_scene(scene_value, selected_scenes):
                    if scene_value is None:
                        return False
                    scene_str = str(scene_value)
                    for s in selected_scenes:
                        s_str = str(s)
                        # Exact match
                        if scene_str == s_str:
                            return True
                        # Sub-scene match: scene 1.1 matches selected scene 1
                        # Check if scene_str starts with "s_str." (e.g., "1.1" starts with "1.")
                        if scene_str.startswith(f"{s_str}."):
                            return True
                        # Also check integer match for decimals (1.0 matches 1)
                        try:
                            scene_int = int(float(scene_value))
                            if scene_int == int(float(s)):
                                return True
                        except (ValueError, TypeError):
                            pass
                    return False

                # Filter narrator segments
                audio_components["narrator_segments"] = [
                    seg
                    for seg in audio_components.get("narrator_segments", [])
                    if matches_selected_scene(seg.get("scene"), selected_scenes)
                ]

                # Filter character dialogue
                audio_components["character_dialogues"] = [
                    seg
                    for seg in audio_components.get("character_dialogues", [])
                    if matches_selected_scene(seg.get("scene"), selected_scenes)
                ]

                # Filter sound effects
                audio_components["sound_effects"] = [
                    seg
                    for seg in audio_components.get("sound_effects", [])
                    if matches_selected_scene(seg.get("scene"), selected_scenes)
                ]

                # Filter background music
                audio_components["background_music"] = [
                    seg
                    for seg in audio_components.get("background_music", [])
                    if matches_selected_scene(seg.get("scene"), selected_scenes)
                ]
            # -----------------------------

            print(f"[AUDIO PARSER] Extracted components (Filtered if applicable):")
            print(
                f"- Narrator segments: {len(audio_components.get('narrator_segments', []))}"
            )
            print(f"- Sound effects: {len(audio_components.get('sound_effects', []))}")
            print(
                f"- Background music: {len(audio_components.get('background_music', []))}"
            )
            print(
                f"- Character dialogues: {len(audio_components.get('character_dialogues', []))}"
            )

            # Generate all audio types
            audio_service = ModelsLabV7AudioService()

            # Ensure script_id is string
            script_id_str = str(video_gen.script_id) if video_gen.script_id else None

            # Generate audio based on script style
            if script_style == "cinematic_movie" or script_style == "cinematic":
                # For cinematic: generate character dialogue + background music + sound effects
                narrator_results = []
                character_results = await generate_character_audio(
                    audio_service,
                    video_generation_id,
                    audio_components.get("character_dialogues", []),
                    chapter_id,
                    user_id,
                    script_id=script_id_str,
                    model_config=audio_config,
                )
            else:
                # For narration: generate narrator voice + background music + sound effects
                narrator_results = await generate_narrator_audio(
                    audio_service,
                    video_generation_id,
                    audio_components.get("narrator_segments", []),
                    chapter_id,
                    user_id,
                    script_id=script_id_str,
                    model_config=audio_config,
                )
                character_results = []

            # Generate sound effects
            sound_effect_results = await generate_sound_effects_audio(
                audio_service,
                video_generation_id,
                audio_components.get("sound_effects", []),
                chapter_id,
                user_id,
                script_id=script_id_str,
            )

            # Generate background music
            background_music_results = await generate_background_music(
                audio_service,
                video_generation_id,
                audio_components.get("background_music", []),
                chapter_id,
                user_id,
                script_id=script_id_str,
            )

            # Compile results
            total_audio_files = (
                len(narrator_results)
                + len(character_results)
                + len(sound_effect_results)
                + len(background_music_results)
            )

            # Update video generation with audio file references
            audio_files_data = {
                "narrator": narrator_results,
                "character": character_results,
                "sound_effects": sound_effect_results,
                "background_music": background_music_results,
            }

            async with session_scope() as session:
                stmt = select(VideoGeneration).where(
                    VideoGeneration.id == uuid.UUID(video_generation_id)
                )
                result = await session.exec(stmt)
                video_gen = result.first()

                if video_gen:
                    video_gen.audio_files = audio_files_data
                    video_gen.generation_status = "audio_completed"
                    session.add(video_gen)
                    await session.commit()

            # Mark step as completed
            pipeline_manager.mark_step_completed(
                video_generation_id,
                PipelineStep.AUDIO_GENERATION,
                {
                    "total_audio_files": total_audio_files,
                    "audio_files_data": audio_files_data,
                },
            )

            success_message = (
                f"Audio generation completed! {total_audio_files} audio files created"
            )
            print(f"[AUDIO GENERATION SUCCESS] {success_message}")

            # Check for existing images before triggering image generation
            print(
                f"[PIPELINE] Checking for existing images before starting image generation"
            )

            async with session_scope() as session:
                from app.videos.models import ImageGeneration

                images_stmt = select(ImageGeneration).where(
                    ImageGeneration.video_generation_id
                    == uuid.UUID(video_generation_id),
                    ImageGeneration.status == "completed",
                )
                images_result = await session.exec(images_stmt)
                existing_images_count = len(list(images_result.all()))

            if existing_images_count > 0:
                print(
                    f"✅ Found {existing_images_count} existing images, skipping image generation"
                )
                async with session_scope() as session:
                    stmt = select(VideoGeneration).where(
                        VideoGeneration.id == uuid.UUID(video_generation_id)
                    )
                    result = await session.exec(stmt)
                    video_gen = result.first()
                    if video_gen:
                        video_gen.generation_status = "images_completed"
                        session.add(video_gen)
                        await session.commit()
            # else:
            #     print(f"[PIPELINE] No existing images found, but assuming audio-only mode. Skipping auto-trigger of image generation.")
            #     # from app.tasks.image_tasks import generate_all_images_for_video
            #     # generate_all_images_for_video.delay(video_generation_id)

            return {
                "status": "success",
                "message": success_message,
                "audio_files_count": total_audio_files,
                "audio_data": audio_files_data,
                "next_step": None,
            }

        except Exception as e:
            error_message = f"Audio generation failed: {str(e)}"
            print(f"[AUDIO GENERATION ERROR] {error_message}")

            # Mark step as failed and update status
            async with session_scope() as session:
                await pipeline_manager.mark_step_failed(
                    video_generation_id,
                    PipelineStep.AUDIO_GENERATION,
                    error_message,
                    session,
                )

                try:
                    # Update status to failed
                    stmt = select(VideoGeneration).where(
                        VideoGeneration.id == uuid.UUID(video_generation_id)
                    )
                    result = await session.exec(stmt)
                    video_gen = result.first()
                    if video_gen:
                        video_gen.generation_status = "failed"
                        video_gen.can_resume = True
                        session.add(video_gen)
                        await session.commit()
                except Exception as update_error:
                    print(
                        f"[AUDIO GENERATION ERROR] Failed to update fail status: {str(update_error)}"
                    )

            raise Exception(error_message)

    return asyncio.run(async_generate_audio())


async def generate_narrator_audio(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    narrator_segments: List[Dict[str, Any]],
    chapter_id: Optional[str],
    user_id: Optional[str],
    script_id: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
) -> List[Dict[str, Any]]:
    """Generate narrator voice audio"""

    print(f"[NARRATOR AUDIO] Generating narrator voice...")
    narrator_results = []

    # Use V7 service voice mapping
    narrator_voice = audio_service.narrator_voices["professional"]

    for i, segment in enumerate(narrator_segments):
        try:
            scene_id = segment.get("scene", 1)
            print(
                f"[NARRATOR AUDIO] Processing segment {i+1}/{len(narrator_segments)} for scene {scene_id}"
            )
            print(
                f"[AUDIO GEN] Generating narrator audio for scene_{scene_id}: {segment['text'][:50]}..."
            )

            # Generate audio
            result = {}
            try:
                result = await audio_service.generate_tts_audio(
                    text=segment["text"],
                    voice_id=narrator_voice,
                    model_id="eleven_multilingual_v2",
                    speed=1.0,
                )
            except Exception as e:
                # Check for Fallback
                fallback_success = False
                if (
                    model_config
                    and model_config.fallback
                    and model_config.fallback.startswith("elevenlabs/")
                ):
                    print(
                        f"[NARRATOR AUDIO] ⚠️ Primary service failed: {e}. Attempting fallback to Direct ElevenLabs..."
                    )
                    try:
                        eleven_service = ElevenLabsService()
                        # Use voice mapping or default
                        fallback_result = await eleven_service.generate_enhanced_speech(
                            text=segment["text"],
                            voice_id=narrator_voice,  # Re-use same ID as they are ElevenLabs IDs
                            user_id=user_id,
                        )

                        if fallback_result and fallback_result.get("audio_url"):
                            print(f"[NARRATOR AUDIO] ✅ Fallback successful!")
                            result = {
                                "status": "success",
                                "audio_url": fallback_result.get("audio_url"),
                                "audio_time": 0,  # Duration might need calculation or be missing
                                "model_used": "direct_eleven_multilingual_v2",
                                "service": "elevenlabs_direct",
                            }
                            fallback_success = True
                        else:
                            print(
                                f"[NARRATOR AUDIO] ❌ Fallback failed: {fallback_result.get('error')}"
                            )

                    except Exception as fallback_e:
                        print(f"[NARRATOR AUDIO] ❌ Fallback exception: {fallback_e}")

                if not fallback_success:
                    raise e  # Re-raise original error if fallback didn't work

            # Extract audio URL from response
            audio_url = None
            duration = 0

            if result.get("status") == "success":
                audio_url = result.get("audio_url")
                duration = result.get("audio_time", 0)

                if not audio_url:
                    raise Exception("No audio URL in V7 response")
            else:
                raise Exception(
                    f"V7 Audio generation failed: {result.get('error', 'Unknown error')}"
                )

            print(
                f"[DEBUG] Inserting narrator audio record for video_gen {video_gen_id}"
            )
            print(
                f"[DEBUG] Audio record chapter_id: {chapter_id}, user_id: {user_id}, script_id: {script_id}"
            )

            # Create audio record
            async with session_scope() as session:
                audio_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    script_id=uuid.UUID(script_id) if script_id else None,
                    audio_type="narrator",
                    text_content=segment["text"],
                    voice_id=narrator_voice,
                    audio_url=audio_url,
                    duration_seconds=float(duration),
                    status="completed",
                    sequence_order=i + 1,
                    model_id=result.get("model_used", "eleven_multilingual_v2"),
                    scene_id=f"scene_{scene_id}",
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "line_number": segment.get("line_number", i + 1),
                        "scene": scene_id,
                        "service": "modelslab_v7",
                        "model_used": result.get(
                            "model_used", "eleven_multilingual_v2"
                        ),
                    },
                )
                session.add(audio_record)
                await session.commit()
                await session.refresh(audio_record)

                narrator_results.append(
                    {
                        "id": str(audio_record.id),
                        "scene": segment.get("scene", 1),
                        "audio_url": audio_url,
                        "duration": duration,
                        "text": segment["text"],
                    }
                )

            print(
                f"[NARRATOR AUDIO] ✅ Generated segment {i+1} - Duration: {duration}s"
            )

        except Exception as e:
            print(f"[NARRATOR AUDIO] ❌ Failed segment {i+1}: {str(e)}")

            # Store failed record
            async with session_scope() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="narrator",
                    text_content=segment["text"],
                    voice_id=narrator_voice,
                    status="failed",
                    error_message=str(e),
                    sequence_order=i + 1,
                    model_id="eleven_multilingual_v2",
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "line_number": segment.get("line_number", i + 1),
                        "scene": scene_id,
                        "service": result.get("service", "modelslab_v7"),
                        "model_used": result.get(
                            "model_used", "eleven_multilingual_v2"
                        ),
                    },
                )
                session.add(failed_record)
                await session.commit()

    print(
        f"[NARRATOR AUDIO] Completed: {len(narrator_results)}/{len(narrator_segments)} segments"
    )
    return narrator_results


async def generate_character_audio(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    character_dialogues: List[Dict[str, Any]],
    chapter_id: Optional[str],
    user_id: Optional[str],
    script_id: Optional[str] = None,
    model_config: Optional[ModelConfig] = None,
) -> List[Dict[str, Any]]:
    """Generate character voice audio for cinematic scripts"""

    print(f"[CHARACTER AUDIO] Generating character voices...")
    character_results = []

    # Get available character voices - organized by gender
    male_voices = [
        (name, vid)
        for name, vid in audio_service.character_voices.items()
        if "male" in name.lower() and "female" not in name.lower()
    ]
    female_voices = [
        (name, vid)
        for name, vid in audio_service.character_voices.items()
        if "female" in name.lower()
    ]
    all_voices = list(audio_service.character_voices.items())
    character_voice_mapping = {}

    # Fetch character descriptions from database for enhanced gender detection
    character_descriptions = {}  # name -> {role, physical_description, personality}
    if user_id:
        try:
            async with session_scope() as session:
                stmt = select(Character).where(Character.user_id == uuid.UUID(user_id))
                result = await session.exec(stmt)
                db_characters = result.all()

                for char in db_characters:
                    # Store with multiple name variations for matching
                    name_key = char.name.upper().strip()
                    character_descriptions[name_key] = {
                        "role": char.role or "",
                        "physical_description": char.physical_description or "",
                        "personality": char.personality or "",
                        "entity_type": char.entity_type or "character",
                    }
                    # Also store by last name only for better matching
                    name_parts = name_key.split()
                    if len(name_parts) > 1:
                        character_descriptions[name_parts[-1]] = character_descriptions[
                            name_key
                        ]

                print(
                    f"[CHARACTER AUDIO] Loaded {len(db_characters)} character descriptions from DB"
                )
        except Exception as e:
            print(
                f"[CHARACTER AUDIO] Warning: Could not load character descriptions: {e}"
            )

    # Gender detection helper
    def detect_character_gender(name: str) -> str:
        """Detect gender from character name. Returns 'male', 'female', or 'unknown'."""
        name_upper = name.upper().strip()

        # Female indicators
        female_prefixes = [
            "MRS.",
            "MRS ",
            "MS.",
            "MS ",
            "MISS ",
            "MISS.",
            "LADY ",
            "LADY.",
            "QUEEN ",
            "PRINCESS ",
            "DUCHESS ",
            "MADAM ",
            "MADAME ",
        ]
        female_names = [
            "SHE",
            "HER",
            "HERSELF",
            "WOMAN",
            "GIRL",
            "MOTHER",
            "MOM",
            "MAMMA",
            "SISTER",
            "AUNT",
            "GRANDMOTHER",
            "GRANDMA",
            "WIFE",
            "DAUGHTER",
            "NIECE",
            "GODMOTHER",
            "WITCH",
            "SORCERESS",
            "PRIESTESS",
            "ACTRESS",
            "WAITRESS",
            "HOSTESS",
            "STEWARDESS",
            "EMPRESS",
        ]

        # Male indicators
        male_prefixes = [
            "MR.",
            "MR ",
            "SIR ",
            "SIR.",
            "LORD ",
            "LORD.",
            "KING ",
            "PRINCE ",
            "DUKE ",
            "MASTER ",
        ]
        male_names = [
            "HE",
            "HIM",
            "HIMSELF",
            "MAN",
            "BOY",
            "FATHER",
            "DAD",
            "PAPA",
            "BROTHER",
            "UNCLE",
            "GRANDFATHER",
            "GRANDPA",
            "HUSBAND",
            "SON",
            "NEPHEW",
            "GODFATHER",
            "WIZARD",
            "SORCERER",
            "PRIEST",
            "ACTOR",
            "WAITER",
            "HOST",
            "STEWARD",
            "EMPEROR",
        ]

        # Check prefixes first (most reliable)
        for prefix in female_prefixes:
            if name_upper.startswith(prefix):
                return "female"
        for prefix in male_prefixes:
            if name_upper.startswith(prefix):
                return "male"

        # Check if name contains gender-specific words
        name_words = name_upper.replace(".", " ").split()
        for word in name_words:
            if word in female_names:
                return "female"
            if word in male_names:
                return "male"

        # Common female first names (when all else fails)
        female_first_names = [
            "LILY",
            "PETUNIA",
            "HERMIONE",
            "MOLLY",
            "MINERVA",
            "MARY",
            "ELIZABETH",
            "SARAH",
            "JANE",
            "EMMA",
            "ANNA",
            "ROSE",
            "ALICE",
            "SUSAN",
            "HELEN",
            "MARGARET",
            "NANCY",
        ]
        for first_name in female_first_names:
            if first_name in name_upper:
                return "female"

        # Check character descriptions from database (enhanced detection)
        # Look up by full name or last name
        char_desc = None
        if name_upper in character_descriptions:
            char_desc = character_descriptions[name_upper]
        else:
            # Try last name only
            name_parts = name_upper.split()
            if name_parts:
                last_name = name_parts[-1]
                if last_name in character_descriptions:
                    char_desc = character_descriptions[last_name]

        if char_desc:
            # Combine all description fields for analysis
            full_desc = f"{char_desc.get('role', '')} {char_desc.get('physical_description', '')} {char_desc.get('personality', '')}".upper()

            # Female indicators in descriptions
            female_desc_words = [
                "SHE",
                "HER",
                "HERSELF",
                "WOMAN",
                "FEMALE",
                "LADY",
                "GIRL",
                "WITCH",
                "SISTER",
                "MOTHER",
                "DAUGHTER",
                "WIFE",
                "AUNT",
                "GRANDMOTHER",
                "PRINCESS",
                "QUEEN",
                "DUCHESS",
                "EMPRESS",
                "PRIESTESS",
                "SORCERESS",
                "ACTRESS",
                "WAITRESS",
            ]

            # Male indicators in descriptions
            male_desc_words = [
                "HE",
                "HIS",
                "HIM",
                "HIMSELF",
                "MAN",
                "MALE",
                "GUY",
                "BOY",
                "WIZARD",
                "BROTHER",
                "FATHER",
                "SON",
                "HUSBAND",
                "UNCLE",
                "GRANDFATHER",
                "PRINCE",
                "KING",
                "DUKE",
                "EMPEROR",
                "PRIEST",
                "SORCERER",
                "ACTOR",
                "WAITER",
                "HALF-GIANT",
                "GIANT",
            ]

            female_score = sum(1 for word in female_desc_words if word in full_desc)
            male_score = sum(1 for word in male_desc_words if word in full_desc)

            if female_score > male_score:
                print(
                    f"[CHARACTER AUDIO] Detected FEMALE from description: {name_upper} (score: {female_score} vs {male_score})"
                )
                return "female"
            elif male_score > female_score:
                print(
                    f"[CHARACTER AUDIO] Detected MALE from description: {name_upper} (score: {male_score} vs {female_score})"
                )
                return "male"

        return "unknown"

    for i, dialogue in enumerate(character_dialogues):
        try:
            character_name = dialogue["character"]
            scene_id = dialogue.get("scene", 1)
            print(
                f"[CHARACTER AUDIO] Processing dialogue {i+1}/{len(character_dialogues)} for {character_name} in scene {scene_id}"
            )

            # Assign voice to character if not already assigned
            if character_name not in character_voice_mapping:
                # Detect gender and select appropriate voice
                gender = detect_character_gender(character_name)

                if gender == "female" and female_voices:
                    # Select from female voices
                    voice_index = hash(character_name) % len(female_voices)
                    voice_name, voice_id = female_voices[voice_index]
                    print(
                        f"[CHARACTER AUDIO] Detected FEMALE: {character_name} -> {voice_name}"
                    )
                elif gender == "male" and male_voices:
                    # Select from male voices
                    voice_index = hash(character_name) % len(male_voices)
                    voice_name, voice_id = male_voices[voice_index]
                    print(
                        f"[CHARACTER AUDIO] Detected MALE: {character_name} -> {voice_name}"
                    )
                else:
                    # Unknown gender - use hash-based selection from all voices
                    voice_index = hash(character_name) % len(all_voices)
                    voice_name, voice_id = all_voices[voice_index]
                    print(
                        f"[CHARACTER AUDIO] Unknown gender: {character_name} -> {voice_name}"
                    )

                character_voice_mapping[character_name] = {
                    "voice_name": voice_name,
                    "voice_id": voice_id,
                    "detected_gender": gender,
                }
                print(
                    f"[CHARACTER AUDIO] Assigned voice '{voice_name}' ({gender}) to {character_name}"
                )

            voice_info = character_voice_mapping[character_name]

            # Generate audio
            result = {}
            try:
                result = await audio_service.generate_tts_audio(
                    text=dialogue["text"],
                    voice_id=voice_info["voice_id"],
                    model_id="eleven_multilingual_v2",
                    speed=1.0,
                )
            except Exception as e:
                # Check for Fallback
                fallback_success = False
                if (
                    model_config
                    and model_config.fallback
                    and model_config.fallback.startswith("elevenlabs/")
                ):
                    print(
                        f"[CHARACTER AUDIO] ⚠️ Primary service failed: {e}. Attempting fallback to Direct ElevenLabs..."
                    )
                    try:
                        eleven_service = ElevenLabsService()
                        fallback_result = await eleven_service.generate_enhanced_speech(
                            text=dialogue["text"],
                            voice_id=voice_info["voice_id"],
                            user_id=user_id,
                        )

                        if fallback_result and fallback_result.get("audio_url"):
                            print(f"[CHARACTER AUDIO] ✅ Fallback successful!")
                            result = {
                                "status": "success",
                                "audio_url": fallback_result.get("audio_url"),
                                "audio_time": 0,
                                "model_used": "direct_eleven_multilingual_v2",
                                "service": "elevenlabs_direct",
                            }
                            fallback_success = True
                    except Exception as fallback_e:
                        print(f"[CHARACTER AUDIO] ❌ Fallback exception: {fallback_e}")

                if not fallback_success:
                    raise e

            audio_url = None
            duration = 0

            if result.get("status") == "success":
                audio_url = result.get("audio_url")
                duration = result.get("audio_time", 0)

                if not audio_url:
                    raise Exception("No audio URL in V7 response")
            else:
                raise Exception(
                    f"V7 Audio generation failed: {result.get('error', 'Unknown error')}"
                )

            # Store in database
            async with session_scope() as session:
                audio_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    script_id=uuid.UUID(script_id) if script_id else None,
                    audio_type="character",
                    text_content=dialogue["text"],
                    voice_id=voice_info["voice_id"],
                    audio_url=audio_url,
                    duration_seconds=float(duration),
                    status="completed",
                    sequence_order=i + 1,
                    model_id=result.get("model_used", "eleven_multilingual_v2"),
                    scene_id=f"scene_{scene_id}",
                    character_name=character_name,
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "character_name": character_name,
                        "voice_name": voice_info["voice_name"],
                        "line_number": dialogue.get("line_number", i + 1),
                        "scene": scene_id,
                        "scene": scene_id,
                        "service": result.get("service", "modelslab_v7"),
                        "model_used": result.get(
                            "model_used", "eleven_multilingual_v2"
                        ),
                        "model_used": result.get(
                            "model_used", "eleven_multilingual_v2"
                        ),
                    },
                )
                session.add(audio_record)
                await session.commit()
                await session.refresh(audio_record)

                character_results.append(
                    {
                        "id": str(audio_record.id),
                        "character": character_name,
                        "voice_name": voice_info["voice_name"],
                        "voice_id": voice_info["voice_id"],
                        "scene": dialogue.get("scene", 1),
                        "audio_url": audio_url,
                        "duration": duration,
                        "text": dialogue["text"],
                    }
                )

            print(
                f"[CHARACTER AUDIO] ✅ Generated dialogue {i+1} for {character_name} - Duration: {duration}s"
            )

        except Exception as e:
            print(
                f"[CHARACTER AUDIO] ❌ Failed dialogue {i+1} for {dialogue.get('character', 'Unknown')}: {str(e)}"
            )

            character_name = dialogue["character"]
            voice_info = character_voice_mapping.get(
                character_name, {"voice_name": "unknown", "voice_id": "unknown"}
            )

            async with session_scope() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="character",
                    text_content=dialogue["text"],
                    voice_id=voice_info["voice_id"],
                    status="failed",
                    error_message=str(e),
                    sequence_order=i + 1,
                    model_id="eleven_multilingual_v2",
                    character_name=character_name,
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "character_name": character_name,
                        "voice_name": voice_info["voice_name"],
                        "line_number": dialogue.get("line_number", i + 1),
                        "scene": dialogue.get("scene", 1),
                        "service": "modelslab_v7",
                    },
                )
                session.add(failed_record)
                await session.commit()

    # Store character voice mappings
    if character_voice_mapping:
        async with session_scope() as session:
            stmt = select(VideoGeneration).where(
                VideoGeneration.id == uuid.UUID(video_gen_id)
            )
            result = await session.exec(stmt)
            video_gen = result.first()
            if video_gen:
                # Add character_voice_mappings to video_data or task_meta
                task_meta = video_gen.task_meta or {}
                task_meta["character_voice_mappings"] = character_voice_mapping
                video_gen.task_meta = task_meta
                session.add(video_gen)
                await session.commit()
        print(f"[CHARACTER AUDIO] Stored voice mappings: {character_voice_mapping}")

    print(
        f"[CHARACTER AUDIO] Completed: {len(character_results)}/{len(character_dialogues)} dialogues"
    )
    return character_results


async def generate_sound_effects_audio(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    sound_effects: List[Dict[str, Any]],
    chapter_id: Optional[str],
    user_id: Optional[str],
    script_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate sound effects audio"""

    print(f"[SOUND EFFECTS] Generating sound effects...")
    effects_results = []

    for i, effect in enumerate(sound_effects):
        try:
            print(
                f"[SOUND EFFECTS] Processing effect {i+1}/{len(sound_effects)}: {effect['description']}"
            )

            # Use V7 sound effects generation
            result = await audio_service.generate_sound_effect(
                description=effect["description"],
                duration=min(30.0, max(3.0, effect.get("duration", 10.0))),
                model_id="eleven_sound_effect",
            )

            if result.get("status") == "success":
                audio_url = result.get("audio_url")
                duration = result.get("audio_time", 10)

                if not audio_url:
                    raise Exception("No audio URL in V7 response")

                # Using passed script_id

                # Store in database
                async with session_scope() as session:
                    audio_record = AudioGeneration(
                        video_generation_id=uuid.UUID(video_gen_id),
                        user_id=uuid.UUID(user_id) if user_id else None,
                        chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                        script_id=uuid.UUID(script_id) if script_id else None,
                        audio_type="sfx",
                        text_content=effect["description"],
                        audio_url=audio_url,
                        duration_seconds=float(duration),
                        sequence_order=i + 1,
                        status="completed",
                        audio_metadata={
                            "chapter_id": chapter_id,
                            "effect_type": effect.get("type", "sound_effect"),
                            "service": "modelslab_v7",
                            "model_used": result.get(
                                "model_used", "eleven_sound_effect"
                            ),
                        },
                    )
                    session.add(audio_record)
                    await session.commit()
                    await session.refresh(audio_record)

                    effects_results.append(
                        {
                            "effect_id": i + 1,
                            "audio_url": audio_url,
                            "description": effect["description"],
                            "duration": duration,
                            "db_id": str(audio_record.id),
                        }
                    )

                print(f"[SOUND EFFECTS] ✅ Effect {i+1} completed: {audio_url}")
            else:
                raise Exception(
                    f"V7 API returned error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(f"[SOUND EFFECTS] ❌ Failed: {effect['description']} - {str(e)}")

            # Store failed record
            async with session_scope() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="sfx",
                    text_content=effect["description"],
                    error_message=str(e),
                    sequence_order=i + 1,
                    status="failed",
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "service": "modelslab_v7",
                    },
                )
                session.add(failed_record)
                await session.commit()
            continue

    print(
        f"[SOUND EFFECTS] Completed: {len(effects_results)}/{len(sound_effects)} effects"
    )
    return effects_results


async def generate_background_music(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    music_cues: List[Dict[str, Any]],
    chapter_id: Optional[str],
    user_id: Optional[str],
    script_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate background music"""

    logger.info(f"[BACKGROUND MUSIC] Generating background music...")
    music_results = []

    for i, music_cue in enumerate(music_cues):
        try:
            scene_id = music_cue["scene"]
            logger.info(
                f"[BACKGROUND MUSIC] Processing scene {scene_id}: {music_cue['description']}"
            )

            # Use V7 music generation
            result = await audio_service.generate_background_music(
                description=music_cue["description"],
                model_id="music_v1",
                duration=30.0,
            )

            if result.get("status") == "success":
                audio_url = result.get("audio_url")
                duration = result.get("audio_time", 30.0)

                if not audio_url:
                    raise Exception("No audio URL in V7 response")

                # Using passed script_id

                # Store in database
                async with session_scope() as session:
                    audio_record = AudioGeneration(
                        video_generation_id=uuid.UUID(video_gen_id),
                        user_id=uuid.UUID(user_id) if user_id else None,
                        chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                        script_id=uuid.UUID(script_id) if script_id else None,
                        audio_type="background_music",
                        text_content=music_cue["description"],
                        audio_url=audio_url,
                        duration_seconds=float(duration),
                        status="completed",
                        sequence_order=i + 1,
                        scene_id=f"scene_{scene_id}",
                        audio_metadata={
                            "chapter_id": chapter_id,
                            "music_type": music_cue.get("type", "background_music"),
                            "scene": scene_id,
                            "service": "modelslab_v7",
                            "model_used": result.get("model_used", "music_v1"),
                        },
                    )
                    session.add(audio_record)
                    await session.commit()
                    await session.refresh(audio_record)

                    music_results.append(
                        {
                            "id": str(audio_record.id),
                            "scene": music_cue["scene"],
                            "audio_url": audio_url,
                            "description": music_cue["description"],
                            "duration": duration,
                        }
                    )

                print(f"[BACKGROUND MUSIC] ✅ Generated for Scene {music_cue['scene']}")
            else:
                raise Exception(
                    f"V7 API returned error: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            print(
                f"[BACKGROUND MUSIC] ❌ Failed for Scene {music_cue['scene']}: {str(e)}"
            )

            # Store failed record
            async with session_scope() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="background_music",
                    text_content=music_cue["description"],
                    status="failed",
                    error_message=str(e),
                    sequence_order=i + 1,
                    audio_metadata={
                        "chapter_id": chapter_id,
                        "service": "modelslab_v7",
                    },
                )
                session.add(failed_record)
                await session.commit()

    print(
        f"[BACKGROUND MUSIC] Completed: {len(music_results)}/{len(music_cues)} music tracks"
    )
    return music_results


@celery_app.task(bind=True)
def generate_chapter_audio_task(
    self,
    audio_type: str,
    text_content: str,
    user_id: str,
    chapter_id: str,
    scene_number: int,
    voice_id: str = None,
    emotion: str = "neutral",
    speed: float = 1.0,
    duration: float = None,
    record_id: str = None,
):
    """Generate audio for a chapter scene"""

    async def async_generate_chapter_audio():
        from app.core.services.elevenlabs import ElevenLabsService
        from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService

        try:
            print(
                f"[CHAPTER AUDIO] Starting {audio_type} generation for chapter {chapter_id}, scene {scene_number}, user {user_id}"
            )
            print(
                f"[DEBUG] Task parameters - record_id: {record_id}, voice_id: {voice_id}"
            )

            # Get the existing record
            async with session_scope() as session:
                if record_id:
                    stmt = select(AudioGeneration).where(
                        AudioGeneration.id == uuid.UUID(record_id)
                    )
                    result = await session.exec(stmt)
                    existing_record = result.first()

                    if existing_record:
                        record_chapter_id = (
                            str(existing_record.chapter_id)
                            if existing_record.chapter_id
                            else chapter_id
                        )
                        print(
                            f"[DEBUG] Existing record chapter_id: {record_chapter_id}"
                        )
                        chapter_id = record_chapter_id
                    else:
                        print(f"[ERROR] Record {record_id} not found!")

            # Update status to processing
            async with session_scope() as session:
                if record_id:
                    stmt = select(AudioGeneration).where(
                        AudioGeneration.id == uuid.UUID(record_id)
                    )
                    result = await session.exec(stmt)
                    audio_record = result.first()
                    if audio_record:
                        audio_record.status = "processing"
                        session.add(audio_record)
                        await session.commit()

            # Get user's subscription tier
            user_tier = "free"
            async with session_scope() as session:
                try:
                    subscription_stmt = select(UserSubscription).where(
                        UserSubscription.user_id == uuid.UUID(user_id),
                        UserSubscription.status == "active",
                    )
                    subscription_result = await session.exec(subscription_stmt)
                    subscription = subscription_result.first()
                    if subscription:
                        user_tier = subscription.tier or "free"
                except Exception as e:
                    print(f"[DEBUG] Could not get user tier: {e}")

            print(f"[DEBUG] User tier: {user_tier}")

            # Choose service based on user tier and audio type
            use_elevenlabs = user_tier == "pro" and audio_type in [
                "narrator",
                "character",
            ]

            if use_elevenlabs:
                # Use ElevenLabs for voice generation (pro users only)
                async with session_scope() as session:
                    audio_service = ElevenLabsService()
                    result = audio_service.generate_enhanced_speech(
                        text=text_content,
                        voice_id=voice_id or "21m00Tcm4TlvDq8ikWAM",
                        user_id=user_id,
                        emotion=emotion,
                        speed=speed,
                    )

                    if result and result.get("audio_url"):
                        audio_url = result["audio_url"]
                        audio_duration = None
                    else:
                        raise Exception("Failed to generate audio with ElevenLabs")
            else:
                # Use ModelsLab for all audio types
                audio_service = ModelsLabV7AudioService()

                if audio_type in ["narrator", "character"]:
                    result = await audio_service.generate_tts_audio(
                        text=text_content,
                        voice_id=voice_id or "en-US-Neural2-D",
                        model_id="eleven_multilingual_v2",
                        speed=speed,
                    )
                elif audio_type == "music":
                    result = await audio_service.generate_sound_effect(
                        description=text_content, duration=duration or 30.0
                    )
                else:
                    result = await audio_service.generate_sound_effect(
                        description=text_content, duration=duration or 10.0
                    )

                if result.get("status") == "success":
                    audio_url = result.get("audio_url")
                    audio_duration = result.get("audio_time", duration)
                else:
                    raise Exception(
                        f"Failed to generate {audio_type}: {result.get('error', 'Unknown error')}"
                    )

            # Update the record with success
            async with session_scope() as session:
                if record_id:
                    stmt = select(AudioGeneration).where(
                        AudioGeneration.id == uuid.UUID(record_id)
                    )
                    result = await session.exec(stmt)
                    audio_record = result.first()
                    if audio_record:
                        audio_record.audio_url = audio_url
                        audio_record.status = "completed"
                        audio_record.duration_seconds = audio_duration
                        audio_record.chapter_id = (
                            uuid.UUID(chapter_id) if chapter_id else None
                        )
                        audio_record.model_id = (
                            "elevenlabs" if use_elevenlabs else "modelslab"
                        )
                        audio_record.metadata = {
                            "chapter_id": chapter_id,
                            "scene_number": scene_number,
                            "audio_type": audio_type,
                            "voice_id": voice_id,
                            "emotion": emotion,
                            "speed": speed,
                            "service_used": (
                                "elevenlabs" if use_elevenlabs else "modelslab"
                            ),
                        }
                        session.add(audio_record)
                        await session.commit()

            print(
                f"[CHAPTER AUDIO] ✅ {audio_type} generation completed for chapter {chapter_id}"
            )
            return {"status": "success", "audio_url": audio_url, "record_id": record_id}

        except Exception as e:
            error_message = f"Chapter audio generation failed: {str(e)}"
            print(f"[CHAPTER AUDIO ERROR] {error_message}")

            # Update record with failure
            async with session_scope() as session:
                if record_id:
                    stmt = select(AudioGeneration).where(
                        AudioGeneration.id == uuid.UUID(record_id)
                    )
                    result = await session.exec(stmt)
                    audio_record = result.first()
                    if audio_record:
                        audio_record.status = "failed"
                        audio_record.error_message = error_message
                        session.add(audio_record)
                        await session.commit()

            raise Exception(error_message)

    return asyncio.run(async_generate_chapter_audio())


@celery_app.task(bind=True)
def export_chapter_audio_mix_task(
    self,
    export_id: str,
    chapter_id: str,
    user_id: str,
    audio_files: list,
    export_format: str = "mp3",
    mix_settings: dict = None,
):
    """Export mixed audio for a chapter"""

    async def async_export_audio():
        from app.core.services.elevenlabs import ElevenLabsService

        try:
            print(f"[AUDIO EXPORT] Starting export for chapter {chapter_id}")

            # Update export status to processing (assuming you have an AudioExport model)
            # For now, just proceed with mixing

            # Prepare audio tracks for mixing
            audio_tracks = []
            for audio_file in audio_files:
                if audio_file.get("audio_url"):
                    track_info = {
                        "url": audio_file["audio_url"],
                        "type": audio_file.get("audio_type"),
                        "volume": (
                            mix_settings.get(
                                f"{audio_file.get('audio_type')}_volume", 1.0
                            )
                            if mix_settings
                            else 1.0
                        ),
                    }
                    audio_tracks.append(track_info)

            if not audio_tracks:
                raise Exception("No valid audio tracks found for mixing")

            # Use ElevenLabs service for mixing
            audio_service = ElevenLabsService()
            mix_result = audio_service.mix_audio_tracks(audio_tracks, user_id)

            if mix_result and mix_result.get("audio_url"):
                download_url = mix_result["audio_url"]
                print(f"[AUDIO EXPORT] ✅ Export completed for chapter {chapter_id}")
                return {
                    "status": "success",
                    "download_url": download_url,
                    "export_id": export_id,
                }
            else:
                raise Exception("Failed to mix audio tracks")

        except Exception as e:
            error_message = f"Audio export failed: {str(e)}"
            print(f"[AUDIO EXPORT ERROR] {error_message}")
            raise Exception(error_message)

    return asyncio.run(async_export_audio())
