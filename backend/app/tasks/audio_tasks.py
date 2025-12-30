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
from app.subscription.models import UserSubscription
from sqlmodel import select
import uuid


@celery_app.task(bind=True)
def generate_all_audio_for_video(self, video_generation_id: str):
    """Main task to generate all audio for a video generation with pipeline support"""

    async def async_generate_audio():
        pipeline_manager = PipelineManager()

        try:
            print(
                f"[AUDIO GENERATION] Starting audio generation for video: {video_generation_id}"
            )

            # Mark audio step as started
            pipeline_manager.mark_step_started(
                video_generation_id, PipelineStep.AUDIO_GENERATION
            )

            # Get video generation data
            async with get_session() as session:
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
                print(
                    f"[VIDEO AUDIO DEBUG] Retrieved chapter_id from video_gen: {chapter_id}"
                )
                print(
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
                            print(
                                f"[SCRIPT STYLE] Fetched from scripts table: {script_style}"
                            )
                        else:
                            print(
                                f"[SCRIPT STYLE] Script {script_id} not found, using default: {script_style}"
                            )
                    except Exception as e:
                        print(
                            f"[SCRIPT STYLE] Error fetching script style: {e}, using default: {script_style}"
                        )
                else:
                    print(
                        f"[SCRIPT STYLE] No script_id found, using default: {script_style}"
                    )

                # Update status
                video_gen.generation_status = "generating_audio"
                session.add(video_gen)
                await session.commit()

            # Parse script for audio components
            parser = ScriptParser()
            audio_components = parser.parse_script_for_audio(
                script_data.get("script", ""),
                script_data.get("characters", []),
                script_data.get("scene_descriptions", []),
                script_style,
            )

            print(f"[AUDIO PARSER] Using script style: {script_style}")
            print(
                f"[AUDIO PARSER] Characters from script_data: {script_data.get('characters', [])}"
            )
            print(
                f"[AUDIO PARSER] Script sample: {script_data.get('script', '')[:200]}..."
            )
            print(f"[AUDIO PARSER] Extracted components:")
            print(f"- Narrator segments: {len(audio_components['narrator_segments'])}")
            print(f"- Sound effects: {len(audio_components['sound_effects'])}")
            print(f"- Background music: {len(audio_components['background_music'])}")

            # Generate all audio types
            audio_service = ModelsLabV7AudioService()

            # Generate audio based on script style
            if script_style == "cinematic_movie":
                # For cinematic: only background music and sound effects
                narrator_results = []
                character_results = []
            else:
                # For narration: generate narrator voice + background music + sound effects
                narrator_results = await generate_narrator_audio(
                    audio_service,
                    video_generation_id,
                    audio_components["narrator_segments"],
                    chapter_id,
                    user_id,
                )
                character_results = []

            # Generate sound effects
            sound_effect_results = await generate_sound_effects_audio(
                audio_service,
                video_generation_id,
                audio_components["sound_effects"],
                chapter_id,
                user_id,
            )

            # Generate background music
            background_music_results = await generate_background_music(
                audio_service,
                video_generation_id,
                audio_components["background_music"],
                chapter_id,
                user_id,
            )

            # Compile results
            total_audio_files = (
                len(narrator_results)
                + len(sound_effect_results)
                + len(background_music_results)
            )

            # Update video generation with audio file references
            audio_files_data = {
                "narrator": narrator_results,
                "sound_effects": sound_effect_results,
                "background_music": background_music_results,
            }

            async with get_session() as session:
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

            async with get_session() as session:
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
                async with get_session() as session:
                    stmt = select(VideoGeneration).where(
                        VideoGeneration.id == uuid.UUID(video_generation_id)
                    )
                    result = await session.exec(stmt)
                    video_gen = result.first()
                    if video_gen:
                        video_gen.generation_status = "images_completed"
                        session.add(video_gen)
                        await session.commit()
            else:
                print(f"[PIPELINE] No existing images found, starting image generation")
                from app.tasks.image_tasks import generate_all_images_for_video

                generate_all_images_for_video.delay(video_generation_id)

            return {
                "status": "success",
                "message": success_message + " - Starting image generation...",
                "audio_files_count": total_audio_files,
                "audio_data": audio_files_data,
                "next_step": "image_generation",
            }

        except Exception as e:
            error_message = f"Audio generation failed: {str(e)}"
            print(f"[AUDIO GENERATION ERROR] {error_message}")

            # Mark step as failed
            pipeline_manager.mark_step_failed(
                video_generation_id, PipelineStep.AUDIO_GENERATION, error_message
            )

            # Update status to failed
            try:
                async with get_session() as session:
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
            except:
                pass

            raise Exception(error_message)

    return asyncio.run(async_generate_audio())


async def generate_narrator_audio(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    narrator_segments: List[Dict[str, Any]],
    chapter_id: Optional[str],
    user_id: Optional[str],
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
            result = await audio_service.generate_tts_audio(
                text=segment["text"],
                voice_id=narrator_voice,
                model_id="eleven_multilingual_v2",
                speed=1.0,
            )

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
            print(f"[DEBUG] Audio record chapter_id: {chapter_id}, user_id: {user_id}")

            # Get script_id from video generation
            script_id = None
            async with get_session() as session:
                try:
                    stmt = select(VideoGeneration).where(
                        VideoGeneration.id == uuid.UUID(video_gen_id)
                    )
                    result_vid = await session.exec(stmt)
                    video_gen = result_vid.first()
                    if video_gen:
                        script_id = (
                            str(video_gen.script_id) if video_gen.script_id else None
                        )
                except Exception as e:
                    print(f"[DEBUG] Could not get script_id from video generation: {e}")

            # Create audio record
            async with get_session() as session:
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
            async with get_session() as session:
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
                        "scene": segment.get("scene", 1),
                        "service": "modelslab_v7",
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
) -> List[Dict[str, Any]]:
    """Generate character voice audio for cinematic scripts"""

    print(f"[CHARACTER AUDIO] Generating character voices...")
    character_results = []

    # Get available character voices
    available_voices = list(audio_service.character_voices.items())
    character_voice_mapping = {}

    for i, dialogue in enumerate(character_dialogues):
        try:
            character_name = dialogue["character"]
            scene_id = dialogue.get("scene", 1)
            print(
                f"[CHARACTER AUDIO] Processing dialogue {i+1}/{len(character_dialogues)} for {character_name} in scene {scene_id}"
            )

            # Assign voice to character if not already assigned
            if character_name not in character_voice_mapping:
                voice_index = hash(character_name) % len(available_voices)
                voice_name, voice_id = available_voices[voice_index]
                character_voice_mapping[character_name] = {
                    "voice_name": voice_name,
                    "voice_id": voice_id,
                }
                print(
                    f"[CHARACTER AUDIO] Assigned voice '{voice_name}' to {character_name}"
                )

            voice_info = character_voice_mapping[character_name]

            # Generate audio
            result = await audio_service.generate_tts_audio(
                text=dialogue["text"],
                voice_id=voice_info["voice_id"],
                model_id="eleven_multilingual_v2",
                speed=1.0,
            )

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

            # Get script_id
            script_id = None
            async with get_session() as session:
                try:
                    stmt = select(VideoGeneration).where(
                        VideoGeneration.id == uuid.UUID(video_gen_id)
                    )
                    result_vid = await session.exec(stmt)
                    video_gen = result_vid.first()
                    if video_gen:
                        script_id = (
                            str(video_gen.script_id) if video_gen.script_id else None
                        )
                except Exception as e:
                    print(f"[DEBUG] Could not get script_id: {e}")

            # Store in database
            async with get_session() as session:
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
                        "service": "modelslab_v7",
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

            async with get_session() as session:
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
        async with get_session() as session:
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

                # Get script_id
                script_id = None
                async with get_session() as session:
                    try:
                        stmt = select(VideoGeneration).where(
                            VideoGeneration.id == uuid.UUID(video_gen_id)
                        )
                        result_vid = await session.exec(stmt)
                        video_gen = result_vid.first()
                        if video_gen:
                            script_id = (
                                str(video_gen.script_id)
                                if video_gen.script_id
                                else None
                            )
                    except Exception as e:
                        print(f"[DEBUG] Could not get script_id: {e}")

                # Store in database
                async with get_session() as session:
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
                            "effect_type": "ambient",
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
            async with get_session() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="sfx",
                    text_content=effect["description"],
                    error_message=str(e),
                    sequence_order=i + 1,
                    status="failed",
                    audio_metadata={"chapter_id": chapter_id, "service": "modelslab_v7"},
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
) -> List[Dict[str, Any]]:
    """Generate background music"""

    print(f"[BACKGROUND MUSIC] Generating background music...")
    music_results = []

    for i, music_cue in enumerate(music_cues):
        try:
            scene_id = music_cue["scene"]
            print(
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

                # Get script_id
                script_id = None
                async with get_session() as session:
                    try:
                        stmt = select(VideoGeneration).where(
                            VideoGeneration.id == uuid.UUID(video_gen_id)
                        )
                        result_vid = await session.exec(stmt)
                        video_gen = result_vid.first()
                        if video_gen:
                            script_id = (
                                str(video_gen.script_id)
                                if video_gen.script_id
                                else None
                            )
                    except Exception as e:
                        print(f"[DEBUG] Could not get script_id: {e}")

                # Store in database
                async with get_session() as session:
                    audio_record = AudioGeneration(
                        video_generation_id=uuid.UUID(video_gen_id),
                        user_id=uuid.UUID(user_id) if user_id else None,
                        chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                        script_id=uuid.UUID(script_id) if script_id else None,
                        audio_type="music",
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
            async with get_session() as session:
                failed_record = AudioGeneration(
                    video_generation_id=uuid.UUID(video_gen_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    chapter_id=uuid.UUID(chapter_id) if chapter_id else None,
                    audio_type="music",
                    text_content=music_cue["description"],
                    status="failed",
                    error_message=str(e),
                    sequence_order=i + 1,
                    audio_metadata={"chapter_id": chapter_id, "service": "modelslab_v7"},
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
            async with get_session() as session:
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
            async with get_session() as session:
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
            async with get_session() as session:
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
                async with get_session() as session:
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
            async with get_session() as session:
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
            async with get_session() as session:
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
