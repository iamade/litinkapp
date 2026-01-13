from datetime import datetime
from typing import Optional, List
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from app.videos.schemas import VideoGenerationRequest, VideoGenerationResponse
from app.api.services.character import CharacterService
from app.api.services.plot import PlotService
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, update, delete, col, or_, text, func, SQLModel
from sqlalchemy.orm import selectinload
from app.videos.models import (
    Script,
    VideoGeneration,
    AudioGeneration,
    ImageGeneration,
    VideoSegment,
    PipelineStepModel,
)
from app.books.models import (
    Book,
    Chapter,
    LearningContent,
)
from app.plots.models import PlotOverview
from app.auth.models import User
import time

from app.ai.schemas import (
    AIRequest,
    AIResponse,
    QuizGenerationRequest,
    AnalyzeChapterSafetyRequest,
)

from app.core.services.ai import AIService

# from app.core.services.voice import VoiceService
from app.api.services.video import VideoService
from app.core.services.rag import RAGService
from app.core.services.elevenlabs import ElevenLabsService
from app.core.services.embeddings import EmbeddingsService
from app.core.database import get_session, get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.books.models import Chapter, Book
from app.core.auth import get_current_active_user
from app.core.services.pipeline import PipelineManager, PipelineStep
from app.core.services.deepseek_script import DeepSeekScriptService
from app.core.services.openrouter import OpenRouterService, ModelTier
from app.api.services.subscription import SubscriptionManager


def parse_scene_descriptions(analysis_result: str) -> list:
    """Parse scene descriptions from AI analysis result with improved logic"""
    scene_descriptions = []

    # Split by common scene delimiters
    lines = analysis_result.split("\n")

    current_scene = ""
    for line in lines:
        line = line.strip()

        # Look for scene markers (Scene 1:, SCENE 1:, ACT I - SCENE 1, etc.)
        # Match patterns like: "Scene 1:", "SCENE 1:", "ACT I - SCENE 1", "**ACT I - SCENE 1**"
        scene_match = re.match(
            r"^(?:\*\*)?(?:ACT\s+[IVX]+\s*-\s*)?(?:Scene\s+|SCENE\s+|scene\s+)(\d+|[A-Za-z]+)\s*(?:\*\*)?:?\s*(.*)$",
            line,
            re.IGNORECASE,
        )

        if scene_match:
            # Save previous scene if it exists
            if current_scene and len(current_scene) > 20:
                scene_descriptions.append(current_scene[:300])  # Limit length
            # Start new scene with description if available
            scene_desc = scene_match.group(2).strip()
            if scene_desc:
                current_scene = scene_desc
            else:
                current_scene = ""
        elif line and len(line) > 10:
            # Continue building current scene description
            if current_scene:
                current_scene += " " + line
            else:
                current_scene = line

    # Add the last scene
    if current_scene and len(current_scene) > 20:
        scene_descriptions.append(current_scene[:300])

    # If no structured scenes found, fall back to line-based parsing
    if not scene_descriptions:
        for line in lines:
            line = line.strip()
            if line and len(line) > 20:
                scene_descriptions.append(line[:300])

    return scene_descriptions


def extract_characters(
    character_details: str, script_style: str = "cinematic_movie"
) -> list:
    """Extract character names from character analysis with improved logic and script style filtering"""
    characters = []

    # Look for patterns like "Character Name: description" or "Name - role"
    character_patterns = [
        r"^([A-Z][a-zA-Z\s]+?)\s*:\s*.+$",  # Name: description
        r"^([A-Z][a-zA-Z\s]+?)\s*-\s*.+$",  # Name - role
        r"^([A-Z][a-zA-Z\s]+?)\s*\([^)]+\)",  # Name (role)
    ]

    lines = character_details.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in character_patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                char_name = match.group(1).strip()
                # Clean up the name (remove extra spaces, titles, etc.)
                char_name = re.sub(r"\s+", " ", char_name)
                if len(char_name) > 1 and char_name not in characters:
                    characters.append(char_name)
                break

    # Fallback: extract capitalized words if no structured characters found
    if not characters:
        potential_chars = re.findall(r"\b[A-Z][a-zA-Z]+\b", character_details)
        # Filter out common non-character words
        exclude_words = {
            "The",
            "And",
            "But",
            "For",
            "Are",
            "With",
            "This",
            "That",
            "From",
            "They",
            "Will",
            "Have",
            "Been",
            "One",
            "Two",
            "Three",
        }
        characters = [char for char in potential_chars if char not in exclude_words]

    # Filter out invalid character names (pronouns and generic terms)
    invalid_names = {
        "he",
        "she",
        "it",
        "they",
        "him",
        "her",
        "his",
        "hers",
        "its",
        "their",
        "theirs",
        "i",
        "me",
        "my",
        "mine",
        "we",
        "us",
        "our",
        "ours",
        "you",
        "your",
        "yours",
        "cat",
        "dog",
        "baby",
        "child",
        "man",
        "woman",
        "boy",
        "girl",
        "person",
        "uncle",
        "aunt",
        "mother",
        "father",
        "brother",
        "sister",
        "cousin",
    }
    characters = [char for char in characters if char.lower() not in invalid_names]

    # Filter characters based on script style for frontend selection
    if script_style == "cinematic_narration":
        # For narration scripts, exclude narrator-like entities that aren't speaking characters
        narrator_indicators = ["narrator", "voice", "speaker", "announcer"]
        filtered_characters = []
        for char in characters:
            char_lower = char.lower()
            # Exclude if it contains narrator indicators
            if not any(indicator in char_lower for indicator in narrator_indicators):
                filtered_characters.append(char)
        characters = filtered_characters

    # Remove duplicates and limit
    characters = list(set(characters))[:10]  # Increased limit to 10

    return characters


def validate_script_style(script_style: str) -> str:
    """Validate and normalize script style"""
    # Map frontend values to backend values
    style_mapping = {
        "cinematic_movie": "cinematic",  # Character dialogue
        "cinematic_narration": "narration",  # Voice-over narration
        "cinematic": "cinematic",
        "narration": "narration",
        "educational": "educational",
        "marketing": "marketing",
    }

    # Normalize the script style
    normalized = style_mapping.get(script_style)
    if not normalized:
        # Default to cinematic if invalid
        return "cinematic"
    return normalized


def get_available_script_styles() -> dict:
    """Get available script styles with descriptions"""
    return {
        "cinematic": {
            "name": "Cinematic",
            "description": "Professional screenplay format with scene headings, character names, and visual descriptions",
            "best_for": "Video production, storytelling, dramatic content",
        },
        "narration": {
            "name": "Narration",
            "description": "Rich voice-over script with descriptive language and atmospheric elements",
            "best_for": "Audiobooks, documentaries, explanatory videos",
        },
        "educational": {
            "name": "Educational",
            "description": "Clear, structured learning content with step-by-step explanations",
            "best_for": "Tutorials, courses, training materials",
        },
        "marketing": {
            "name": "Marketing",
            "description": "Compelling promotional content with hooks and calls-to-action",
            "best_for": "Advertisements, product demos, promotional videos",
        },
    }


async def enhance_with_plot_context(
    session: AsyncSession,
    user_id: str,
    book_id: str,
    chapter_content: str,
    custom_logline: Optional[str] = None,
) -> dict:
    """Enhanced plot context integration for script generation"""
    try:
        plot_service = PlotService(session)
        plot_overview = await plot_service.get_plot_overview(
            user_id=user_id, book_id=book_id
        )

        if not plot_overview and not custom_logline:
            return {"enhanced_content": None, "plot_info": None}

        # Get characters for this plot if plot exists
        characters = []
        if plot_overview:
            character_service = CharacterService(session)
            characters = await character_service.get_characters_by_plot(
                plot_overview.id, user_id
            )

        # Build comprehensive plot context
        plot_context_parts = []

        # Plot overview section
        plot_context_parts.append("PLOT OVERVIEW:")

        # Use custom logline if provided, otherwise fallback to DB
        if custom_logline:
            plot_context_parts.append(f"Logline: {custom_logline}")
            plot_context_parts.append(
                f"(NOTE: This logline overrides original plot logline)"
            )
        elif plot_overview and plot_overview.logline:
            plot_context_parts.append(f"Logline: {plot_overview.logline}")

        if plot_overview:
            if plot_overview.themes:
                plot_context_parts.append(f"Themes: {', '.join(plot_overview.themes)}")
            if plot_overview.story_type:
                plot_context_parts.append(f"Story Type: {plot_overview.story_type}")
            if plot_overview.genre:
                plot_context_parts.append(f"Genre: {plot_overview.genre}")
            if plot_overview.tone:
                plot_context_parts.append(f"Tone: {plot_overview.tone}")
            if plot_overview.setting:
                plot_context_parts.append(f"Setting: {plot_overview.setting}")
            if plot_overview.target_audience:
                plot_context_parts.append(
                    f"Target Audience: {plot_overview.target_audience}"
                )

        # Characters section
        if characters:
            plot_context_parts.append("\nCHARACTERS:")
            for char in characters[:8]:  # Limit to 8 characters for brevity
                char_info = f"- {char.name}"
                if char.role:
                    char_info += f" ({char.role})"
                if char.personality:
                    char_info += f": {char.personality[:150]}..."
                plot_context_parts.append(char_info)

        # Conflict and stakes
        if plot_overview.conflict_type or plot_overview.stakes:
            plot_context_parts.append("\nSTORY ELEMENTS:")
            if plot_overview.conflict_type:
                plot_context_parts.append(
                    f"Conflict Type: {plot_overview.conflict_type}"
                )
            if plot_overview.stakes:
                plot_context_parts.append(f"Stakes: {plot_overview.stakes}")

        # Combine plot context with chapter content
        plot_context_text = "\n".join(plot_context_parts)
        enhanced_content = f"{plot_context_text}\n\nCHAPTER CONTENT:\n{chapter_content}"

        return {
            "enhanced_content": enhanced_content,
            "plot_info": {
                "plot_id": plot_overview.id,
                "logline": plot_overview.logline,
                "genre": plot_overview.genre,
                "tone": plot_overview.tone,
                "character_count": len(characters) if characters else 0,
            },
        }

    except Exception as e:
        print(f"Error in enhance_with_plot_context: {str(e)}")
        return {"enhanced_content": None, "plot_info": None}


router = APIRouter()


@router.post("/generate-text", response_model=AIResponse)
async def generate_text(
    request: AIRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate text using AI service"""
    ai_service = AIService()
    # Map prompt to content, context to book_type, and use a default difficulty
    content = request.prompt
    book_type = request.context if request.context else "learning"
    difficulty = "medium"
    response = await ai_service.generate_chapter_content(content, book_type, difficulty)
    return AIResponse(text=str(response))


@router.post("/generate-quiz")
async def generate_quiz(
    request: QuizGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate quiz using AI service"""
    ai_service = AIService()
    quiz = await ai_service.generate_quiz(request.chapter_content, request.difficulty)
    return quiz


@router.post("/generate-voice")
async def generate_voice(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate voice using ElevenLabs service"""
    elevenlabs_service = ElevenLabsService()
    # Use generate_enhanced_speech which returns a dict with audio_url
    result = await elevenlabs_service.generate_enhanced_speech(text, voice_id)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    return {"voice_url": result.get("audio_url")}


# New RAG-based video generation endpoints
@router.post("/generate-video-from-chapter")
async def generate_video_from_chapter(
    chapter_id: str,
    video_style: str = "realistic",
    include_context: bool = True,
    include_audio_enhancement: bool = True,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate video from chapter using RAG system with ElevenLabs audio enhancement"""
    try:
        # Verify chapter access
        statement = select(Chapter, Book).join(Book).where(Chapter.id == chapter_id)
        result = await session.exec(statement)
        chapter_book = result.first()

        if not chapter_book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter, book = chapter_book

        # Check access permissions
        if book.status != "published" and str(book.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Generate video using RAG-enhanced service with audio enhancement
        video_service = VideoService(session)
        video_result = await video_service.generate_video_from_chapter(
            chapter_id=chapter_id,
            video_style=video_style,
            include_context=include_context,
            include_audio_enhancement=include_audio_enhancement,
        )

        if not video_result:
            raise HTTPException(status_code=500, detail="Failed to generate video")

        return video_result

    except Exception as e:
        print(f"Error generating video from chapter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-tutorial-video")
async def generate_tutorial_video(
    chapter_id: str,
    video_style: str = "realistic",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate tutorial video from chapter using RAG system"""
    try:
        # Verify chapter access
        statement = select(Chapter, Book).join(Book).where(Chapter.id == chapter_id)
        result = await session.exec(statement)
        chapter_book = result.first()

        if not chapter_book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter, book = chapter_book

        # Check access permissions
        if book.status != "published" and str(book.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Generate tutorial video
        video_service = VideoService(session)
        video_result = await video_service.generate_tutorial_video(
            chapter_id=chapter_id,
            video_style=video_style,
        )

        if not video_result:
            raise HTTPException(
                status_code=500, detail="Failed to generate tutorial video"
            )

        return video_result

    except Exception as e:
        print(f"Error generating tutorial video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-entertainment-video", response_model=VideoGenerationResponse)
async def generate_entertainment_video(
    request: VideoGenerationRequest,
    # request: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate entertainment video using already saved script"""
    try:
        chapter_id = request.chapter_id
        quality_tier = request.quality_tier
        video_style = request.video_style
        # Extract parameters from request body
        # chapter_id = request.get('chapter_id')
        # quality_tier = request.get('quality_tier', 'basic')
        # video_style = request.get('video_style', 'realistic')  # This is for visual styling

        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Step 1: Get the most recent script for this chapter (regardless of style)
        # Step 1: Get the most recent script for this chapter (regardless of style)
        stmt = (
            select(Script)
            .where(Script.chapter_id == chapter_id, Script.user_id == current_user.id)
            .order_by(col(Script.created_at).desc())
            .limit(1)
        )
        result = await session.exec(stmt)
        script_response = result.first()

        if not script_response:
            raise HTTPException(
                status_code=400,
                detail="No script found for this chapter. Please generate script first using 'Generate Script & Scene'.",
            )

        script_data = script_response

        # Step 2: Create video generation record
        print(
            f"[VIDEO GEN DEBUG] Creating video generation with chapter_id: {chapter_id}, script_id: {script_data['id']}, user_id: {current_user.id}"
        )
        video_generation = VideoGeneration(
            chapter_id=chapter_id,
            script_id=script_data.id,
            user_id=current_user.id,
            generation_status="pending",
            quality_tier=quality_tier,
            can_resume=True,
            retry_count=0,
            script_data={
                "script": script_data.script,
                "scene_descriptions": script_data.scene_descriptions,
                "characters": script_data.characters,
                "script_style": script_data.script_style,
                "video_style": video_style,
            },
        )
        session.add(video_generation)
        await session.commit()
        await session.refresh(video_generation)
        video_gen_id = str(video_generation.id)

        try:
            # Step 3: Check for pre-generated audio first
            print(f"🔍 Checking for pre-generated audio for chapter: {chapter_id}")

            # Check for existing audio in audio_generations table
            print(f"[AUDIO QUERY DEBUG] Querying audio_generations with:")
            print(f"  chapter_id: {chapter_id}")
            print(f"  user_id: {current_user.id}")
            print(f"  generation_status: completed (using 'generation_status' column)")

            stmt = select(AudioGeneration).where(
                AudioGeneration.chapter_id == chapter_id,
                AudioGeneration.user_id == current_user.id,
                AudioGeneration.generation_status == "completed",
            )
            result = await session.exec(stmt)
            audio_records = result.all()

            print(f"[AUDIO QUERY DEBUG] Found {len(audio_records)} records")
            if audio_records:
                for idx, record in enumerate(audio_records):
                    print(
                        f"[AUDIO QUERY DEBUG] Record {idx}: status={record.status}, generation_status={record.generation_status}"
                    )
            else:
                print("[AUDIO QUERY DEBUG] No records found.")

            existing_audio = []
            audio_by_type = {
                "narrator": [],
                "characters": [],
                "sound_effects": [],
                "background_music": [],
            }

            if audio_records:
                for audio_record in audio_records:
                    audio_type = audio_record.audio_type or "narrator"
                    # Map database fields to expected format
                    audio_data = {
                        "id": str(audio_record.id),
                        "url": audio_record.audio_url,
                        "audio_url": audio_record.audio_url,
                        "duration": audio_record.duration or 0,
                        "file_name": audio_record.text_content or "",
                        "scene_number": audio_record.sequence_order or 0,
                        "character_name": (
                            audio_record.metadata.get("character_name")
                            if audio_record.metadata
                            else None
                        ),
                        "volume": 1.0,
                    }

                    # Categorize by type
                    if audio_type == "narrator":
                        audio_by_type["narrator"].append(audio_data)
                    elif audio_type == "character":
                        audio_by_type["characters"].append(audio_data)
                    elif audio_type in ["sfx", "sound_effect"]:
                        audio_by_type["sound_effects"].append(audio_data)
                    elif audio_type == "music":
                        audio_by_type["background_music"].append(audio_data)

                    existing_audio.append(audio_data)

            print(f"📊 Found {len(existing_audio)} pre-generated audio files")

            if existing_audio:
                # Use pre-generated audio - skip audio generation
                print(f"✅ Using pre-generated audio, skipping audio generation step")

                # Organize audio by type for storage
                audio_by_type = {
                    "narrator": [],
                    "characters": [],
                    "sound_effects": [],
                    "background_music": [],
                }

                for audio_file in existing_audio:
                    audio_type = audio_file.get("audio_type", "narrator")
                    audio_by_type[audio_type].append(
                        {
                            "id": audio_file["id"],
                            "url": audio_file["audio_url"],
                            "duration": audio_file.get("duration", 0),
                            "name": audio_file.get("file_name", ""),
                            "scene_number": audio_file.get("scene_number", 0),
                            "character": audio_file.get("character_name"),
                            "volume": audio_file.get("volume", 1.0),
                        }
                    )

                # Check for pre-generated images from image_generations table
                existing_images = []
                image_by_type = {"character_images": [], "scene_images": []}

                # Query image_generations table for images associated with this chapter
                stmt = select(ImageGeneration).where(
                    ImageGeneration.user_id == current_user.id,
                    ImageGeneration.status == "completed",
                )
                result = await session.exec(stmt)
                image_records = result.all()

                if image_records:
                    for img in image_records:
                        metadata = img.metadata or {}
                        # Check if image is associated with this chapter
                        if metadata.get("chapter_id") == chapter_id:
                            image_type = metadata.get("image_type", "scene")
                            image_data = {
                                "id": str(img.id),
                                "url": img.image_url,
                                "image_url": img.image_url,
                                "prompt": img.image_prompt or "",
                                "created_at": (
                                    img.created_at.isoformat()
                                    if img.created_at
                                    else None
                                ),
                            }

                            if image_type == "character":
                                image_data["character_name"] = metadata.get(
                                    "character_name", ""
                                )
                                image_by_type["character_images"].append(image_data)
                            elif image_type == "scene":
                                image_data["scene_number"] = metadata.get(
                                    "scene_number", 0
                                )
                                image_by_type["scene_images"].append(image_data)

                            existing_images.append(image_data)

                print(f"📊 Found {len(existing_images)} pre-generated images")

                # Store pre-generated audio and images in video generation record
                stmt = select(VideoGeneration).where(VideoGeneration.id == video_gen_id)
                result = await session.exec(stmt)
                video_gen = result.first()
                if video_gen:
                    video_gen.audio_files = audio_by_type
                    video_gen.image_data = {
                        "images": image_by_type,
                        "statistics": {
                            "total_images": len(existing_images),
                            "character_images": len(image_by_type["character_images"]),
                            "scene_images": len(image_by_type["scene_images"]),
                        },
                    }
                    video_gen.generation_status = "images_completed"
                    video_gen.task_metadata = {
                        "audio_source": "pre_generated",
                        "image_source": "pre_generated",
                        "audio_files_count": len(existing_audio),
                        "image_files_count": len(existing_images),
                        "started_at": datetime.now().isoformat(),
                    }
                    session.add(video_gen)
                    await session.commit()

                # ✅ FIXED: Queue video generation task since we have pre-generated assets
                print(f"🎬 Queuing video generation task for video: {video_gen_id}")
                from app.tasks.video_tasks import generate_all_videos_for_generation

                task = generate_all_videos_for_generation.delay(video_gen_id)
                print(f"✅ Video generation task queued successfully: {task.id}")

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Can't find pre-generated audio and stop the video generation",
                )
                # print(f"🎵 No pre-generated audio found, starting audio generation for video: {video_gen_id}")

                # from app.tasks.audio_tasks import generate_all_audio_for_video
                # task = generate_all_audio_for_video.delay(video_gen_id)
                # print(f"✅ Audio task queued successfully: {task.id}")

                # # Store task ID and update status in database
                # supabase_client.table('video_generations').update({
                #     'audio_task_id': task.id,
                #     'generation_status': 'generating_audio',
                #     'task_metadata': {
                #         'audio_source': 'generated',
                #         'audio_task_id': task.id,
                #         'audio_task_state': task.state,
                #         'started_at': datetime.now().isoformat()
                #     }
                # }).eq('id', video_gen_id).execute()

        except Exception as e:
            print(f"❌ Failed to queue audio task: {e}")

            stmt = select(VideoGeneration).where(VideoGeneration.id == video_gen_id)
            result = await session.exec(stmt)
            video_gen = result.first()
            if video_gen:
                video_gen.generation_status = "failed"
                video_gen.error_message = f"Failed to start audio generation: {str(e)}"
                session.add(video_gen)
                await session.commit()

            raise e

        # Handle response based on whether a task was queued
        if task:
            audio_task_id = task.id
            task_status = task.state
            status = "queued"
            message = "Video generation started using saved script"
        else:
            audio_task_id = None
            task_status = "completed"
            status = "ready"
            message = "Video generation ready using pre-generated assets"

        return VideoGenerationResponse(
            video_generation_id=video_gen_id,
            script_id=script_data["id"],
            status=status,
            audio_task_id=audio_task_id,
            task_status=task_status,
            message=message,
            script_info={
                "script_style": script_data["script_style"],
                "video_style": video_style,  # ✅ Now this works
                "scenes": len(script_data.get("scene_descriptions", [])),
                "characters": len(script_data.get("characters", [])),
                "created_at": script_data["created_at"],
            },
        )

        # return VideoGenerationResponse(
        #     video_generation_id=video_gen_id,
        #     script_id=script_data['id'],
        #     status="queued",
        #     audio_task_id=task.id,
        #     task_status=task.state,
        #     message="Video generation started using saved script",
        #     script_info={
        #         "script_style": script_data['script_style'],
        #         "video_style": request.get('video_style', 'realistic'),
        #         "scenes": len(script_data.get('scene_descriptions', [])),
        #         "characters": len(script_data.get('characters', [])),
        #         "created_at": script_data['created_at']
        #     }
        # )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video-generation-status/{video_gen_id}")
async def get_video_generation_status(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get video generation status with detailed progress"""
    try:
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        data = result.first()

        if not data:
            raise HTTPException(status_code=404, detail="Video generation not found")

        status = data.generation_status

        task_metadata = data.task_metadata or {}
        audio_task_id = task_metadata.get("audio_task_id") or data.get("audio_task_id")

        if audio_task_id and status in ["generating_audio", "pending"]:
            try:
                from app.tasks.celery_app import celery_app

                task_result = celery_app.AsyncResult(audio_task_id)

                if task_result.state == "SUCCESS":
                    # Task completed but DB not updated yet
                    status = "audio_completed"
                elif task_result.state == "FAILURE":
                    status = "failed"
                    data["error_message"] = str(task_result.result)
                elif task_result.state == "PENDING":
                    status = "generating_audio"

                # Add task info to response
                data["task_info"] = {
                    "task_id": audio_task_id,
                    "task_state": task_result.state,
                    "task_result": (
                        str(task_result.result) if task_result.result else None
                    ),
                }
            except Exception as e:
                print(f"Error checking task status: {e}")

        # Base response
        result = {
            "status": status,
            "generation_status": status,
            "quality_tier": data["quality_tier"],
            "video_url": data.get("video_url"),
            "created_at": data["created_at"],
            "script_id": data.get("script_id"),
            "error_message": data.get("error_message"),
        }

        # Add audio information if available
        if data.get("audio_files"):
            audio_data = data["audio_files"]
            result["audio_progress"] = {
                "narrator_files": len(audio_data.get("narrator", [])),
                "character_files": len(audio_data.get("characters", [])),
                "sound_effects": len(audio_data.get("sound_effects", [])),
                "background_music": len(audio_data.get("background_music", [])),
            }

        # Add task info if available
        if "task_info" in data:
            result["task_info"] = data["task_info"]

        # Add image information if available
        if data.get("image_data"):
            image_data = data["image_data"]
            result["image_progress"] = image_data.get("statistics", {})

            # Include character images for frontend display
            if status in ["images_completed", "generating_video", "completed"]:
                character_images = image_data.get("character_images", [])
                result["character_images"] = [
                    img for img in character_images if img is not None
                ]

        #  Add video information if available
        if data.get("video_data"):
            video_data = data["video_data"]
            result["video_progress"] = video_data.get("statistics", {})

            # Include scene videos for frontend display
            if status in ["video_completed", "merging_audio", "completed"]:
                scene_videos = video_data.get("scene_videos", [])
                result["scene_videos"] = [
                    video for video in scene_videos if video is not None
                ]

        # Add merge information if available
        if data.get("merge_data"):
            merge_data = data["merge_data"]
            result["merge_progress"] = merge_data.get("merge_statistics", {})

            # Include final video information if completed
            if status == "completed":
                result["final_video_ready"] = True
                result["merge_details"] = {
                    "processing_time": merge_data.get("merge_statistics", {}).get(
                        "processing_time", 0
                    ),
                    "file_size_mb": merge_data.get("merge_statistics", {}).get(
                        "file_size_mb", 0
                    ),
                    "scenes_merged": merge_data.get("merge_statistics", {}).get(
                        "total_scenes_merged", 0
                    ),
                    "audio_tracks_mixed": merge_data.get("merge_statistics", {}).get(
                        "audio_tracks_mixed", 0
                    ),
                }

        # ✅ NEW: Add lip sync information if available
        if data.get("lipsync_data"):
            lipsync_data = data["lipsync_data"]
            result["lipsync_progress"] = lipsync_data.get("statistics", {})

            # Include lip sync details if completed
            if status in ["lipsync_completed", "completed"]:
                result["lipsync_completed"] = True
                result["lipsync_details"] = {
                    "characters_lip_synced": lipsync_data.get("statistics", {}).get(
                        "characters_lip_synced", 0
                    ),
                    "scenes_processed": lipsync_data.get("statistics", {}).get(
                        "total_scenes_processed", 0
                    ),
                    "processing_method": lipsync_data.get("statistics", {}).get(
                        "processing_method", "unknown"
                    ),
                }

                # Include lip synced scenes
                lip_synced_scenes = lipsync_data.get("lip_synced_scenes", [])
                result["lip_synced_scenes"] = [
                    scene for scene in lip_synced_scenes if scene is not None
                ]

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chapter-video-generations/{chapter_id}")
async def get_chapter_video_generations(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get all video generations for a chapter"""
    try:
        print(f"🔍 DEBUG: Getting video generations for chapter: {chapter_id}")
        print(f"🔍 DEBUG: User ID: {getattr(current_user, 'id', 'Unknown')}")

        # First check if chapter exists
        stmt = select(Chapter).where(Chapter.id == chapter_id)
        result = await session.exec(stmt)
        chapter_exists = result.first()

        print(f"🔍 DEBUG: Chapter found: {chapter_exists}")

        stmt = (
            select(VideoGeneration)
            .where(
                VideoGeneration.chapter_id == chapter_id,
                VideoGeneration.user_id == current_user.id,
            )
            .order_by(col(VideoGeneration.created_at).desc())
        )
        result = await session.exec(stmt)
        response_data = [g.model_dump() for g in result.all()]

        print(f"🔍 DEBUG: Video generations found: {len(response_data)}")

        generations = []
        for gen in response_data:
            # Add pipeline status for each generation
            try:
                pipeline_manager = PipelineManager()
                pipeline_status = pipeline_manager.get_pipeline_status(gen["id"])
                gen["pipeline_status"] = pipeline_status

                # Add retry capability flag
                gen["can_resume"] = gen.get("generation_status") in [
                    "failed",
                    "audio_completed",
                    "images_completed",
                    "video_completed",
                ] or (pipeline_status and pipeline_status.get("can_resume", False))

            except Exception as e:
                print(f"Error getting pipeline status for {gen['id']}: {e}")
                gen["pipeline_status"] = None
                gen["can_resume"] = gen.get("generation_status") == "failed"

            generations.append(gen)

        result = {
            "chapter_id": chapter_id,
            "generations": generations,
            "total": len(generations),
        }

        print(f"🔍 DEBUG: Returning result with {len(generations)} generations")
        return result

    except Exception as e:
        print(f"❌ ERROR in get_chapter_video_generations: {e}")
        import traceback

        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


# Add this new endpoint after get_character_images function (around line 310):


@router.get("/scene-videos/{video_gen_id}")
async def get_scene_videos(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get scene videos for a video generation"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        # Get scene videos
        stmt = (
            select(VideoSegment)
            .where(
                VideoSegment.video_generation_id == video_gen_id,
                VideoSegment.status == "completed",
            )
            .order_by(VideoSegment.scene_id)
        )
        result = await session.exec(stmt)
        videos_data = [v.model_dump() for v in result.all()]

        scene_videos = []
        total_duration = 0.0

        for video in videos_response.data or []:
            # Calculate resolution from width and height
            width = video.get("width", 512)
            height = video.get("height", 288)
            resolution = f"{width}x{height}"

            scene_videos.append(
                {
                    "id": video["id"],
                    "scene_id": video["scene_id"],
                    "scene_description": video["scene_description"],
                    "video_url": video["video_url"],
                    "duration": video["duration_seconds"],
                    "resolution": video["resolution"],
                    "width": width,  # ✅ Include individual dimensions too
                    "height": height,  # ✅ Include individual dimensions too
                    "fps": video["fps"],
                    "generation_method": video["generation_method"],
                    "created_at": video["created_at"],
                }
            )
            total_duration += video["duration_seconds"]

        return {
            "video_generation_id": video_gen_id,
            "scene_videos": scene_videos,
            "total_scenes": len(scene_videos),
            "total_duration": total_duration,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add this new endpoint after get_scene_videos function (around line 380):


@router.get("/final-video/{video_gen_id}")
async def get_final_video(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get final merged video for a video generation"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        data = video_response

        if data.generation_status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Video generation not completed. Current status: {data.generation_status}",
            )

        final_video_url = data.video_url
        merge_data = data.get("merge_data", {})

        if not final_video_url:
            raise HTTPException(status_code=404, detail="Final video not found")

        return {
            "video_generation_id": video_gen_id,
            "final_video_url": final_video_url,
            "status": "completed",
            "merge_statistics": merge_data.get("merge_statistics", {}),
            "quality_versions": merge_data.get("quality_versions", []),
            "processing_details": merge_data.get("processing_details", {}),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/merge-status/{video_gen_id}")
async def get_merge_status(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get detailed merge status and progress"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        data = video_response
        status = data.generation_status
        merge_data = data.merge_data or {}

        result = {
            "video_generation_id": video_gen_id,
            "merge_status": status,
            "is_merging": status == "merging_audio",
            "is_completed": status == "completed",
            "final_video_url": data.video_url,
            "error_message": data.error_message,
        }

        # Add merge statistics if available
        if merge_data:
            result["merge_statistics"] = merge_data.get("merge_statistics", {})
            result["processing_details"] = merge_data.get("processing_details", {})

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add these new endpoints after get_merge_status function (around line 450):


@router.get("/lip-sync-status/{video_gen_id}")
async def get_lip_sync_status(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get detailed lip sync status and progress"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        data = video_response
        status = data.generation_status
        lipsync_data = data.lipsync_data or {}

        result = {
            "video_generation_id": video_gen_id,
            "lipsync_status": status,
            "is_applying_lipsync": status == "applying_lipsync",
            "is_lipsync_completed": status in ["lipsync_completed", "completed"],
            "error_message": data.get("error_message"),
        }

        # Add lip sync statistics if available
        if lipsync_data:
            result["lipsync_statistics"] = lipsync_data.get("statistics", {})
            result["lip_synced_scenes"] = lipsync_data.get("lip_synced_scenes", [])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lip-synced-videos/{video_gen_id}")
async def get_lip_synced_videos(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get lip synced scene videos for a video generation"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        # Get lip synced video segments
        stmt = (
            select(VideoSegment)
            .where(
                VideoSegment.video_generation_id == video_gen_id,
                VideoSegment.generation_method == "lip_sync",
                VideoSegment.status == "completed",
            )
            .order_by(VideoSegment.scene_id)
        )
        result = await session.exec(stmt)
        lipsync_response = result.all()

        lip_synced_videos = []
        total_duration = 0.0

        for video in lipsync_response.data or []:
            metadata = video.get("metadata", {})
            lip_synced_videos.append(
                {
                    "id": video["id"],
                    "scene_id": video["scene_id"],
                    "original_video_url": metadata.get("original_video_url"),
                    "lipsync_video_url": video["video_url"],
                    "duration": video["duration_seconds"],
                    "characters_processed": metadata.get("characters_processed", []),
                    "faces_detected": metadata.get("faces_detected", 0),
                    "processing_model": video["processing_model"],
                    "created_at": video["created_at"],
                }
            )
            total_duration += video["duration_seconds"]

        return {
            "video_generation_id": video_gen_id,
            "lip_synced_videos": lip_synced_videos,
            "total_scenes": len(lip_synced_videos),
            "total_duration": total_duration,
            "characters_with_lipsync": len(
                set(
                    [
                        char
                        for video in lip_synced_videos
                        for char in video.get("characters_processed", [])
                    ]
                )
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-lip-sync/{video_gen_id}")
async def trigger_lip_sync_manually(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Manually trigger lip sync processing for a video generation"""
    try:
        # Verify access and status
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        data = video_response
        status = data.generation_status

        # Check if lip sync can be applied
        if status not in ["video_completed", "completed", "lipsync_failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot apply lip sync. Current status: {status}. Video generation must be completed first.",
            )

        # Check if character dialogue exists
        audio_files = data.get("audio_files", {})
        character_audio = audio_files.get("characters", [])

        if not character_audio:
            raise HTTPException(
                status_code=400,
                detail="No character dialogue found. Lip sync requires character audio.",
            )

        # Trigger lip sync task
        from app.tasks.lipsync_tasks import apply_lip_sync_to_generation

        task = apply_lip_sync_to_generation.delay(video_gen_id)

        return {
            "message": "Lip sync processing started",
            "task_id": task.id,
            "video_generation_id": video_gen_id,
            "character_dialogues": len(character_audio),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/script-styles")
async def get_script_styles():
    """Get available script styles with descriptions"""
    return {"styles": get_available_script_styles(), "default": "cinematic"}


@router.get("/scripts/{chapter_id}")
async def list_chapter_scripts(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List all scripts for a chapter by current user"""
    try:
        print(
            f"[DEBUG] list_chapter_scripts called for chapter_id: {chapter_id}, user_id: {current_user.id}"
        )

        # Check if chapter_id is an Artifact and resolve to real Chapter ID if possible
        search_ids = [chapter_id]
        try:
            from app.projects.models import Artifact, Project

            # Check if it's an artifact
            stmt = select(Artifact).where(Artifact.id == chapter_id)
            artifact = (await session.exec(stmt)).first()

            if artifact:
                # Get project to check for book link
                project = (
                    await session.exec(
                        select(Project).where(Project.id == artifact.project_id)
                    )
                ).first()
                if project and project.book_id:
                    # Try to find corresponding Chapter
                    content_data = artifact.content or {}
                    chapter_num = content_data.get("chapter_number")
                    if chapter_num:
                        chap_stmt = select(Chapter).where(
                            Chapter.book_id == project.book_id,
                            Chapter.chapter_number == chapter_num,
                        )
                        real_chapter = (await session.exec(chap_stmt)).first()
                        if real_chapter:
                            print(
                                f"[ListScripts] Resolved Artifact {chapter_id} to Chapter {real_chapter.id}"
                            )
                            search_ids.append(str(real_chapter.id))
        except Exception as resolve_err:
            print(
                f"[ListScripts] Warning: Error resolving artifact to chapter: {resolve_err}"
            )

        # Convert IDs to UUIDs for DB query
        search_uuids = []
        for sid in search_ids:
            try:
                search_uuids.append(uuid.UUID(str(sid)))
            except ValueError:
                pass

        stmt = (
            select(Script)
            .where(
                col(Script.chapter_id).in_(search_uuids),
                Script.user_id == current_user.id,
            )
            .order_by(col(Script.created_at).desc())
        )
        result = await session.exec(stmt)
        scripts_data = [s.model_dump() for s in result.all()]

        print(f"[DEBUG] list_chapter_scripts - raw scripts data: {scripts_data}")
        for script in scripts_data:
            print(
                f"[DEBUG] list_chapter_scripts - script {script.get('id')}: script_story_type = {script.get('script_story_type')}"
            )

        return {"chapter_id": chapter_id, "scripts": scripts_data}

    except Exception as e:
        print(f"Error listing scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/script/{script_id}")
async def get_script_details(
    script_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get detailed script information"""
    try:
        stmt = select(Script).where(
            Script.id == script_id, Script.user_id == current_user.id
        )
        result = await session.exec(stmt)
        script_data = result.first()

        if not script_data:
            raise HTTPException(status_code=404, detail="Script not found")

        return script_data

    except Exception as e:
        print(f"Error getting script details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Script Evaluation Endpoint ---
@router.post("/evaluate-script/{script_id}")
async def evaluate_script(
    script_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Evaluate a script using DeepSeekScriptService (LLM) for coherence, storytelling, character consistency, video suitability.
    Returns scores and feedback.
    """
    try:
        # Fetch script and chapter context
        stmt = select(Script).where(
            Script.id == script_id, Script.user_id == current_user.id
        )
        result = await session.exec(stmt)
        script_record = result.first()
        if not script_record:
            raise HTTPException(status_code=404, detail="Script not found")
        script = script_record.script
        chapter_id = script_record.chapter_id
        plot_context = None
        if chapter_id:
            stmt = select(Chapter).where(Chapter.id == chapter_id)
            result = await session.exec(stmt)
            chapter = result.first()
            plot_context = chapter.content if chapter else None

        # Evaluate using DeepSeekScriptService
        from app.core.services.deepseek_script import DeepSeekScriptService

        deepseek = DeepSeekScriptService()
        result = await deepseek.evaluate_script(script, plot_context=plot_context)

        # Optionally update script status and store evaluation
        if result.get("status") == "success" and result.get("scores"):
            stmt = select(Script).where(Script.id == script_id)
            exec_result = await session.exec(stmt)
            script_record = exec_result.first()
            if script_record:
                script_record.evaluation = result["scores"]
                script_record.status = "evaluated"
                session.add(script_record)
                await session.commit()

        return result
    except Exception as e:
        print(f"Error evaluating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Script Status Management Endpoints ---
@router.post("/script-status/{script_id}")
async def update_script_status(
    script_id: str,
    status: str = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update the status of a script (draft, evaluated, approved, rejected, active).
    """
    try:
        allowed_statuses = [
            "draft",
            "evaluated",
            "approved",
            "rejected",
            "active",
            "ready",
        ]
        if status not in allowed_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        stmt = select(Script).where(Script.id == script_id)
        result = await session.exec(stmt)
        script_record = result.first()

        if not script_record or script_record.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to update this script"
            )

        script_record.status = status
        session.add(script_record)
        await session.commit()
        return {"message": "Status updated", "script_id": script_id, "status": status}
    except Exception as e:
        print(f"Error updating script status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate-script/{script_id}")
async def activate_script(
    script_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Set a script as active for its chapter (deactivate others).
    """
    try:
        stmt = select(Script).where(Script.id == script_id)
        result = await session.exec(stmt)
        script_record = result.first()

        if not script_record or script_record.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to activate this script"
            )

        chapter_id = script_record.chapter_id

        # Deactivate other scripts for this chapter/user
        stmt = select(Script).where(
            Script.chapter_id == chapter_id,
            Script.user_id == current_user.id,
            Script.id != script_id,
        )
        result = await session.exec(stmt)
        other_scripts = result.all()
        for s in other_scripts:
            s.status = "ready"
            session.add(s)

        # Activate selected script
        script_record.status = "active"
        session.add(script_record)
        await session.commit()
        return {"message": "Script activated", "script_id": script_id}
    except Exception as e:
        print(f"Error activating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate-script/{script_id}")
async def deactivate_script(
    script_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Deactivate a script (set status to ready).
    """
    try:
        stmt = select(Script).where(Script.id == script_id)
        result = await session.exec(stmt)
        script_record = result.first()

        if not script_record or script_record.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to deactivate this script"
            )

        script_record.status = "ready"
        session.add(script_record)
        await session.commit()
        return {"message": "Script deactivated", "script_id": script_id}
    except Exception as e:
        print(f"Error deactivating script: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# get_character_images endpoint:


@router.get("/character-images/{video_gen_id}")
async def get_character_images(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get character images for a video generation"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        # Get character images
        stmt = select(ImageGeneration).where(
            ImageGeneration.video_generation_id == video_gen_id,
            ImageGeneration.image_type == "character",
            ImageGeneration.status == "completed",
        )
        result = await session.exec(stmt)
        images_data = [i.model_dump() for i in result.all()]

        character_images = []
        for img in images_data or []:
            character_images.append(
                {
                    "id": img["id"],
                    "character_name": img["character_name"],
                    "image_url": img["image_url"],
                    "prompt": img["image_prompt"],
                    "created_at": img["created_at"],
                }
            )

        return {
            "video_generation_id": video_gen_id,
            "character_images": character_images,
            "total_characters": len(character_images),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-video-avatar")
async def generate_video_avatar(
    chapter_id: str,
    avatar_style: str = "realistic",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate video avatar from chapter content"""
    try:
        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Generate video avatar
        video_service = VideoService(session)
        avatar_result = await video_service.generate_story_scene(
            scene_description=chapter_data.title,
            dialogue=chapter_data.content[:500],
            avatar_style=avatar_style,
        )

        if not avatar_result:
            raise HTTPException(
                status_code=500, detail="Failed to generate video avatar"
            )

        return avatar_result

    except Exception as e:
        print(f"Error generating video avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance-entertainment-content")
async def enhance_entertainment_content(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Enhance entertainment content using PlotDrive service"""
    try:
        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Enhance content using RAG service with PlotDrive
        rag_service = RAGService(session)
        chapter_context = await rag_service.get_chapter_with_context(
            chapter_id, include_adjacent=True
        )

        if not chapter_context:
            raise HTTPException(
                status_code=404, detail="Could not retrieve chapter context"
            )

        enhancement = await rag_service.enhance_entertainment_content(chapter_context)

        return {"chapter_id": chapter_id, "enhancement": enhancement}

    except Exception as e:
        print(f"Error enhancing entertainment content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-screenplay")
async def generate_screenplay(
    chapter_id: str,
    style: str = "realistic",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate screenplay using RAG service with PlotDrive"""
    try:
        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Generate screenplay using RAG service with PlotDrive
        rag_service = RAGService(session)
        chapter_context = await rag_service.get_chapter_with_context(
            chapter_id, include_adjacent=True
        )

        if not chapter_context:
            raise HTTPException(
                status_code=404, detail="Could not retrieve chapter context"
            )

        screenplay = await rag_service._generate_entertainment_script(
            chapter_context, style
        )

        return {"chapter_id": chapter_id, "screenplay": screenplay, "style": style}

    except Exception as e:
        print(f"Error generating screenplay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# New embeddings management endpoints
@router.post("/create-chapter-embeddings")
async def create_chapter_embeddings(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create vector embeddings for a chapter"""
    try:
        # Verify chapter access
        # Verify chapter access
        stmt = select(Chapter, Book).join(Book).where(Chapter.id == chapter_id)
        result = await session.exec(stmt)
        chapter_book = result.first()

        if not chapter_book:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter_data, book_data = chapter_book

        # Check access permissions
        if str(book_data.user_id) != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Create embeddings
        embeddings_service = EmbeddingsService(session)
        success = await embeddings_service.create_chapter_embeddings(
            chapter_id=chapter_id, content=chapter_data.content
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to create embeddings")

        return {"message": "Embeddings created successfully", "chapter_id": chapter_id}

    except Exception as e:
        print(f"Error creating chapter embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-book-embeddings")
async def create_book_embeddings(
    book_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Create vector embeddings for a book"""
    try:
        # Verify book access
        # Verify book access
        stmt = select(Book).where(Book.id == book_id)
        result = await session.exec(stmt)
        book_data = result.first()

        if not book_data:
            raise HTTPException(status_code=404, detail="Book not found")

        # Check access permissions
        if str(book_data.user_id) != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this book"
            )

        # Create embeddings
        embeddings_service = EmbeddingsService(session)
        success = await embeddings_service.create_book_embeddings(
            book_id=book_id,
            title=book_data["title"],
            description=book_data.get("description"),
            content=book_data.get("content"),
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to create embeddings")

        return {"message": "Book embeddings created successfully", "book_id": book_id}

    except Exception as e:
        print(f"Error creating book embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-similar-content")
async def search_similar_content(
    query: str,
    book_id: str = None,
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Search for similar content using vector embeddings"""
    try:
        embeddings_service = EmbeddingsService(session)
        results = await embeddings_service.search_similar_chapters(
            query=query, book_id=book_id, limit=limit
        )

        return {"query": query, "results": results, "total_results": len(results)}

    except Exception as e:
        print(f"Error searching similar content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-similar-books")
async def search_similar_books(
    query: str,
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Search for similar books using vector embeddings"""
    try:
        embeddings_service = EmbeddingsService(session)
        results = await embeddings_service.search_similar_books(
            query=query, limit=limit
        )

        return {"query": query, "results": results, "total_results": len(results)}

    except Exception as e:
        print(f"Error searching similar books: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ElevenLabs enhanced endpoints
@router.post("/generate-enhanced-speech")
async def generate_enhanced_speech(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    emotion: str = "neutral",
    speed: float = 1.0,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate enhanced speech with emotion and speed control"""
    try:
        elevenlabs_service = ElevenLabsService()
        result = await elevenlabs_service.generate_enhanced_speech(
            text=text,
            voice_id=voice_id,
            user_id=current_user.id,
            emotion=emotion,
            speed=speed,
        )

        return result

    except Exception as e:
        print(f"Error generating enhanced speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-sound-effects")
async def generate_sound_effects(
    effect_type: str,
    duration: float = 2.0,
    intensity: str = "medium",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate sound effects"""
    try:
        elevenlabs_service = ElevenLabsService()
        audio_url = await elevenlabs_service.generate_sound_effect(
            effect_type=effect_type,
            duration=duration,
            intensity=intensity,
            user_id=current_user.id,
        )

        return {"audio_url": audio_url}

    except Exception as e:
        print(f"Error generating sound effects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-audio-for-script")
async def generate_audio_for_script(
    request: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate all audio assets (dialogue, narration, music, sfx) for a script.
    Creates a VideoGeneration container and triggers the audio task.
    """
    try:
        chapter_id = request.get("chapter_id")
        script_id = request.get("script_id")

        if not chapter_id or not script_id:
            raise HTTPException(
                status_code=400, detail="chapter_id and script_id are required"
            )

        print(
            f"🎵 Initiating audio generation for Script: {script_id} (Chapter: {chapter_id})"
        )

        # Verify ownership/access
        # (Simplified for brevity, assumes standard checks)

        # 1. Ensure Script exists and get data
        stmt = select(Script).where(Script.id == uuid.UUID(script_id))
        result = await session.exec(stmt)
        script_data = result.first()

        if not script_data:
            raise HTTPException(status_code=404, detail="Script not found")

        # 2. Create VideoGeneration container
        # We reuse VideoGeneration as the container for all assets
        video_gen = VideoGeneration(
            chapter_id=uuid.UUID(chapter_id),
            user_id=current_user.id,
            script_id=uuid.UUID(script_id),
            script_data={
                "script": script_data.script,
                "characters": script_data.characters,
                "scene_descriptions": script_data.scene_descriptions,
                "style": script_data.script_style,
            },
            generation_status="generating_audio",
            quality_tier="standard",  # Default, will be updated by task
            task_meta={"pipeline_state": {"current_stage": "audio"}},
        )
        session.add(video_gen)
        await session.commit()
        await session.refresh(video_gen)

        video_gen_id = str(video_gen.id)
        print(f"✅ Created VideoGeneration container: {video_gen_id}")

        # 3. Trigger Celery Task
        from app.tasks.audio_tasks import generate_all_audio_for_video

        task = generate_all_audio_for_video.delay(video_gen_id)

        return {
            "status": "processing",
            "message": "Audio generation started",
            "video_generation_id": video_gen_id,
            "task_id": task.id,
        }

    except Exception as e:
        print(f"❌ Error initiating audio generation: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-audio-narration")
async def generate_audio_narration(
    request: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate audio narration for learning content using RAG embeddings and ElevenLabs"""
    try:
        chapter_id = request.get("chapter_id")
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Check if this is a learning book
        if book_data.book_type != "learning":
            raise HTTPException(
                status_code=400,
                detail="Audio narration is only available for learning books",
            )

        # Generate tutorial script using RAG and AI
        ai_service = AIService()

        # Create tutorial prompt based on chapter content
        tutorial_prompt = f"""
        Create an engaging audio tutorial script for the following learning content:
        
        Chapter Title: {chapter_data.title}
        Chapter Content: {chapter_data.content[:1000]}...
        
        Requirements:
        1. Write a clear, educational tutorial script for audio narration
        2. Use a conversational, teaching tone suitable for audio learning
        3. Break down complex concepts into digestible parts
        4. Include examples and explanations
        5. Keep it engaging and informative
        6. Target duration: 3-5 minutes when narrated
        7. Format as a simple speaking script (no character names, no scene descriptions)
        8. Focus on educational content delivery
        9. Use natural speech patterns and transitions
        
        Write the script as if a teacher is directly speaking to students about this topic.
        Do NOT include character names, scene descriptions, or cinematic elements.
        Format the script for ElevenLabs audio narration.
        """

        # Generate tutorial script using AI
        tutorial_script = await ai_service.generate_tutorial_script(tutorial_prompt)

        if not tutorial_script:
            raise HTTPException(
                status_code=500, detail="Failed to generate tutorial script"
            )

        # Generate audio using ElevenLabs
        elevenlabs_service = ElevenLabsService()

        audio_result = await elevenlabs_service.create_audio_narration(
            text=tutorial_script,
            narrator_style="professional",
            user_id=current_user.id,
        )

        if not audio_result:
            raise HTTPException(
                status_code=500, detail="Failed to generate audio narration"
            )

        # Store the result in database (optional)
        audio_record = LearningContent(
            chapter_id=chapter_id,
            book_id=book_data.id,
            user_id=current_user.id,
            content_type="audio_narration",
            content_url=audio_result,
            script=tutorial_script,
            duration=180,  # Default 3 minutes
            status="ready",
        )
        session.add(audio_record)
        await session.commit()

        return {
            "id": f"audio_{int(time.time())}",
            "audio_url": audio_result,
            "duration": 180,
            "status": "ready",
        }

    except Exception as e:
        print(f"Error generating audio narration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-realistic-video")
async def generate_realistic_video(
    request: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate realistic video tutorial using RAG embeddings and Tavus with enhanced error handling"""
    try:
        print(f"🎬 Starting realistic video generation for user: {current_user.id}")

        chapter_id = request.get("chapter_id")
        if not chapter_id:
            print("❌ Missing chapter_id in request")
            raise HTTPException(status_code=400, detail="chapter_id is required")

        print(f"📖 Processing chapter: {chapter_id}")

        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            print(f"❌ Chapter not found: {chapter_id}")
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        print(f"📚 Book: {book_data.title} (Type: {book_data.book_type})")

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            print(f"❌ Access denied for chapter: {chapter_id}")
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )

        # Check if this is a learning book
        if book_data.book_type != "learning":
            print(
                f"❌ Book type '{book_data.book_type}' is not supported for realistic video"
            )
            raise HTTPException(
                status_code=400,
                detail="Realistic video is only available for learning books",
            )

        # Generate tutorial script using RAG and AI
        ai_service = AIService()

        # Create tutorial prompt for video
        tutorial_prompt = f"""
        Create an engaging tutorial script for the following learning content:
        
        Chapter Title: {chapter_data.title}
        Chapter Content: {chapter_data.content[:1000]}...
        
        Requirements:
        1. Write a clear, educational tutorial script for a teacher/tutor to present
        2. Use a conversational, teaching tone
        3. Break down complex concepts into digestible parts
        4. Include examples and explanations
        5. Target duration: 3-5 minutes when spoken
        6. Format as a simple speaking script (no character names, no scene descriptions)
        7. Focus on educational content delivery
        8. Use natural speech patterns and transitions
        
        Write the script as if a teacher is directly speaking to students about this topic.
        Do NOT include character names, scene descriptions, or cinematic elements.
        """

        print(f"🤖 Generating tutorial script...")

        # Generate tutorial script using AI
        tutorial_script = await ai_service.generate_tutorial_script(tutorial_prompt)

        if not tutorial_script:
            print("❌ Failed to generate tutorial script")
            raise HTTPException(
                status_code=500, detail="Failed to generate tutorial script"
            )

        print(f"✅ Tutorial script generated ({len(tutorial_script)} characters)")

        # Generate video using Tavus
        video_service = VideoService(session)

        # Store initial record with pending status
        initial_record = {
            "chapter_id": chapter_id,
            "book_id": book_data["id"],
            "user_id": current_user.id,
            "content_type": "realistic_video",
            "content_url": None,
            "tavus_url": None,
            "tavus_video_id": None,
            "script": tutorial_script,
            "duration": 180,
            "status": "processing",
            "error_message": None,
        }

        print(f"💾 Storing initial record in database...")
        learning_content = LearningContent(
            chapter_id=chapter_id,
            book_id=book_data.id,
            user_id=current_user.id,
            content_type="video_tutorial",
            title=f"Video Tutorial: {chapter_data.title}",
            script=tutorial_script,
            duration=180,
            status="processing",
            error_message=None,
        )
        session.add(learning_content)
        await session.commit()
        await session.refresh(learning_content)
        content_id = str(learning_content.id)

        print(f"✅ Database record created with ID: {content_id}")

        # Use Tavus directly with the tutorial script
        print(f"🎬 Calling Tavus API for video generation...")
        tavus_result = await video_service._generate_tavus_video(
            tutorial_script, "realistic", content_id
        )

        if not tavus_result:
            print("❌ Tavus video generation returned None")
            # Update record with failed status
            if content_id:
                learning_content.status = "failed"
                learning_content.error_message = (
                    "Tavus video generation failed - no result returned"
                )
                session.add(learning_content)
                await session.commit()
            raise HTTPException(
                status_code=500,
                detail="Failed to generate realistic video - Tavus returned no result",
            )

        print(f"✅ Tavus API call completed")
        print(f"📊 Tavus result status: {tavus_result.get('status', 'unknown')}")

        # Extract Tavus information
        tavus_video_id = tavus_result.get("video_id")
        tavus_url = tavus_result.get("hosted_url") or tavus_result.get("video_url")
        download_url = tavus_result.get("download_url")
        final_video_url = tavus_result.get("video_url") or tavus_result.get(
            "download_url"
        )

        print(f"🆔 Tavus Video ID: {tavus_video_id}")
        print(f"🌐 Tavus URL: {tavus_url}")
        print(f"🔗 Final Video URL: {final_video_url}")

        # Only set content_url if video is truly ready (downloadable URL present)
        update_data = {
            "tavus_url": tavus_url,
            "tavus_video_id": tavus_video_id,
            "status": "ready" if final_video_url else "processing",
        }
        if final_video_url:
            update_data["content_url"] = final_video_url
            update_data["duration"] = tavus_result.get("duration", 180)
        if content_id:
            print(f"💾 Updating database record with Tavus results...")
            learning_content.tavus_url = tavus_url
            learning_content.tavus_video_id = tavus_video_id
            learning_content.status = "ready" if final_video_url else "processing"

            if final_video_url:
                learning_content.content_url = final_video_url
                learning_content.duration = tavus_result.get("duration", 180)

            session.add(learning_content)
            await session.commit()

        # Return response
        response_data = {
            "id": content_id or f"video_{int(time.time())}",
            "tavus_url": tavus_url,
            "tavus_video_id": tavus_video_id,
            "status": "ready" if final_video_url else "processing",
        }

        if final_video_url:
            response_data["video_url"] = final_video_url
            response_data["duration"] = tavus_result.get("duration", 180)
        elif tavus_url:
            # If we have a hosted_url but no final video_url, the video is still processing
            # but we can provide the hosted_url for immediate access
            response_data["hosted_url"] = tavus_url
            response_data["message"] = (
                "Video is still processing. You can access it via the hosted URL or wait for completion."
            )

        print(f"✅ Realistic video generation completed successfully")
        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error generating realistic video: {e}")
        import traceback

        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/list-voices")
async def list_voices(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """List available ElevenLabs voices"""
    try:
        elevenlabs_service = ElevenLabsService()
        voices = await elevenlabs_service.list_voices()

        return {"voices": voices}

    except Exception as e:
        print(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-chapter-safety")
async def analyze_chapter_safety(
    request: AnalyzeChapterSafetyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Analyze chapter content for potential KlingAI risk control issues"""
    try:
        # Get chapter details
        stmt = select(Chapter).where(Chapter.id == request.chapter_id)
        result = await session.exec(stmt)
        chapter = result.first()

        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter_content = chapter.content
        chapter_title = chapter.title

        # Analyze content safety
        video_service = VideoService(session)
        safety_analysis = video_service.analyze_chapter_content_safety(
            chapter_content, chapter_title
        )

        return {
            "success": True,
            "analysis": safety_analysis,
            "chapter_id": request.chapter_id,
            "chapter_title": chapter_title,
        }

    except Exception as e:
        print(f"Error analyzing chapter safety: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error analyzing chapter safety: {str(e)}"
        )


@router.get("/check-video-status/{content_id}")
async def check_video_status(
    content_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Check the status of video generation and handle completion"""
    try:
        stmt = select(LearningContent).where(LearningContent.id == content_id)
        result = await session.exec(stmt)
        content_data = result.first()

        if not content_data:
            raise HTTPException(status_code=404, detail="Content not found")
        if content_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this content"
            )
        # If status is already ready and content_url is present, return the data
        if content_data.status == "ready" and content_data.content_url:
            return {
                "id": content_id,
                "status": "ready",
                "video_url": content_data["content_url"],
                "tavus_url": content_data.get("tavus_url"),
                "duration": content_data.duration or 180,
            }
        # If status is processing and we have a Tavus video ID, check its status
        if content_data.status == "processing" and content_data.tavus_video_id:
            video_service = VideoService(session)
            tavus_status = await video_service._poll_video_status(
                content_data.tavus_video_id, f"Video for content {content_id}"
            )
            if tavus_status["status"] in ["completed", "ready"]:
                video_url = tavus_status.get("video_url") or tavus_status.get(
                    "download_url"
                )
                if video_url:
                    final_video_url = await video_service._download_and_store_video(
                        video_url, f"video_{content_id}.mp4", current_user.id
                    )
                    content_data.status = "ready"
                    content_data.content_url = final_video_url
                    content_data.duration = tavus_status.get("duration", 180)
                    session.add(content_data)
                    await session.commit()
                    return {
                        "id": content_id,
                        "status": "ready",
                        "video_url": final_video_url,
                        "tavus_url": content_data.get("tavus_url"),
                        "duration": tavus_status.get("duration", 180),
                    }
                else:
                    return {
                        "id": content_id,
                        "status": "completed_no_download",
                        "tavus_url": content_data.get("tavus_url"),
                        "message": "Video completed but download URL not available",
                    }
            elif tavus_status["status"] == "failed":
                content_data.status = "failed"
                content_data.error_message = tavus_status.get(
                    "error", "Video generation failed"
                )
                session.add(content_data)
                await session.commit()
                return {
                    "id": content_id,
                    "status": "failed",
                    "error": tavus_status.get("error", "Video generation failed"),
                }
            elif tavus_status["status"] == "timeout":
                return {
                    "id": content_id,
                    "status": "timeout",
                    "tavus_url": content_data.get("tavus_url"),
                    "message": tavus_status.get(
                        "message", "Video generation timed out"
                    ),
                }
            else:
                return {
                    "id": content_id,
                    "status": "processing",
                    "tavus_url": content_data.get("tavus_url"),
                    "tavus_video_id": content_data.get("tavus_video_id"),
                    "progress": tavus_status.get("generation_progress", "0/100"),
                }
        # Return current status
        return {
            "id": content_id,
            "status": content_data.status,
            "tavus_url": content_data.tavus_url,
            "error_message": content_data.error_message,
        }
    except Exception as e:
        print(f"Error checking video status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-content/{chapter_id}")
async def get_learning_content(
    chapter_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get existing learning content for a chapter"""
    try:
        # Get all learning content for this chapter

        # Get all learning content for this chapter and user
        stmt = select(LearningContent).where(
            LearningContent.chapter_id == chapter_id,
            LearningContent.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        content_records = result.all()

        if not content_records:
            return {"chapter_id": chapter_id, "content": []}

        # Format content
        user_content = []
        for content in content_records:
            user_content.append(
                {
                    "id": str(content.id),
                    "content_type": content.content_type,
                    "content_url": content.content_url,
                    "tavus_url": content.tavus_url,
                    "status": content.status,
                    "duration": content.duration or 180,
                    "created_at": (
                        content.created_at.isoformat() if content.created_at else None
                    ),
                    "updated_at": (
                        content.updated_at.isoformat() if content.updated_at else None
                    ),
                }
            )

        return {"chapter_id": chapter_id, "content": user_content}

    except Exception as e:
        print(f"Error getting learning content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/combine-videos")
async def combine_videos(
    request: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Combine multiple videos using FFmpeg"""
    try:
        video_urls = request.get("video_urls", [])
        if not video_urls or len(video_urls) < 2:
            raise HTTPException(
                status_code=400, detail="At least 2 video URLs are required"
            )

        video_service = VideoService(session)

        # Combine videos using FFmpeg
        combined_video_url = await video_service._combine_videos_with_ffmpeg(
            video_urls, f"combined_video_{int(time.time())}.mp4", current_user.id
        )

        if not combined_video_url:
            raise HTTPException(status_code=500, detail="Failed to combine videos")

        return {
            "combined_video_url": combined_video_url,
            "source_videos": video_urls,
            "status": "success",
        }

    except Exception as e:
        print(f"Error combining videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/combine-tavus-videos")
async def combine_tavus_videos(
    request: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Combine Tavus video segments and process hosted_url"""
    try:
        print(f"🎬 Starting Tavus video combination for user: {current_user.id}")

        content_id = request.get("content_id")
        if not content_id:
            print("❌ Missing content_id in request")
            raise HTTPException(status_code=400, detail="content_id is required")

        print(f"📖 Processing content: {content_id}")

        # Verify content access
        stmt = select(LearningContent).where(LearningContent.id == content_id)
        result = await session.exec(stmt)
        content_data = result.first()

        if not content_data:
            print(f"❌ Content not found: {content_id}")
            raise HTTPException(status_code=404, detail="Content not found")

        # Check access permissions
        if content_data.user_id != current_user.id:
            print(f"❌ Access denied for content: {content_id}")
            raise HTTPException(
                status_code=403, detail="Not authorized to access this content"
            )

        # Check if content has a Tavus URL
        tavus_url = content_data.tavus_url
        if not tavus_url:
            print(f"❌ No Tavus URL found for content: {content_id}")
            raise HTTPException(
                status_code=400, detail="No Tavus URL found for this content"
            )

        print(f"🌐 Tavus URL found: {tavus_url}")

        # Combine videos using the video service
        video_service = VideoService(session)
        result = await video_service.combine_tavus_videos(content_id)

        if not result:
            print(f"❌ Failed to combine videos for content: {content_id}")
            raise HTTPException(status_code=500, detail="Failed to combine videos")

        print(f"✅ Video combination completed successfully")
        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error combining Tavus videos: {e}")
        import traceback

        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Update the generate_script_and_scenes endpoint
@router.post("/generate-script-and-scenes")
async def generate_script_and_scenes(
    request: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate only the AI script and scene descriptions for a chapter using OpenRouter (no video generation)"""
    try:
        # Extract from request body
        chapter_id = request.get("chapter_id")
        script_style = validate_script_style(request.get("script_style", "cinematic"))
        script_name = request.get("script_name")  # Optional custom name for the script
        plot_context = request.get("plot_context")  # Optional flag/context
        custom_logline = request.get(
            "custom_logline"
        )  # User's specific instructions/logline
        script_story_type = request.get("scriptStoryType")  # Extract script story type

        print(f"[DEBUG] generate_script_and_scenes - received request: {request}")
        print(f"[DEBUG] Custom Logline: {custom_logline}")

        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Try to find chapter in Chapter table first (Explorer mode)
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        book_data = None
        chapter_content = None
        chapter_title = None
        book_id = None
        is_artifact = False

        if chapter_data:
            # Found in Chapter table (Explorer mode or Creator mode with linked book)
            book_data = chapter_data.book
            chapter_content = chapter_data.content
            chapter_title = chapter_data.title
            book_id = chapter_data.book_id
        else:
            # Not in Chapter table - check Artifacts (Creator mode)
            from app.projects.models import Artifact, Project

            stmt = select(Artifact).where(Artifact.id == chapter_id)
            result = await session.exec(stmt)
            artifact_data = result.first()

            if artifact_data:
                is_artifact = True
                # Extract content from artifact
                content_data = artifact_data.content or {}
                chapter_content = content_data.get("content", "")
                chapter_title = content_data.get("title", "Chapter")

                # Get project for access control
                stmt = select(Project).where(Project.id == artifact_data.project_id)
                result = await session.exec(stmt)
                project = result.first()

                if project:
                    if project.user_id != current_user.id:
                        raise HTTPException(
                            status_code=403,
                            detail="Not authorized to access this chapter",
                        )
                    book_id = project.id  # Default to project_id

                    # Try to resolve to real Chapter for RAG (if project has linked book)
                    if project.book_id:
                        chapter_num = content_data.get("chapter_number")
                        if chapter_num:
                            stmt = select(Chapter).where(
                                Chapter.book_id == project.book_id,
                                Chapter.chapter_number == chapter_num,
                            )
                            real_chapter = (await session.exec(stmt)).first()
                            if real_chapter:
                                print(
                                    f"[ScriptGen] Resolved Artifact {chapter_id} to Chapter {real_chapter.id}"
                                )
                                chapter_id = (
                                    real_chapter.id
                                )  # Switch to real Chapter ID
                                is_artifact = False  # Treat as normal chapter for RAG
                                book_id = project.book_id  # Use real book ID
                                # Update content from real chapter to be safe
                                chapter_content = real_chapter.content
                                chapter_title = real_chapter.title
                else:
                    raise HTTPException(status_code=404, detail="Project not found")
            else:
                raise HTTPException(status_code=404, detail="Chapter not found")

        # Check access permissions (for regular chapters with books)
        if book_data:
            if book_data.status != "published" and book_data.user_id != current_user.id:
                raise HTTPException(
                    status_code=403, detail="Not authorized to access this chapter"
                )

        # ✅ NEW: Check subscription tier and limits
        subscription_manager = SubscriptionManager(session)
        user_tier = await subscription_manager.get_user_tier(current_user.id)
        tier_check = await subscription_manager.can_user_generate_video(current_user.id)

        if not tier_check["can_generate"]:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly limit reached. You have used {tier_check['videos_used']} out of {tier_check['videos_limit']} videos. Please upgrade your subscription.",
            )

        # Map subscription tier to model tier
        model_tier_mapping = {
            "free": ModelTier.FREE,
            "basic": ModelTier.BASIC,
            "standard": ModelTier.STANDARD,
            "premium": ModelTier.PREMIUM,
            "professional": ModelTier.PROFESSIONAL,
        }
        user_model_tier = model_tier_mapping.get(user_tier.value, ModelTier.FREE)

        print(
            f"[OpenRouter] Generating {script_style} script for {user_tier.value} tier user"
        )

        # Initialize OpenRouter service
        openrouter_service = OpenRouterService()

        # Get chapter context for enhanced content
        rag_service = RAGService(session)
        if not is_artifact:
            # For regular chapters, use RAG to get context and adjacent chapters
            chapter_context = await rag_service.get_chapter_with_context(
                chapter_id, include_adjacent=True
            )
        else:
            # For artifacts (Creator mode), use extracted content directly
            # RAG/Embeddings might not be ready or applicable yet
            chapter_context = {
                "total_context": chapter_content,
                "chapter": {"title": chapter_title, "content": chapter_content},
            }

        # Prepare content for OpenRouter based on script style
        content_for_script = chapter_context.get("total_context", chapter_content)

        # Enhance with plot context (Always attempt if we have a book_id, or if custom_logline is provided)
        plot_enhanced = False
        plot_info = None

        # We should try to enhance if explicitly requested OR if we have custom logline OR by default?
        # Let's say we always try to enhance if it's a book chapter to get better results.
        # But previous logic used `if plot_context`. Let's assume frontend now sends plot_context=True usually,
        # OR we trigger it if `custom_logline` is present.

        should_enhance = plot_context or custom_logline

        if should_enhance:
            try:
                plot_info = await enhance_with_plot_context(
                    session,
                    current_user.id,
                    book_id,
                    content_for_script,
                    custom_logline=custom_logline,
                )
                if plot_info and plot_info.get("enhanced_content"):
                    content_for_script = plot_info["enhanced_content"]
                    plot_enhanced = True
                    print(
                        f"[PlotService] Enhanced script generation with plot context for chapter {chapter_id}"
                    )

            except Exception as plot_error:
                print(
                    f"[PlotService] Warning: Could not enhance with plot context: {str(plot_error)}"
                )
                # Continue with original content if plot enhancement fails

        # Extract target duration from request
        target_duration = request.get("target_duration", "auto")
        if target_duration == "auto":
            target_duration = "auto"
        elif isinstance(target_duration, str) and target_duration.isdigit():
            target_duration = int(target_duration)
        else:
            target_duration = None

        # ✅ Generate script using OpenRouter with tier-appropriate model
        script_result = await openrouter_service.generate_script(
            content=chapter_content,  # Use chapter content (works for both Chapter and Artifact)
            user_tier=user_model_tier,
            script_type=script_style,
            target_duration=target_duration,
            plot_context=(
                plot_info if plot_info and plot_info.get("enhanced_content") else None
            ),
        )

        if script_result.get("status") != "success":
            raise HTTPException(
                status_code=500,
                detail=f"OpenRouter script generation failed: {script_result.get('error', 'Unknown error')}",
            )

        script = script_result.get("content", "")
        usage = script_result.get("usage", {})

        # ✅ First, try to parse scenes directly from the script
        scene_descriptions = []

        # Parse scenes directly from script by looking for scene headers
        script_lines = script.split("\n")
        current_scene = ""
        scene_number = 0
        pending_location = None  # Track location header to merge with scene

        for i, line in enumerate(script_lines):
            line_stripped = line.strip()

            # Check if this is an ACT-SCENE header (primary scene marker)
            # Check if this is an ACT-SCENE header (primary scene marker) - supports both screenplay and narration styles
            act_scene_match = re.match(
                r"^(?:(?:\*?\*?ACT\s+[IVX0-9]+\s*-?\s*SCENE\s+\d+\*?\*?)|(?:###\s*.*\[.*\]))",
                line_stripped,
                re.IGNORECASE,
            )

            # Check if this is a location header (INT./EXT.)
            location_match = re.match(
                r"^(?:INT\.|EXT\.)\s+.+\s+-\s+(?:DAY|NIGHT|MORNING|EVENING|AFTERNOON)",
                line_stripped,
                re.IGNORECASE,
            )

            if act_scene_match:
                # Save previous scene if it exists
                if current_scene and len(current_scene) > 20:
                    scene_descriptions.append(current_scene[:400])

                # Start new scene
                scene_number += 1
                current_scene = line_stripped
                pending_location = None  # Reset pending location

                # Look ahead for location header on next line
                if i + 1 < len(script_lines):
                    next_line = script_lines[i + 1].strip()
                    if re.match(r"^(?:INT\.|EXT\.)", next_line, re.IGNORECASE):
                        current_scene += " " + next_line
                        # Add context from lines after location
                        context_lines = []
                        for j in range(i + 2, min(i + 6, len(script_lines))):
                            ctx_line = script_lines[j].strip()
                            if (
                                ctx_line
                                and not ctx_line.isupper()
                                and len(ctx_line) > 10
                            ):
                                context_lines.append(ctx_line)
                            if len(context_lines) >= 2:
                                break
                        if context_lines:
                            current_scene += " " + " ".join(context_lines)
                    else:
                        # No location header, just add context
                        context_lines = []
                        for j in range(i + 1, min(i + 5, len(script_lines))):
                            ctx_line = script_lines[j].strip()
                            if (
                                ctx_line
                                and not ctx_line.isupper()
                                and len(ctx_line) > 10
                            ):
                                context_lines.append(ctx_line)
                            if len(context_lines) >= 2:
                                break
                        if context_lines:
                            current_scene += " " + " ".join(context_lines)

            # Skip location headers as they're included with ACT-SCENE headers
            # Don't match them as separate scenes

        # Add the last scene
        if current_scene and len(current_scene) > 20:
            scene_descriptions.append(current_scene[:400])

        # If direct parsing found scenes, use those
        if scene_descriptions and len(scene_descriptions) > 1:
            print(
                f"[DEBUG] Parsed {len(scene_descriptions)} scenes directly from script"
            )
        else:
            # Fallback: Use AI to analyze and extract scenes
            print(
                f"[DEBUG] Direct parsing found {len(scene_descriptions)} scenes, using AI analysis fallback"
            )
            scene_breakdown_result = await openrouter_service.analyze_content(
                content=f"""Extract ALL scenes from this script. Identify acts and scenes properly.

For each scene, provide:
- Act number (I, II, or III)
- Scene number within the act
- Location and time of day
- Key action/description (2-3 sentences)
- Characters involved

Format each scene as:
ACT [I/II/III] - SCENE [number]: [Location] - [Time]
Description: [detailed visual description]
Characters: [list of characters]

Script to analyze:
{script}""",
                user_tier=user_model_tier,
                analysis_type="summary",
            )

            if scene_breakdown_result.get("status") == "success":
                analysis_result = scene_breakdown_result.get("result", "")
                ai_scenes = parse_scene_descriptions(analysis_result)
                if len(ai_scenes) > len(scene_descriptions):
                    scene_descriptions = ai_scenes
                    print(f"[DEBUG] AI analysis found {len(ai_scenes)} scenes")

        # Allow more scenes (up to 30 for complete story coverage)
        scene_descriptions = scene_descriptions[:30]
        print(f"[DEBUG] Final scene count: {len(scene_descriptions)}")

        # ✅ Generate character analysis using OpenRouter
        character_analysis_result = await openrouter_service.analyze_content(
            content=f"Extract and describe all characters mentioned in this script. Format as 'Character Name: [brief description/role]':\n\n{script}",
            user_tier=user_model_tier,
            analysis_type="characters",
        )

        characters = []
        character_details = ""
        if character_analysis_result.get("status") == "success":
            character_details = character_analysis_result.get("result", "")
            # Extract character names with improved logic, filtered by script style
            characters = extract_characters(character_details, script_style)

        # ✅ FALLBACK: If no characters found from AI analysis, extract directly from script
        if not characters or len(characters) == 0:
            print(
                f"[DEBUG] No characters from AI analysis, extracting directly from script"
            )
            # Extract character names from dialogue - lines that are all caps followed by dialogue
            script_lines = script.split("\n")
            potential_characters = set()

            for i, line in enumerate(script_lines):
                line_stripped = line.strip()
                # Look for character names: ALL CAPS lines that are not scene headers
                if (
                    line_stripped
                    and line_stripped.isupper()
                    and not line_stripped.startswith(
                        ("INT.", "EXT.", "SCENE", "ACT", "FADE", "CUT TO")
                    )
                    and not any(x in line_stripped for x in ["**", ":", "NARRATOR ("])
                ):
                    # Clean up the character name
                    char_name = line_stripped.strip("*").strip()
                    # Remove parenthetical descriptions like "(V.O.)" or "(mocking)"
                    char_name = re.sub(r"\([^)]+\)", "", char_name).strip()
                    # Only add if it looks like a valid name (2-30 chars, contains letters)
                    if 2 <= len(char_name) <= 30 and any(
                        c.isalpha() for c in char_name
                    ):
                        potential_characters.add(char_name.title())

            characters = list(potential_characters)[:15]  # Limit to 15 characters
            print(
                f"[DEBUG] Extracted {len(characters)} characters directly from script: {characters}"
            )

        # Generate default script name if not provided
        if not script_name:
            try:
                # Count existing scripts for this chapter
                statement = select(func.count()).where(
                    Script.chapter_id == uuid.UUID(chapter_id)
                )
                result = await session.exec(statement)
                count = result.one()
            except Exception as e:
                print(f"Error counting scripts: {e}")
                count = 0

            style_display = script_style.replace("_", " ").title()
            if "cinematic" in script_style.lower():
                style_display = "Character Dialogue"
            elif "narration" in script_style.lower():
                style_display = "Voice-over Narration"

            script_name = f"{style_display} {count + 1:03d}"

        # Enhanced script data with metadata
        script_data = {
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "script_name": script_name,
            "user_id": current_user.id,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "total_scenes": len(scene_descriptions),
                "estimated_duration": len(script) * 0.01,  # Rough estimate
                "has_characters": len(characters) > 0,
                "script_length": len(script),
                "model_used": script_result.get("model_used", "unknown"),
                "tier": user_tier.value,
                "tokens_used": usage.get("total_tokens", 0),
                "estimated_cost": usage.get("estimated_cost", 0),
            },
        }

        # NOTE: Script data is stored in the dedicated Script table below
        # The Chapter model does not have ai_generated_content field

        # Allow multiple scripts per chapter by not checking for existing ones
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user.id,
            "script_style": script_style,
            "script_name": script_name,
            "script": script,
            "video_style": script_style,  # Required field - use script_style as default
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "metadata": script_data["metadata"],
            "status": "ready",
            "service_used": "openrouter",
            "script_story_type": script_story_type,  # Store the script story type
        }

        print(
            f"[DEBUG] generate_script_and_scenes - storing script_record with script_story_type: {script_story_type}"
        )

        # Always insert new script (allow multiple scripts per chapter)
        new_script = Script(**script_record)
        session.add(new_script)
        await session.commit()
        await session.refresh(new_script)
        script_id = str(new_script.id)

        # ✅ Record usage for billing/limits
        await subscription_manager.record_usage(
            user_id=current_user.id,
            resource_type="script",
            cost_usd=usage.get("estimated_cost", 0.0),
            metadata={
                "script_style": script_style,
                "model_used": script_data["metadata"].get("model_used", "unknown"),
                "tokens_used": usage.get("total_tokens", 0),
            },
        )

        print(
            f"[OpenRouter] Successfully generated {script_style} script with {len(characters)} characters and {len(scene_descriptions)} scenes"
        )

        return {
            "chapter_id": chapter_id,
            "script_id": script_id,
            "script_name": script_name,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "metadata": script_data["metadata"],
            "service_used": "openrouter",
            "tier": user_tier.value,
            "plot_enhanced": plot_enhanced,
            "plot_info": plot_info["plot_info"] if plot_info else None,
            "usage_info": {
                "tokens_used": usage.get("total_tokens", 0),
                "estimated_cost": usage.get("estimated_cost", 0),
                "model_used": script_result.get("model_used"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating script and scenes with OpenRouter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-script-and-scenes")
async def generate_script_and_scenes_with_gpt(
    request: dict = Body(...),  # Accept body instead of query params
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Generate only the AI script and scene descriptions for a chapter (no video generation)"""
    try:
        # Extract from request body
        chapter_id = request.get("chapter_id")
        script_style = request.get("script_style", "cinematic_movie")

        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book

        # Check access permissions
        if book_data.status != "published" and book_data.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this chapter"
            )
        # Generate script using RAGService
        rag_service = RAGService(session)
        chapter_context = await rag_service.get_chapter_with_context(
            chapter_id, include_adjacent=True
        )
        script_result = await rag_service.generate_video_script(
            chapter_context,
            video_style=getattr(book_data, "book_type", "realistic") or "realistic",
            script_style=script_style,
        )
        script = script_result.get("script", "")
        characters = script_result.get("characters", [])
        character_details = script_result.get("character_details", "")
        # Parse script for scene descriptions
        video_service = VideoService()
        parsed = video_service._parse_script_for_services(script, script_style)
        scene_descriptions = parsed.get("scene_descriptions") or parsed.get(
            "parsed_sections", {}
        ).get("scene_descriptions", [])

        # Enhanced script data with metadata
        script_data = {
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "user_id": current_user.id,
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "total_scenes": len(scene_descriptions),
                "estimated_duration": len(script) * 0.01,  # Rough estimate
                "has_characters": len(characters) > 0,
                "script_length": len(script),
            },
        }

        # Store in chapters table (your existing approach)
        # Store in chapters table (your existing approach)
        ai_content = chapter_data.ai_generated_content or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user.id}:{script_style}"
        ai_content[key] = script_data

        chapter_data.ai_generated_content = ai_content
        session.add(chapter_data)
        await session.commit()

        # ALSO create a dedicated scripts table entry for easier access
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user.id,
            "script_style": script_style,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "metadata": script_data["metadata"],
            "status": "ready",
        }

        # Insert or update in scripts table
        # Insert or update in scripts table
        stmt = select(Script).where(
            Script.chapter_id == chapter_id,
            Script.user_id == current_user.id,
            Script.script_style == script_style,
        )
        result = await session.exec(stmt)
        existing_script = result.first()

        if existing_script:
            # Update existing
            for key, value in script_record.items():
                setattr(existing_script, key, value)
            session.add(existing_script)
            await session.commit()
            await session.refresh(existing_script)
            script_id = str(existing_script.id)
        else:
            # Insert new
            new_script = Script(**script_record)
            session.add(new_script)
            await session.commit()
            await session.refresh(new_script)
            script_id = str(new_script.id)

        return {
            "chapter_id": chapter_id,
            "script_id": script_id,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "metadata": script_data["metadata"],
        }
    except Exception as e:
        print(f"Error generating script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-script-and-scenes")
async def save_script_and_scenes(
    chapter_id: str = Body(...),
    script: str = Body(...),
    scene_descriptions: list = Body(...),
    characters: list = Body(...),
    character_details: str = Body(...),
    script_style: str = Body(...),
    script_name: str = Body(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Save a new AI-generated script and scene descriptions for a chapter."""
    try:
        # Verify chapter access
        # Verify chapter access
        stmt = (
            select(Chapter)
            .options(selectinload(Chapter.book))
            .where(Chapter.id == chapter_id)
        )
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        book_data = chapter_data.book
        if str(book_data.user_id) != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this chapter"
            )

        # Generate default script name if not provided
        if not script_name:
            try:
                # Count existing scripts for this chapter
                statement = select(func.count()).where(
                    Script.chapter_id == uuid.UUID(chapter_id)
                )
                result = await session.exec(statement)
                count = result.one()
            except Exception as e:
                print(f"Error counting scripts: {e}")
                count = 0

            style_display = script_style.replace("_", " ").title()
            if "cinematic" in script_style.lower():
                style_display = "Character Dialogue"
            elif "narration" in script_style.lower():
                style_display = "Voice-over Narration"

            script_name = f"{style_display} {count + 1:03d}"

        # Validate script style
        script_style = validate_script_style(script_style)

        # Create new script record (allow multiple scripts)
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user.id,
            "script_style": script_style,
            "script_name": script_name,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "metadata": {
                "total_scenes": len(scene_descriptions),
                "estimated_duration": len(script) * 0.01,
                "has_characters": len(characters) > 0,
                "script_length": len(script),
            },
            "status": "ready",
            "service_used": "manual",
        }

        new_script = Script(**script_record)
        session.add(new_script)
        await session.commit()
        await session.refresh(new_script)
        script_id = str(new_script.id)

        return {
            "message": "Saved",
            "chapter_id": chapter_id,
            "script_id": script_id,
            "script_name": script_name,
            "script_style": script_style,
        }
    except Exception as e:
        print(f"Error saving script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get-script-and-scenes")
async def get_script_and_scenes(
    chapter_id: str,
    script_style: str = "cinematic_movie",
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Fetch the saved AI-generated script and scene descriptions for a chapter (per user)."""
    try:
        stmt = select(Chapter).where(Chapter.id == chapter_id)
        result = await session.exec(stmt)
        chapter_data = result.first()

        if not chapter_data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        ai_content = chapter_data.ai_generated_content or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user.id}:{script_style}"
        result = ai_content.get(key)
        if not result:
            return {
                "chapter_id": chapter_id,
                "script_style": script_style,
                "content": None,
            }
        return {
            "chapter_id": chapter_id,
            "script_style": script_style,
            "content": result,
        }
    except Exception as e:
        print(f"Error fetching script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-script/{script_id}")
async def delete_script(
    script_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a specific script by ID."""
    try:
        print(f"[DEBUG] Deleting script {script_id} for user {current_user.id}")

        try:
            s_uuid = uuid.UUID(script_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid script ID format")

        # Verify script ownership
        stmt = select(Script).where(Script.id == s_uuid)
        result = await session.exec(stmt)
        script_data = result.first()

        if not script_data:
            print(f"[DEBUG] Script {script_id} not found in DB")
            raise HTTPException(status_code=404, detail="Script not found")

        if str(script_data.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this script"
            )

        # Capture data before delete
        style = script_data.script_style

        # RAW DELETE
        delete_stmt = delete(Script).where(Script.id == s_uuid)
        await session.exec(delete_stmt)
        await session.commit()

        # Verify deletion
        verify_stmt = select(Script).where(Script.id == s_uuid)
        verify_res = await session.exec(verify_stmt)
        if verify_res.first():
            print(f"[ERROR] Script {script_id} STILL EXISTS after delete commit!")
            raise HTTPException(
                status_code=500, detail="Database refused to delete script"
            )

        print(f"[DEBUG] Script {script_id} deleted and committed.")

        return {
            "message": "Script deleted successfully",
            "script_id": script_id,
            "script_style": style,
        }
    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        print(f"Error deleting script: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class ScriptUpdate(SQLModel):
    script_name: Optional[str] = None
    characters: Optional[List[str]] = None
    character_ids: Optional[List[str]] = None  # UUIDs of linked plot characters
    character_details: Optional[str] = None
    status: Optional[str] = None


@router.patch("/script/{script_id}")
async def update_script(
    script_id: str,
    script_update: ScriptUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    try:
        script = await session.get(Script, uuid.UUID(script_id))
        if not script:
            raise HTTPException(status_code=404, detail="Script not found")

        # Check authorization
        if str(script.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized")

        # Update all provided fields
        if script_update.script_name is not None:
            script.script_name = script_update.script_name

        if script_update.characters is not None:
            script.characters = script_update.characters

        if script_update.character_ids is not None:
            script.character_ids = script_update.character_ids

        if script_update.character_details is not None:
            script.character_details = script_update.character_details

        if script_update.status is not None:
            script.status = script_update.status

        session.add(script)
        await session.commit()
        await session.refresh(script)

        return script
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline-status/{video_gen_id}")
async def get_pipeline_status(
    video_gen_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Get detailed pipeline status for video generation"""
    try:
        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_data = result.first()

        if not video_data:
            raise HTTPException(status_code=404, detail="Video generation not found")

        # Get pipeline steps
        stmt = (
            select(PipelineStepModel)
            .where(PipelineStepModel.video_generation_id == video_gen_id)
            .order_by(PipelineStepModel.step_order)
        )
        result = await session.exec(stmt)
        pipeline_steps = result.all()

        # Calculate progress
        total_steps = len(pipeline_steps) or 5  # Default to 5 steps
        completed_steps = len([s for s in pipeline_steps if s.status == "completed"])
        failed_steps = len([s for s in pipeline_steps if s.status == "failed"])

        # Determine current step
        current_step = None
        next_step = None

        processing_steps = [s for s in pipeline_steps if s.status == "processing"]
        if processing_steps:
            current_step = processing_steps[0].step_name
        else:
            # Find next pending step
            pending_steps = [s for s in pipeline_steps if s.status == "pending"]
            if pending_steps:
                next_step = pending_steps[0].step_name

        # Calculate percentage
        percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0

        # Determine overall status
        overall_status = video_data.generation_status

        # Build response
        pipeline_status = {
            "overall_status": overall_status,
            "failed_at_step": (
                video_data.task_meta.get("failed_at_step")
                if video_data.task_meta
                else None
            ),
            "can_resume": video_data.can_resume,
            "retry_count": video_data.retry_count,
            "progress": {
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "total_steps": total_steps,
                "percentage": round(percentage, 1),
                "current_step": current_step,
                "next_step": next_step,
            },
            "steps": [s.model_dump() for s in pipeline_steps],
            "pipeline_state": (
                video_data.task_meta.get("pipeline_state", {})
                if video_data.task_meta
                else {}
            ),
        }

        return pipeline_status

    except Exception as e:
        print(f"Error getting pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-generation/{video_gen_id}")
async def retry_video_generation(
    video_gen_id: str,
    request: dict = Body(default={}),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Retry video generation from failed step or specific step - with smart resume logic"""
    try:
        print(f"🔄 Starting retry for video generation: {video_gen_id}")
        print(f"🔄 Request body: {request}")

        # Extract retry_from_step from request body
        retry_from_step = request.get("retry_from_step") if request else None

        # Verify access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_gen_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        video_data = video_response.model_dump()
        current_status = video_data.get("generation_status")

        print(f"🔄 Current status: {current_status}")

        # ✅ NEW: Smart step determination based on existing data
        next_step = await determine_next_step_from_database(
            video_gen_id, video_data, session
        )

        if retry_from_step:
            try:
                requested_step = PipelineStep(retry_from_step)
                # Warn if they're trying to redo a completed step
                if next_step.value > requested_step.value:
                    print(
                        f"⚠️  WARNING: User requested step {requested_step.value} but {next_step.value} is the next logical step"
                    )
                step_to_retry = requested_step
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid step: {retry_from_step}"
                )
        else:
            step_to_retry = next_step

        print(f"🔄 Determined retry step: {step_to_retry.value}")

        # Update retry count
        retry_count = video_data.get("retry_count", 0) + 1

        # Update video generation status based on step
        new_status = get_status_for_step(step_to_retry)

        video_response.generation_status = new_status
        video_response.task_meta["failed_at_step"] = None
        video_response.task_meta["error_message"] = None
        video_response.retry_count = retry_count
        video_response.can_resume = False
        video_response.updated_at = datetime.now()

        session.add(video_response)
        await session.commit()

        # Trigger the appropriate task
        task_id = await trigger_task_for_step(step_to_retry, video_gen_id, session)

        return {
            "message": f"Retrying from step: {step_to_retry.value}",
            "video_generation_id": video_gen_id,
            "retry_step": step_to_retry.value,
            "task_id": task_id,
            "retry_count": retry_count,
            "new_status": new_status,
            "existing_progress": await get_existing_progress_summary(
                video_gen_id, session
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in retry: {e}")
        import traceback

        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def determine_next_step_from_database(
    video_gen_id: str, video_data: dict, session: AsyncSession
) -> PipelineStep:
    """Determine the next step based on existing SUCCESSFUL data in the database"""

    print(f"🔍 Analyzing existing data for video generation: {video_gen_id}")

    # ✅ FIXED: Check for actual successful completions, not just existence
    audio_files = video_data.get("audio_files") or {}

    # Count actual successful audio files
    narrator_count = len(audio_files.get("narrator", []))
    characters_count = len(audio_files.get("characters", []))
    sound_effects_count = len(audio_files.get("sound_effects", []))
    background_music_count = len(audio_files.get("background_music", []))
    total_audio_count = (
        narrator_count + characters_count + sound_effects_count + background_music_count
    )

    has_audio = total_audio_count > 0

    # ✅ FIXED: Check image statistics for successful generations
    image_data = video_data.get("image_data") or {}
    image_stats = image_data.get("statistics", {})
    successful_images = image_stats.get("total_images_generated", 0)
    character_images_generated = image_stats.get("character_images_generated", 0)
    scene_images_generated = image_stats.get("scene_images_generated", 0)

    has_images = successful_images > 0 or (
        character_images_generated > 0 or scene_images_generated > 0
    )

    # ✅ FIXED: Check video statistics for successful generations
    video_data_obj = video_data.get("video_data") or {}
    video_stats = video_data_obj.get("statistics", {})
    successful_videos = video_stats.get("videos_generated", 0)

    has_videos = successful_videos > 0

    # ✅ FIXED: Check for actual final video URL
    has_merged_video = bool(video_data.get("video_url"))

    # ✅ FIXED: Check lipsync statistics
    lipsync_data = video_data.get("lipsync_data") or {}
    lipsync_stats = lipsync_data.get("statistics", {})
    lipsync_scenes = lipsync_stats.get("scenes_processed", 0)

    has_lipsync = lipsync_scenes > 0

    # Also check database tables for more accuracy - but check for COMPLETED status
    try:
        # Check audio_generations table - only count completed
        stmt = select(func.count(AudioGeneration.id)).where(
            AudioGeneration.video_generation_id == video_gen_id,
            AudioGeneration.status == "completed",
        )
        result = await session.exec(stmt)
        db_audio_count = result.one()

        # Check image_generations table - only count completed
        stmt = select(func.count(ImageGeneration.id)).where(
            ImageGeneration.video_generation_id == video_gen_id,
            ImageGeneration.status == "completed",
        )
        result = await session.exec(stmt)
        db_image_count = result.one()

        # Check video_segments table - only count completed
        stmt = select(func.count(VideoSegment.id)).where(
            VideoSegment.video_generation_id == video_gen_id,
            VideoSegment.status == "completed",
        )
        result = await session.exec(stmt)
        db_video_count = result.one()

        # Use database data as the source of truth with counts
        has_audio = has_audio or (db_audio_count > 0)
        has_images = has_images or (db_image_count > 0)
        has_videos = has_videos or (db_video_count > 0)

        print(f"📊 Database verification:")
        print(f"   - DB Audio files: {db_audio_count}")
        print(f"   - DB Image files: {db_image_count}")
        print(f"   - DB Video files: {db_video_count}")

    except Exception as db_error:
        print(f"⚠️  Database check error: {db_error}")
        # Continue with original data if DB check fails

    print(f"📊 Existing progress (CORRECTED):")
    print(f"   - Audio: {'✅' if has_audio else '❌'} ({total_audio_count} files)")
    print(
        f"   - Images: {'✅' if has_images else '❌'} ({successful_images} generated)"
    )
    print(
        f"   - Videos: {'✅' if has_videos else '❌'} ({successful_videos} generated)"
    )
    print(f"   - Merged: {'✅' if has_merged_video else '❌'}")
    print(f"   - Lipsync: {'✅' if has_lipsync else '❌'} ({lipsync_scenes} scenes)")

    # Determine next step based on what's actually missing
    if not has_audio:
        print(f"🎯 Next step: AUDIO_GENERATION (missing audio)")
        return PipelineStep.AUDIO_GENERATION

    if not has_images:
        print(f"🎯 Next step: IMAGE_GENERATION (missing images)")
        return PipelineStep.IMAGE_GENERATION

    if not has_videos:
        print(f"🎯 Next step: VIDEO_GENERATION (missing videos)")
        return PipelineStep.VIDEO_GENERATION

    if not has_merged_video:
        print(f"🎯 Next step: AUDIO_VIDEO_MERGE (missing final video)")
        return PipelineStep.AUDIO_VIDEO_MERGE

    # Check if lipsync is needed (only if there are character dialogues)
    script_data = video_data.get("script_data") or {}
    characters = script_data.get("characters", [])
    character_audio = audio_files.get("characters", [])

    needs_lipsync = bool(characters and character_audio)

    if needs_lipsync and not has_lipsync:
        print(
            f"🎯 Next step: LIP_SYNC (missing lipsync for {len(characters)} characters)"
        )
        return PipelineStep.LIP_SYNC

    # If everything exists, just return the status-based step
    current_status = video_data.get("generation_status", "failed")
    if current_status == "completed":
        print(f"🎯 All steps completed, but retrying LIP_SYNC as final step")
        return PipelineStep.LIP_SYNC
    else:
        print(f"🎯 Defaulting to AUDIO_GENERATION as fallback")
        return PipelineStep.AUDIO_GENERATION


async def get_existing_progress_summary(
    video_gen_id: str, session: AsyncSession
) -> dict:
    """Get a summary of existing progress for the frontend - CORRECTED VERSION"""
    try:
        stmt = select(VideoGeneration).where(VideoGeneration.id == video_gen_id)
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            return {}

        video_data = video_response.model_dump()

        # ✅ FIXED: Count actual successful items, not just existence
        audio_files = video_data.get("audio_files") or {}
        image_data = video_data.get("image_data") or {}
        video_data_obj = video_data.get("video_data") or {}

        # Count actual audio files
        audio_count = (
            len(audio_files.get("narrator", []))
            + len(audio_files.get("characters", []))
            + len(audio_files.get("sound_effects", []))
            + len(audio_files.get("background_music", []))
        )

        # Get actual successful counts from statistics
        image_stats = image_data.get("statistics", {})
        image_count = image_stats.get("total_images_generated", 0)

        video_stats = video_data_obj.get("statistics", {})
        video_count = video_stats.get("videos_generated", 0)

        return {
            "audio_files_count": audio_count,
            "images_count": image_count,
            "videos_count": video_count,
            "has_final_video": bool(video_data.get("video_url")),
            "last_completed_step": get_last_completed_step_corrected(video_data),
            "progress_percentage": calculate_progress_percentage_corrected(video_data),
        }

    except Exception as e:
        print(f"Error getting progress summary: {e}")
        return {}


def get_last_completed_step_corrected(video_data: dict) -> str:
    """Determine the last completed step - CORRECTED VERSION"""

    # Check actual successful counts
    audio_files = video_data.get("audio_files") or {}
    total_audio = (
        len(audio_files.get("narrator", []))
        + len(audio_files.get("characters", []))
        + len(audio_files.get("sound_effects", []))
        + len(audio_files.get("background_music", []))
    )

    image_data = video_data.get("image_data") or {}
    image_stats = image_data.get("statistics", {})
    total_images = image_stats.get("total_images_generated", 0)

    video_data_obj = video_data.get("video_data") or {}
    video_stats = video_data_obj.get("statistics", {})
    total_videos = video_stats.get("videos_generated", 0)

    lipsync_data = video_data.get("lipsync_data") or {}
    lipsync_stats = lipsync_data.get("statistics", {})
    lipsync_scenes = lipsync_stats.get("scenes_processed", 0)

    has_final_video = bool(video_data.get("video_url"))

    # Return the last successfully completed step
    if lipsync_scenes > 0:
        return "lipsync_completed"
    elif has_final_video:
        return "merge_completed"
    elif total_videos > 0:
        return "video_completed"
    elif total_images > 0:
        return "images_completed"
    elif total_audio > 0:
        return "audio_completed"
    else:
        return "none"


def calculate_progress_percentage_corrected(video_data: dict) -> float:
    """Calculate overall progress percentage - CORRECTED VERSION"""
    steps_completed = 0
    total_steps = 5  # audio, image, video, merge, lipsync

    # Check actual successful completions
    audio_files = video_data.get("audio_files") or {}
    total_audio = (
        len(audio_files.get("narrator", []))
        + len(audio_files.get("characters", []))
        + len(audio_files.get("sound_effects", []))
        + len(audio_files.get("background_music", []))
    )

    if total_audio > 0:
        steps_completed += 1

    image_data = video_data.get("image_data") or {}
    if image_data.get("statistics", {}).get("total_images_generated", 0) > 0:
        steps_completed += 1

    video_data_obj = video_data.get("video_data") or {}
    if video_data_obj.get("statistics", {}).get("videos_generated", 0) > 0:
        steps_completed += 1

    if video_data.get("video_url"):
        steps_completed += 1

    lipsync_data = video_data.get("lipsync_data") or {}
    if lipsync_data.get("statistics", {}).get("scenes_processed", 0) > 0:
        steps_completed += 1

    return (steps_completed / total_steps) * 100


def get_status_for_step(step: PipelineStep) -> str:
    """Get the appropriate status for a pipeline step"""
    status_mapping = {
        PipelineStep.AUDIO_GENERATION: "generating_audio",
        PipelineStep.IMAGE_GENERATION: "generating_images",
        PipelineStep.VIDEO_GENERATION: "generating_video",
        PipelineStep.AUDIO_VIDEO_MERGE: "merging_audio",
        PipelineStep.LIP_SYNC: "applying_lipsync",
    }
    return status_mapping.get(step, "retrying")


async def trigger_task_for_step(
    step: PipelineStep, video_gen_id: str, session: AsyncSession
) -> str:
    """Trigger the appropriate task for a pipeline step"""
    try:
        task_id = None

        if step == PipelineStep.AUDIO_GENERATION:
            from app.tasks.audio_tasks import generate_all_audio_for_video

            task = generate_all_audio_for_video.delay(video_gen_id)
            task_id = task.id
            print(f"🎵 Started audio generation task: {task_id}")

        elif step == PipelineStep.IMAGE_GENERATION:
            from app.tasks.image_tasks import generate_all_images_for_video

            task = generate_all_images_for_video.delay(video_gen_id)
            task_id = task.id
            print(f"🖼️  Started image generation task: {task_id}")

        elif step == PipelineStep.VIDEO_GENERATION:
            from app.tasks.video_tasks import generate_all_videos_for_generation

            task = generate_all_videos_for_generation.delay(video_gen_id)
            task_id = task.id
            print(f"🎬 Started video generation task: {task_id}")

        elif step == PipelineStep.AUDIO_VIDEO_MERGE:
            from app.tasks.merge_tasks import merge_audio_video_for_generation

            task = merge_audio_video_for_generation.delay(video_gen_id)
            task_id = task.id
            print(f"🔗 Started merge task: {task_id}")

        elif step == PipelineStep.LIP_SYNC:
            from app.tasks.lipsync_tasks import apply_lip_sync_to_generation

            task = apply_lip_sync_to_generation.delay(video_gen_id)
            task_id = task.id
            print(f"💋 Started lipsync task: {task_id}")

        return task_id

    except Exception as task_error:
        print(f"❌ Failed to start task for step {step.value}: {task_error}")

        # Revert status back to failed
        # Revert status back to failed
        stmt = select(VideoGeneration).where(VideoGeneration.id == video_gen_id)
        result = await session.exec(stmt)
        video_gen = result.first()

        if video_gen:
            video_gen.generation_status = "failed"
            video_gen.error_message = f"Failed to start retry task: {str(task_error)}"
            video_gen.can_resume = True
            session.add(video_gen)
            await session.commit()

        raise HTTPException(
            status_code=500, detail=f"Failed to start retry task: {str(task_error)}"
        )


@router.get("/video-generation/{video_generation_id}/status")
async def get_video_generation_polling_status(
    video_generation_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Comprehensive polling endpoint for video generation status with step-by-step progress"""
    try:
        # Verify access to video generation
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == video_generation_id,
            VideoGeneration.user_id == current_user.id,
        )
        result = await session.exec(stmt)
        video_response = result.first()

        if not video_response:
            raise HTTPException(status_code=404, detail="Video generation not found")

        video_data = video_response.model_dump()
        overall_status = video_data.get("generation_status", "pending")

        # Get pipeline steps for detailed progress
        stmt = (
            select(PipelineStepModel)
            .where(PipelineStepModel.video_generation_id == video_generation_id)
            .order_by(PipelineStepModel.step_order)
        )
        result = await session.exec(stmt)
        pipeline_steps = [step.model_dump() for step in result.all()]

        # Initialize step progress tracking
        step_progress = {
            "image_generation": {"status": "pending", "progress": 0},
            "audio_generation": {"status": "pending", "progress": 0},
            "video_generation": {"status": "pending", "progress": 0},
            "audio_video_merge": {"status": "pending", "progress": 0},
        }

        # Map pipeline steps to progress tracking
        for step in pipeline_steps:
            step_name = step.get("step_name", "").lower()
            step_status = step.get("status", "pending")

            if "image" in step_name:
                step_progress["image_generation"]["status"] = step_status
                step_progress["image_generation"]["progress"] = (
                    100 if step_status == "completed" else 50
                )
            elif "audio" in step_name:
                step_progress["audio_generation"]["status"] = step_status
                step_progress["audio_generation"]["progress"] = (
                    100 if step_status == "completed" else 50
                )
            elif "video" in step_name and "merge" not in step_name:
                step_progress["video_generation"]["status"] = step_status
                step_progress["video_generation"]["progress"] = (
                    100 if step_status == "completed" else 50
                )
            elif "merge" in step_name:
                step_progress["audio_video_merge"]["status"] = step_status
                step_progress["audio_video_merge"]["progress"] = (
                    100 if step_status == "completed" else 50
                )

        # Determine current step based on overall status
        current_step = "pending"
        if overall_status == "generating_audio":
            current_step = "audio_generation"
        elif overall_status == "generating_images":
            current_step = "image_generation"
        elif overall_status == "generating_video":
            current_step = "video_generation"
        elif overall_status == "merging_audio":
            current_step = "audio_video_merge"
        elif overall_status == "completed":
            current_step = "completed"
        elif overall_status == "failed":
            current_step = "failed"

        # Calculate overall progress percentage
        completed_steps = sum(
            1 for step in step_progress.values() if step["status"] == "completed"
        )
        total_steps = len(step_progress)
        progress_percentage = (
            int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        )

        # Check for active Celery tasks
        celery_task_info = await get_celery_task_status(video_data, session)

        # Build comprehensive response
        response_data = {
            "status": overall_status,
            "current_step": current_step,
            "progress_percentage": progress_percentage,
            "steps": step_progress,
            "error": video_data.get("error_message"),
            "video_url": video_data.get("video_url"),
            "created_at": video_data.get("created_at"),
            "updated_at": video_data.get("updated_at"),
            "celery_task": celery_task_info,
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting video generation polling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_celery_task_status(video_data: dict, session: AsyncSession) -> dict:
    """Get Celery task status information"""
    try:
        task_info = {"task_id": None, "task_state": None, "eta": None, "result": None}

        # Check for task IDs in metadata or direct fields
        task_metadata = video_data.get("task_metadata", {})
        audio_task_id = task_metadata.get("audio_task_id") or video_data.get(
            "audio_task_id"
        )
        image_task_id = task_metadata.get("image_task_id")
        video_task_id = task_metadata.get("video_task_id")
        merge_task_id = task_metadata.get("merge_task_id")

        # Use the most relevant task ID based on current status
        current_status = video_data.get("generation_status", "pending")
        task_id = None

        if current_status == "generating_audio" and audio_task_id:
            task_id = audio_task_id
        elif current_status == "generating_images" and image_task_id:
            task_id = image_task_id
        elif current_status == "generating_video" and video_task_id:
            task_id = video_task_id
        elif current_status == "merging_audio" and merge_task_id:
            task_id = merge_task_id

        if task_id:
            try:
                from app.tasks.celery_app import celery_app

                task_result = celery_app.AsyncResult(task_id)

                task_info.update(
                    {
                        "task_id": task_id,
                        "task_state": task_result.state,
                        "eta": getattr(task_result, "eta", None),
                        "result": (
                            str(task_result.result) if task_result.result else None
                        ),
                    }
                )

                # If task failed, update error information
                if task_result.state == "FAILURE":
                    task_info["error"] = str(task_result.result)

            except Exception as task_error:
                print(f"Error checking Celery task status: {task_error}")
                task_info["error"] = f"Failed to check task status: {str(task_error)}"

        return task_info

    except Exception as e:
        print(f"Error in get_celery_task_status: {e}")
        return {"error": str(e)}


@router.post("/video/retry/{task_id}")
async def retry_video_retrieval(
    task_id: str,
    video_url: str = Body(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
):
    """Retry video retrieval for a failed video generation task"""
    try:
        print(f"🔄 Starting video retrieval retry for task: {task_id}")

        # Verify task access
        stmt = select(VideoGeneration).where(
            VideoGeneration.id == task_id, VideoGeneration.user_id == current_user.id
        )
        result = await session.exec(stmt)
        task_response = result.first()

        if not task_response:
            raise HTTPException(
                status_code=404, detail="Video generation task not found"
            )

        task_data = task_response.model_dump()
        current_status = task_data.get("generation_status")

        # Check if this task is eligible for retry
        if current_status not in ["video_completed", "failed", "retrieval_failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry video retrieval. Current status: {current_status}",
            )

        # Check retry count
        retry_count = task_data.get("retry_count", 0)
        max_retries = 3

        if retry_count >= max_retries:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum retry attempts ({max_retries}) exceeded",
            )

        # Get video URL from request or task data
        if not video_url:
            # Try to get video URL from task metadata
            task_metadata = task_data.get("task_metadata", {})
            video_url = task_metadata.get("future_links_url") or task_metadata.get(
                "video_url"
            )

            if not video_url:
                raise HTTPException(
                    status_code=400,
                    detail="No video URL available for retry. Please provide a video_url parameter.",
                )

        print(f"🔄 Attempting video retrieval from URL: {video_url}")

        # Import and use the video service for retry
        from app.core.services.modelslab_v7_video import ModelsLabV7VideoService

        video_service = ModelsLabV7VideoService()

        # Attempt video retrieval
        retry_result = await video_service.retry_video_retrieval(video_url)

        if not retry_result.get("success"):
            # Update retry count and status
            new_retry_count = retry_count + 1
            task_response.retry_count = new_retry_count
            task_response.last_retry_at = datetime.now()
            task_response.generation_status = (
                "retrieval_failed" if new_retry_count < max_retries else "failed"
            )
            task_response.error_message = retry_result.get(
                "error", "Video retrieval failed"
            )
            task_response.can_resume = new_retry_count < max_retries

            session.add(task_response)
            await session.commit()

            raise HTTPException(
                status_code=500,
                detail=f"Video retrieval failed: {retry_result.get('error', 'Unknown error')}",
            )

        # Success - update task with video URL and mark as completed
        video_url = retry_result.get("video_url")
        video_duration = retry_result.get("duration", 0)

        task_response.generation_status = "completed"
        task_response.video_url = video_url
        task_response.retry_count = retry_count + 1
        task_response.last_retry_at = datetime.now()
        task_response.error_message = None
        task_response.can_resume = False

        # Update metadata
        metadata = task_data.get("task_metadata", {})
        metadata.update(
            {
                "retry_success": True,
                "retry_video_url": video_url,
                "video_duration": video_duration,
                "final_retrieval_time": datetime.now().isoformat(),
            }
        )
        task_response.task_meta = metadata

        session.add(task_response)
        await session.commit()

        print(f"✅ Video retrieval retry successful for task: {task_id}")

        return {
            "success": True,
            "message": "Video retrieval successful",
            "video_url": video_url,
            "duration": video_duration,
            "retry_count": retry_count + 1,
            "task_id": task_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in video retrieval retry: {e}")
        import traceback

        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
