from datetime import datetime
from typing import Optional
import re
from fastapi import APIRouter, Depends, HTTPException, Body
from app.schemas.video import VideoGenerationRequest, VideoGenerationResponse
from app.services.character_service import CharacterService
from app.services.plot_service import PlotService
from supabase import Client
import time

from app.schemas import AIRequest, AIResponse, QuizGenerationRequest, User, AnalyzeChapterSafetyRequest
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.video_service import VideoService
from app.services.rag_service import RAGService
from app.services.elevenlabs_service import ElevenLabsService
from app.services.embeddings_service import EmbeddingsService
from app.core.database import get_supabase
from app.core.auth import get_current_active_user
from app.services.pipeline_manager import PipelineManager, PipelineStep
from app.services.deepseek_script_service import DeepSeekScriptService
from app.services.openrouter_service import OpenRouterService, ModelTier
from app.services.subscription_manager import SubscriptionManager


def parse_scene_descriptions(analysis_result: str) -> list:
    """Parse scene descriptions from AI analysis result with improved logic"""
    scene_descriptions = []

    # Split by common scene delimiters
    lines = analysis_result.split('\n')

    current_scene = ""
    for line in lines:
        line = line.strip()

        # Look for scene markers (Scene 1:, Scene One:, SCENE 1:, etc.)
        scene_match = re.match(r'^(?:Scene\s+|SCENE\s+|scene\s+)(\d+|[A-Za-z]+)\s*:\s*(.+)$', line, re.IGNORECASE)

        if scene_match:
            # Save previous scene if it exists
            if current_scene and len(current_scene) > 20:
                scene_descriptions.append(current_scene[:300])  # Limit length
            # Start new scene
            current_scene = scene_match.group(2) + ": " + scene_match.group(3)
        elif line and len(line) > 10:
            # Continue building current scene
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


def extract_characters(character_details: str, script_style: str = "cinematic_movie") -> list:
    """Extract character names from character analysis with improved logic and script style filtering"""
    characters = []

    # Look for patterns like "Character Name: description" or "Name - role"
    character_patterns = [
        r'^([A-Z][a-zA-Z\s]+?)\s*:\s*.+$',  # Name: description
        r'^([A-Z][a-zA-Z\s]+?)\s*-\s*.+$',   # Name - role
        r'^([A-Z][a-zA-Z\s]+?)\s*\([^)]+\)', # Name (role)
    ]

    lines = character_details.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        for pattern in character_patterns:
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                char_name = match.group(1).strip()
                # Clean up the name (remove extra spaces, titles, etc.)
                char_name = re.sub(r'\s+', ' ', char_name)
                if len(char_name) > 1 and char_name not in characters:
                    characters.append(char_name)
                break

    # Fallback: extract capitalized words if no structured characters found
    if not characters:
        potential_chars = re.findall(r'\b[A-Z][a-zA-Z]+\b', character_details)
        # Filter out common non-character words
        exclude_words = {'The', 'And', 'But', 'For', 'Are', 'With', 'This', 'That', 'From', 'They', 'Will', 'Have', 'Been', 'One', 'Two', 'Three'}
        characters = [char for char in potential_chars if char not in exclude_words]

    # Filter characters based on script style for frontend selection
    if script_style == "cinematic_narration":
        # For narration scripts, exclude narrator-like entities that aren't speaking characters
        narrator_indicators = ['narrator', 'voice', 'speaker', 'announcer']
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
    valid_styles = ["cinematic", "narration", "educational", "marketing"]
    if script_style not in valid_styles:
        # Default to cinematic if invalid
        return "cinematic"
    return script_style


def get_available_script_styles() -> dict:
    """Get available script styles with descriptions"""
    return {
        "cinematic": {
            "name": "Cinematic",
            "description": "Professional screenplay format with scene headings, character names, and visual descriptions",
            "best_for": "Video production, storytelling, dramatic content"
        },
        "narration": {
            "name": "Narration",
            "description": "Rich voice-over script with descriptive language and atmospheric elements",
            "best_for": "Audiobooks, documentaries, explanatory videos"
        },
        "educational": {
            "name": "Educational",
            "description": "Clear, structured learning content with step-by-step explanations",
            "best_for": "Tutorials, courses, training materials"
        },
        "marketing": {
            "name": "Marketing",
            "description": "Compelling promotional content with hooks and calls-to-action",
            "best_for": "Advertisements, product demos, promotional videos"
        }
    }


async def enhance_with_plot_context(supabase_client: Client, user_id: str, book_id: str, chapter_content: str) -> dict:
    """Enhanced plot context integration for script generation"""
    try:
        plot_service = PlotService(supabase_client)
        plot_overview = await plot_service.get_plot_overview(
            user_id=user_id,
            book_id=book_id
        )

        if not plot_overview:
            return {"enhanced_content": None, "plot_info": None}

        # Get characters for this plot
        character_service = CharacterService(supabase_client)
        characters = await character_service.get_characters_by_plot(
            plot_overview.id, user_id
        )

        # Build comprehensive plot context
        plot_context_parts = []

        # Plot overview section
        plot_context_parts.append("PLOT OVERVIEW:")
        if plot_overview.logline:
            plot_context_parts.append(f"Logline: {plot_overview.logline}")
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
            plot_context_parts.append(f"Target Audience: {plot_overview.target_audience}")

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
                plot_context_parts.append(f"Conflict Type: {plot_overview.conflict_type}")
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
                "character_count": len(characters) if characters else 0
            }
        }

    except Exception as e:
        print(f"Error in enhance_with_plot_context: {str(e)}")
        return {"enhanced_content": None, "plot_info": None}


router = APIRouter()

@router.post("/generate-text", response_model=AIResponse)
async def generate_text(
    request: AIRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate quiz using AI service"""
    ai_service = AIService()
    quiz = await ai_service.generate_quiz(request.chapter_content, request.difficulty)
    return quiz

@router.post("/generate-voice")
async def generate_voice(
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate voice using ElevenLabs service"""
    voice_service = VoiceService()
    voice_url = await voice_service.generate_voice(text, voice_id)
    return {"voice_url": voice_url}

# New RAG-based video generation endpoints
@router.post("/generate-video-from-chapter")
async def generate_video_from_chapter(
    chapter_id: str,
    video_style: str = "realistic",
    include_context: bool = True,
    include_audio_enhancement: bool = True,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate video from chapter using RAG system with ElevenLabs audio enhancement"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Generate video using RAG-enhanced service with audio enhancement
        video_service = VideoService(supabase_client)
        video_result = await video_service.generate_video_from_chapter(
            chapter_id=chapter_id,
            video_style=video_style,
            include_context=include_context,
            include_audio_enhancement=include_audio_enhancement,
            supabase_client=supabase_client
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate tutorial video from chapter using RAG system"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Generate tutorial video
        video_service = VideoService(supabase_client)
        video_result = await video_service.generate_tutorial_video(
            chapter_id=chapter_id,
            video_style=video_style,
            supabase_client=supabase_client
        )
        
        if not video_result:
            raise HTTPException(status_code=500, detail="Failed to generate tutorial video")
        
        return video_result
        
    except Exception as e:
        print(f"Error generating tutorial video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
@router.post("/generate-entertainment-video", response_model=VideoGenerationResponse)
async def generate_entertainment_video(
    request: VideoGenerationRequest, 
    # request: dict = Body(...),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
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
        script_response = supabase_client.table('scripts')\
            .select('*')\
            .eq('chapter_id', chapter_id)\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not script_response.data:
            raise HTTPException(
                status_code=400, 
                detail="No script found for this chapter. Please generate script first using 'Generate Script & Scene'."
            )
        
        script_data = script_response.data[0]

        # Step 2: Create video generation record
        print(f"[VIDEO GEN DEBUG] Creating video generation with chapter_id: {chapter_id}, script_id: {script_data['id']}, user_id: {current_user['id']}")
        video_generation = supabase_client.table('video_generations').insert({
            'chapter_id': chapter_id,
            'script_id': script_data['id'],
            'user_id': current_user['id'],
            'generation_status': 'pending',
            'quality_tier': quality_tier,
            'can_resume': True,  # ✅ Add this field
            'retry_count': 0,    # ✅ Add this field
            'script_data': {
                'script': script_data['script'],
                'scene_descriptions': script_data['scene_descriptions'],
                'characters': script_data['characters'],
                'script_style': script_data['script_style'],  # Preserve original style
                'video_style': video_style  # New: visual styling for video generation
            }
        }).execute()

        video_gen_id = video_generation.data[0]['id']
        
        try:
            # Step 3: Check for pre-generated audio first
            print(f"🔍 Checking for pre-generated audio for chapter: {chapter_id}")

            # Check for existing audio in audio_generations table
            print(f"[AUDIO QUERY DEBUG] Querying audio_generations with:")
            print(f"  chapter_id: {chapter_id}")
            print(f"  user_id: {current_user['id']}")
            print(f"  generation_status: completed (using 'generation_status' column)")

            audio_response = supabase_client.table('audio_generations')\
                .select('*')\
                .eq('chapter_id', chapter_id)\
                .eq('user_id', current_user['id'])\
                .eq('generation_status', 'completed')\
                .execute()

            print(f"[AUDIO QUERY DEBUG] Raw response: {audio_response.data}")
            if audio_response.data:
                for idx, record in enumerate(audio_response.data):
                    print(f"[AUDIO QUERY DEBUG] Record {idx}: keys={list(record.keys())}")
                    print(f"[AUDIO QUERY DEBUG] Record {idx}: status={record.get('status')}, generation_status={record.get('generation_status')}")
            else:
                print("[AUDIO QUERY DEBUG] No records found.")

            existing_audio = []
            audio_by_type = {
                'narrator': [],
                'characters': [],
                'sound_effects': [],
                'background_music': []
            }

            if audio_response.data:
                for audio_record in audio_response.data:
                    audio_type = audio_record.get('audio_type', 'narrator')
                    # Map database fields to expected format
                    audio_data = {
                        'id': audio_record['id'],
                        'url': audio_record['audio_url'],
                        'audio_url': audio_record['audio_url'],
                        'duration': audio_record.get('duration', 0),
                        'file_name': audio_record.get('text_content', ''),
                        'scene_number': audio_record.get('sequence_order', 0),
                        'character_name': audio_record.get('metadata', {}).get('character_name'),
                        'volume': 1.0
                    }

                    # Categorize by type
                    if audio_type == 'narrator':
                        audio_by_type['narrator'].append(audio_data)
                    elif audio_type == 'character':
                        audio_by_type['characters'].append(audio_data)
                    elif audio_type in ['sfx', 'sound_effect']:
                        audio_by_type['sound_effects'].append(audio_data)
                    elif audio_type == 'music':
                        audio_by_type['background_music'].append(audio_data)

                    existing_audio.append(audio_data)

            print(f"📊 Found {len(existing_audio)} pre-generated audio files")

            if existing_audio:
                # Use pre-generated audio - skip audio generation
                print(f"✅ Using pre-generated audio, skipping audio generation step")

                # Organize audio by type for storage
                audio_by_type = {
                    'narrator': [],
                    'characters': [],
                    'sound_effects': [],
                    'background_music': []
                }

                for audio_file in existing_audio:
                    audio_type = audio_file.get('audio_type', 'narrator')
                    audio_by_type[audio_type].append({
                        'id': audio_file['id'],
                        'url': audio_file['audio_url'],
                        'duration': audio_file.get('duration', 0),
                        'name': audio_file.get('file_name', ''),
                        'scene_number': audio_file.get('scene_number', 0),
                        'character': audio_file.get('character_name'),
                        'volume': audio_file.get('volume', 1.0)
                    })

                # Check for pre-generated images from image_generations table
                existing_images = []
                image_by_type = {
                    'character_images': [],
                    'scene_images': []
                }

                # Query image_generations table for images associated with this chapter
                images_response = supabase_client.table('image_generations')\
                    .select('*')\
                    .eq('user_id', current_user['id'])\
                    .eq('status', 'completed')\
                    .execute()

                if images_response.data:
                    for img in images_response.data:
                        metadata = img.get('metadata', {})
                        # Check if image is associated with this chapter
                        if metadata.get('chapter_id') == chapter_id:
                            image_type = metadata.get('image_type', 'scene')
                            image_data = {
                                'id': img['id'],
                                'url': img['image_url'],
                                'image_url': img['image_url'],
                                'prompt': img.get('image_prompt', ''),
                                'created_at': img['created_at']
                            }

                            if image_type == 'character':
                                image_data['character_name'] = metadata.get('character_name', '')
                                image_by_type['character_images'].append(image_data)
                            elif image_type == 'scene':
                                image_data['scene_number'] = metadata.get('scene_number', 0)
                                image_by_type['scene_images'].append(image_data)

                            existing_images.append(image_data)

                print(f"📊 Found {len(existing_images)} pre-generated images")

                # Store pre-generated audio and images in video generation record
                supabase_client.table('video_generations').update({
                    'audio_files': audio_by_type,
                    'image_data': {
                        'images': image_by_type,
                        'statistics': {
                            'total_images': len(existing_images),
                            'character_images': len(image_by_type['character_images']),
                            'scene_images': len(image_by_type['scene_images'])
                        }
                    },
                    'generation_status': 'images_completed',  # Skip to next step assuming images are pre-generated
                    'task_metadata': {
                        'audio_source': 'pre_generated',
                        'image_source': 'pre_generated',
                        'audio_files_count': len(existing_audio),
                        'image_files_count': len(existing_images),
                        'started_at': datetime.now().isoformat()
                    }
                }).eq('id', video_gen_id).execute()

                # ✅ FIXED: Queue video generation task since we have pre-generated assets
                print(f"🎬 Queuing video generation task for video: {video_gen_id}")
                from app.tasks.video_tasks import generate_all_videos_for_generation
                task = generate_all_videos_for_generation.delay(video_gen_id)
                print(f"✅ Video generation task queued successfully: {task.id}")

            else:
                raise HTTPException(status_code=400, detail="Can't find pre-generated audio and stop the video generation")
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
            
            supabase_client.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': f"Failed to start audio generation: {str(e)}"
            }).eq('id', video_gen_id).execute()
            
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
            script_id=script_data['id'],
            status=status,
            audio_task_id=audio_task_id,
            task_status=task_status,
            message=message,
            script_info={
                "script_style": script_data['script_style'],
                "video_style": video_style,  # ✅ Now this works
                "scenes": len(script_data.get('scene_descriptions', [])),
                "characters": len(script_data.get('characters', [])),
                "created_at": script_data['created_at']
            }
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get video generation status with detailed progress"""
    try:
        response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        data = response.data
        status = data['generation_status']
        
        task_metadata = data.get('task_metadata', {})
        audio_task_id = task_metadata.get('audio_task_id') or data.get('audio_task_id')
        
        if audio_task_id and status in ['generating_audio', 'pending']:
            try:
                from app.tasks.celery_app import celery_app
                task_result = celery_app.AsyncResult(audio_task_id)
                
                if task_result.state == 'SUCCESS':
                    # Task completed but DB not updated yet
                    status = 'audio_completed'
                elif task_result.state == 'FAILURE':
                    status = 'failed'
                    data['error_message'] = str(task_result.result)
                elif task_result.state == 'PENDING':
                    status = 'generating_audio'
                
                # Add task info to response
                data['task_info'] = {
                    'task_id': audio_task_id,
                    'task_state': task_result.state,
                    'task_result': str(task_result.result) if task_result.result else None
                }
            except Exception as e:
                print(f"Error checking task status: {e}")
        
        # Base response
        result = {
            'status': status,
            'generation_status': status, 
            'quality_tier': data['quality_tier'],
            'video_url': data.get('video_url'),
            'created_at': data['created_at'],
            'script_id': data.get('script_id'),
            'error_message': data.get('error_message')
        }
        
        # Add audio information if available
        if data.get('audio_files'):
            audio_data = data['audio_files']
            result['audio_progress'] = {
                'narrator_files': len(audio_data.get('narrator', [])),
                'character_files': len(audio_data.get('characters', [])),
                'sound_effects': len(audio_data.get('sound_effects', [])),
                'background_music': len(audio_data.get('background_music', []))
            }
            
        # Add task info if available
        if 'task_info' in data:
            result['task_info'] = data['task_info']
        
        # Add image information if available
        if data.get('image_data'):
            image_data = data['image_data']
            result['image_progress'] = image_data.get('statistics', {})
            
            # Include character images for frontend display
            if status in ['images_completed', 'generating_video', 'completed']:
                character_images = image_data.get('character_images', [])
                result['character_images'] = [
                    img for img in character_images if img is not None
                ]
        
        #  Add video information if available
        if data.get('video_data'):
            video_data = data['video_data']
            result['video_progress'] = video_data.get('statistics', {})
            
            # Include scene videos for frontend display
            if status in ['video_completed', 'merging_audio', 'completed']:
                scene_videos = video_data.get('scene_videos', [])
                result['scene_videos'] = [
                    video for video in scene_videos if video is not None
                ]
        
        # Add merge information if available
        if data.get('merge_data'):
            merge_data = data['merge_data']
            result['merge_progress'] = merge_data.get('merge_statistics', {})
            
            # Include final video information if completed
            if status == 'completed':
                result['final_video_ready'] = True
                result['merge_details'] = {
                    'processing_time': merge_data.get('merge_statistics', {}).get('processing_time', 0),
                    'file_size_mb': merge_data.get('merge_statistics', {}).get('file_size_mb', 0),
                    'scenes_merged': merge_data.get('merge_statistics', {}).get('total_scenes_merged', 0),
                    'audio_tracks_mixed': merge_data.get('merge_statistics', {}).get('audio_tracks_mixed', 0)
                }
        
         # ✅ NEW: Add lip sync information if available
        if data.get('lipsync_data'):
            lipsync_data = data['lipsync_data']
            result['lipsync_progress'] = lipsync_data.get('statistics', {})
            
            # Include lip sync details if completed
            if status in ['lipsync_completed', 'completed']:
                result['lipsync_completed'] = True
                result['lipsync_details'] = {
                    'characters_lip_synced': lipsync_data.get('statistics', {}).get('characters_lip_synced', 0),
                    'scenes_processed': lipsync_data.get('statistics', {}).get('total_scenes_processed', 0),
                    'processing_method': lipsync_data.get('statistics', {}).get('processing_method', 'unknown')
                }
                
                # Include lip synced scenes
                lip_synced_scenes = lipsync_data.get('lip_synced_scenes', [])
                result['lip_synced_scenes'] = [
                    scene for scene in lip_synced_scenes if scene is not None
                ]
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chapter-video-generations/{chapter_id}")
async def get_chapter_video_generations(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get all video generations for a chapter"""
    try:
        print(f"🔍 DEBUG: Getting video generations for chapter: {chapter_id}")
        print(f"🔍 DEBUG: User ID: {current_user.get('id', 'Unknown')}")
        
        # First check if chapter exists
        chapter_check = supabase_client.table('chapters')\
            .select('id, title')\
            .eq('id', chapter_id)\
            .execute()
        
        print(f"🔍 DEBUG: Chapter found: {len(chapter_check.data or [])}")
        
        
        response = supabase_client.table('video_generations')\
            .select('*')\
            .eq('chapter_id', chapter_id)\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .execute()
            
        print(f"🔍 DEBUG: Video generations found: {len(response.data or [])}")
        
        
        generations = []
        for gen in response.data or []:
            # Add pipeline status for each generation
            try:
                pipeline_manager = PipelineManager()
                pipeline_status = pipeline_manager.get_pipeline_status(gen['id'])
                gen['pipeline_status'] = pipeline_status
                
                # Add retry capability flag
                gen['can_resume'] = (
                    gen.get('generation_status') in ['failed', 'audio_completed', 'images_completed', 'video_completed'] or
                    (pipeline_status and pipeline_status.get('can_resume', False))
                )
                
            except Exception as e:
                print(f"Error getting pipeline status for {gen['id']}: {e}")
                gen['pipeline_status'] = None
                gen['can_resume'] = gen.get('generation_status') == 'failed'
            
            generations.append(gen)
        
        result = {
            'chapter_id': chapter_id,
            'generations': generations,
            'total': len(generations)
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get scene videos for a video generation"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Get scene videos
        videos_response = supabase_client.table('video_segments')\
            .select('*')\
            .eq('video_generation_id', video_gen_id)\
            .eq('status', 'completed')\
            .order('scene_id')\
            .execute()
        
        scene_videos = []
        total_duration = 0.0
        
        for video in videos_response.data or []:
            # Calculate resolution from width and height
            width = video.get('width', 512)
            height = video.get('height', 288)
            resolution = f"{width}x{height}"
            
            scene_videos.append({
                'id': video['id'],
                'scene_id': video['scene_id'],
                'scene_description': video['scene_description'],
                'video_url': video['video_url'],
                'duration': video['duration_seconds'],
                'resolution': video['resolution'],
                'width': width,  # ✅ Include individual dimensions too
                'height': height,  # ✅ Include individual dimensions too
                'fps': video['fps'],
                'generation_method': video['generation_method'],
                'created_at': video['created_at']
            })
            total_duration += video['duration_seconds']
        
        return {
            'video_generation_id': video_gen_id,
            'scene_videos': scene_videos,
            'total_scenes': len(scene_videos),
            'total_duration': total_duration
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Add this new endpoint after get_scene_videos function (around line 380):

@router.get("/final-video/{video_gen_id}")
async def get_final_video(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get final merged video for a video generation"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        data = video_response.data
        
        if data['generation_status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail=f"Video generation not completed. Current status: {data['generation_status']}"
            )
        
        final_video_url = data.get('video_url')
        merge_data = data.get('merge_data', {})
        
        if not final_video_url:
            raise HTTPException(status_code=404, detail="Final video not found")
        
        return {
            'video_generation_id': video_gen_id,
            'final_video_url': final_video_url,
            'status': 'completed',
            'merge_statistics': merge_data.get('merge_statistics', {}),
            'quality_versions': merge_data.get('quality_versions', []),
            'processing_details': merge_data.get('processing_details', {})
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/merge-status/{video_gen_id}")
async def get_merge_status(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed merge status and progress"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        data = video_response.data
        status = data['generation_status']
        merge_data = data.get('merge_data', {})
        
        result = {
            'video_generation_id': video_gen_id,
            'merge_status': status,
            'is_merging': status == 'merging_audio',
            'is_completed': status == 'completed',
            'final_video_url': data.get('video_url'),
            'error_message': data.get('error_message')
        }
        
        # Add merge statistics if available
        if merge_data:
            result['merge_statistics'] = merge_data.get('merge_statistics', {})
            result['processing_details'] = merge_data.get('processing_details', {})
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Add these new endpoints after get_merge_status function (around line 450):

@router.get("/lip-sync-status/{video_gen_id}")
async def get_lip_sync_status(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed lip sync status and progress"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        data = video_response.data
        status = data['generation_status']
        lipsync_data = data.get('lipsync_data', {})
        
        result = {
            'video_generation_id': video_gen_id,
            'lipsync_status': status,
            'is_applying_lipsync': status == 'applying_lipsync',
            'is_lipsync_completed': status in ['lipsync_completed', 'completed'],
            'error_message': data.get('error_message')
        }
        
        # Add lip sync statistics if available
        if lipsync_data:
            result['lipsync_statistics'] = lipsync_data.get('statistics', {})
            result['lip_synced_scenes'] = lipsync_data.get('lip_synced_scenes', [])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lip-synced-videos/{video_gen_id}")
async def get_lip_synced_videos(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get lip synced scene videos for a video generation"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Get lip synced video segments
        lipsync_response = supabase_client.table('video_segments')\
            .select('*')\
            .eq('video_generation_id', video_gen_id)\
            .eq('generation_method', 'lip_sync')\
            .eq('status', 'completed')\
            .order('scene_id')\
            .execute()
        
        lip_synced_videos = []
        total_duration = 0.0
        
        for video in lipsync_response.data or []:
            metadata = video.get('metadata', {})
            lip_synced_videos.append({
                'id': video['id'],
                'scene_id': video['scene_id'],
                'original_video_url': metadata.get('original_video_url'),
                'lipsync_video_url': video['video_url'],
                'duration': video['duration_seconds'],
                'characters_processed': metadata.get('characters_processed', []),
                'faces_detected': metadata.get('faces_detected', 0),
                'processing_model': video['processing_model'],
                'created_at': video['created_at']
            })
            total_duration += video['duration_seconds']
        
        return {
            'video_generation_id': video_gen_id,
            'lip_synced_videos': lip_synced_videos,
            'total_scenes': len(lip_synced_videos),
            'total_duration': total_duration,
            'characters_with_lipsync': len(set([
                char for video in lip_synced_videos 
                for char in video.get('characters_processed', [])
            ]))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trigger-lip-sync/{video_gen_id}")
async def trigger_lip_sync_manually(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Manually trigger lip sync processing for a video generation"""
    try:
        # Verify access and status
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        data = video_response.data
        status = data['generation_status']
        
        # Check if lip sync can be applied
        if status not in ['video_completed', 'completed', 'lipsync_failed']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot apply lip sync. Current status: {status}. Video generation must be completed first."
            )
        
        # Check if character dialogue exists
        audio_files = data.get('audio_files', {})
        character_audio = audio_files.get('characters', [])
        
        if not character_audio:
            raise HTTPException(
                status_code=400,
                detail="No character dialogue found. Lip sync requires character audio."
            )
        
        # Trigger lip sync task
        from app.tasks.lipsync_tasks import apply_lip_sync_to_generation
        task = apply_lip_sync_to_generation.delay(video_gen_id)
        
        return {
            'message': 'Lip sync processing started',
            'task_id': task.id,
            'video_generation_id': video_gen_id,
            'character_dialogues': len(character_audio)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/script-styles")
async def get_script_styles():
    """Get available script styles with descriptions"""
    return {
        "styles": get_available_script_styles(),
        "default": "cinematic"
    }

@router.get("/scripts/{chapter_id}")
async def list_chapter_scripts(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """List all scripts for a chapter by current user"""
    try:
        scripts = supabase_client.table('scripts')\
            .select('*')\
            .eq('chapter_id', chapter_id)\
            .eq('user_id', current_user['id'])\
            .order('created_at', desc=True)\
            .execute()

        return {
            'chapter_id': chapter_id,
            'scripts': scripts.data or []
        }

    except Exception as e:
        print(f"Error listing scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/script/{script_id}")
async def get_script_details(
    script_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed script information"""
    try:
        script = supabase_client.table('scripts')\
            .select('*')\
            .eq('id', script_id)\
            .eq('user_id', current_user['id'])\
            .single().execute()
        
        if not script.data:
            raise HTTPException(status_code=404, detail="Script not found")
        
        return script.data
        
    except Exception as e:
        print(f"Error getting script details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# get_character_images endpoint:

@router.get("/character-images/{video_gen_id}")
async def get_character_images(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get character images for a video generation"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        # Get character images
        images_response = supabase_client.table('image_generations')\
            .select('*')\
            .eq('video_generation_id', video_gen_id)\
            .eq('image_type', 'character')\
            .eq('status', 'completed')\
            .execute()
        
        character_images = []
        for img in images_response.data or []:
            character_images.append({
                'id': img['id'],
                'character_name': img['character_name'],
                'image_url': img['image_url'],
                'prompt': img['image_prompt'],
                'created_at': img['created_at']
            })
        
        return {
            'video_generation_id': video_gen_id,
            'character_images': character_images,
            'total_characters': len(character_images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-video-avatar")
async def generate_video_avatar(
    chapter_id: str,
    avatar_style: str = "realistic",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate video avatar from chapter content"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Generate video avatar
        video_service = VideoService(supabase_client)
        avatar_result = await video_service.generate_story_scene(
            scene_description=chapter_data['title'],
            dialogue=chapter_data['content'][:500],
            avatar_style=avatar_style
        )
        
        if not avatar_result:
            raise HTTPException(status_code=500, detail="Failed to generate video avatar")
        
        return avatar_result
        
    except Exception as e:
        print(f"Error generating video avatar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New PlotDrive enhancement endpoints
@router.post("/enhance-entertainment-content")
async def enhance_entertainment_content(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Enhance entertainment content using PlotDrive service"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Enhance content using RAG service with PlotDrive
        rag_service = RAGService(supabase_client)
        chapter_context = await rag_service.get_chapter_with_context(chapter_id, include_adjacent=True)
        
        if not chapter_context:
            raise HTTPException(status_code=404, detail="Could not retrieve chapter context")
        
        enhancement = await rag_service.enhance_entertainment_content(chapter_context)
        
        return {
            'chapter_id': chapter_id,
            'enhancement': enhancement
        }
        
    except Exception as e:
        print(f"Error enhancing entertainment content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-screenplay")
async def generate_screenplay(
    chapter_id: str,
    style: str = "realistic",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate screenplay using RAG service with PlotDrive"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Generate screenplay using RAG service with PlotDrive
        rag_service = RAGService(supabase_client)
        chapter_context = await rag_service.get_chapter_with_context(chapter_id, include_adjacent=True)
        
        if not chapter_context:
            raise HTTPException(status_code=404, detail="Could not retrieve chapter context")
        
        screenplay = await rag_service._generate_entertainment_script(chapter_context, style)
        
        return {
            'chapter_id': chapter_id,
            'screenplay': screenplay,
            'style': style
        }
        
    except Exception as e:
        print(f"Error generating screenplay: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New embeddings management endpoints
@router.post("/create-chapter-embeddings")
async def create_chapter_embeddings(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Create vector embeddings for a chapter"""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Create embeddings
        embeddings_service = EmbeddingsService(supabase_client)
        success = await embeddings_service.create_chapter_embeddings(
            chapter_id=chapter_id,
            content=chapter_data['content']
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Create vector embeddings for a book"""
    try:
        # Verify book access
        book_response = supabase_client.table('books').select('*').eq('id', book_id).single().execute()
        if not book_response.data:
            raise HTTPException(status_code=404, detail="Book not found")
        
        book_data = book_response.data
        
        # Check access permissions
        if book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this book")
        
        # Create embeddings
        embeddings_service = EmbeddingsService(supabase_client)
        success = await embeddings_service.create_book_embeddings(
            book_id=book_id,
            title=book_data['title'],
            description=book_data.get('description'),
            content=book_data.get('content')
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Search for similar content using vector embeddings"""
    try:
        embeddings_service = EmbeddingsService(supabase_client)
        results = await embeddings_service.search_similar_chapters(
            query=query,
            book_id=book_id,
            limit=limit
        )
        
        return {
            'query': query,
            'results': results,
            'total_results': len(results)
        }
        
    except Exception as e:
        print(f"Error searching similar content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search-similar-books")
async def search_similar_books(
    query: str,
    limit: int = 5,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Search for similar books using vector embeddings"""
    try:
        embeddings_service = EmbeddingsService(supabase_client)
        results = await embeddings_service.search_similar_books(
            query=query,
            limit=limit
        )
        
        return {
            'query': query,
            'results': results,
            'total_results': len(results)
        }
        
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate enhanced speech with emotion and speed control"""
    try:
        elevenlabs_service = ElevenLabsService(supabase_client)
        result = await elevenlabs_service.generate_enhanced_speech(
            text=text,
            voice_id=voice_id,
            user_id=current_user['id'],
            emotion=emotion,
            speed=speed
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate sound effects"""
    try:
        elevenlabs_service = ElevenLabsService()
        audio_url = await elevenlabs_service.generate_sound_effect(
            effect_type=effect_type,
            duration=duration,
            intensity=intensity,
            user_id=current_user['id']
        )
        
        return {"audio_url": audio_url}
        
    except Exception as e:
        print(f"Error generating sound effects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-audio-narration")
async def generate_audio_narration(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate audio narration for learning content using RAG embeddings and ElevenLabs"""
    try:
        chapter_id = request.get("chapter_id")
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")
        
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Check if this is a learning book
        if book_data['book_type'] != 'learning':
            raise HTTPException(status_code=400, detail="Audio narration is only available for learning books")
        
        # Generate tutorial script using RAG and AI
        ai_service = AIService()
        
        # Create tutorial prompt based on chapter content
        tutorial_prompt = f"""
        Create an engaging audio tutorial script for the following learning content:
        
        Chapter Title: {chapter_data['title']}
        Chapter Content: {chapter_data['content'][:1000]}...
        
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
            raise HTTPException(status_code=500, detail="Failed to generate tutorial script")
        
        # Generate audio using ElevenLabs
        elevenlabs_service = ElevenLabsService(supabase_client)
        
        audio_result = await elevenlabs_service.create_audio_narration(
            text=tutorial_script,
            narrator_style="professional",
            user_id=current_user['id']
        )
        
        if not audio_result:
            raise HTTPException(status_code=500, detail="Failed to generate audio narration")
        
        # Store the result in database (optional)
        audio_record = {
            "chapter_id": chapter_id,
            "book_id": book_data['id'],
            "user_id": current_user['id'],
            "content_type": "audio_narration",
            "content_url": audio_result,
            "script": tutorial_script,
            "duration": 180,  # Default 3 minutes
            "status": "ready"
        }
        
        supabase_client.table('learning_content').insert(audio_record).execute()
        
        return {
            "id": f"audio_{int(time.time())}",
            "audio_url": audio_result,
            "duration": 180,
            "status": "ready"
        }
        
    except Exception as e:
        print(f"Error generating audio narration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-realistic-video")
async def generate_realistic_video(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate realistic video tutorial using RAG embeddings and Tavus with enhanced error handling"""
    try:
        print(f"🎬 Starting realistic video generation for user: {current_user['id']}")
        
        chapter_id = request.get("chapter_id")
        if not chapter_id:
            print("❌ Missing chapter_id in request")
            raise HTTPException(status_code=400, detail="chapter_id is required")
        
        print(f"📖 Processing chapter: {chapter_id}")
        
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            print(f"❌ Chapter not found: {chapter_id}")
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        
        print(f"📚 Book: {book_data.get('title', 'Unknown')} (Type: {book_data.get('book_type', 'Unknown')})")
        
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            print(f"❌ Access denied for chapter: {chapter_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        
        # Check if this is a learning book
        if book_data['book_type'] != 'learning':
            print(f"❌ Book type '{book_data['book_type']}' is not supported for realistic video")
            raise HTTPException(status_code=400, detail="Realistic video is only available for learning books")
        
        # Generate tutorial script using RAG and AI
        ai_service = AIService()
        
        # Create tutorial prompt for video
        tutorial_prompt = f"""
        Create an engaging tutorial script for the following learning content:
        
        Chapter Title: {chapter_data['title']}
        Chapter Content: {chapter_data['content'][:1000]}...
        
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
            raise HTTPException(status_code=500, detail="Failed to generate tutorial script")
        
        print(f"✅ Tutorial script generated ({len(tutorial_script)} characters)")
        
        # Generate video using Tavus
        video_service = VideoService(supabase_client)
        
        # Store initial record with pending status
        initial_record = {
            "chapter_id": chapter_id,
            "book_id": book_data['id'],
            "user_id": current_user['id'],
            "content_type": "realistic_video",
            "content_url": None,
            "tavus_url": None,
            "tavus_video_id": None,
            "script": tutorial_script,
            "duration": 180,
            "status": "processing",
            "error_message": None
        }
        
        print(f"💾 Storing initial record in database...")
        db_result = supabase_client.table('learning_content').insert(initial_record).execute()
        content_id = db_result.data[0]['id'] if db_result.data else None
        
        if not content_id:
            print("❌ Failed to create database record")
            raise HTTPException(status_code=500, detail="Failed to create database record")
        
        print(f"✅ Database record created with ID: {content_id}")
        
        # Use Tavus directly with the tutorial script
        print(f"🎬 Calling Tavus API for video generation...")
        tavus_result = await video_service._generate_tavus_video(tutorial_script, "realistic", content_id, supabase_client)
        
        if not tavus_result:
            print("❌ Tavus video generation returned None")
            # Update record with failed status
            if content_id:
                supabase_client.table('learning_content').update({
                    "status": "failed",
                    "error_message": "Tavus video generation failed - no result returned"
                }).eq("id", content_id).execute()
            raise HTTPException(status_code=500, detail="Failed to generate realistic video - Tavus returned no result")
        
        print(f"✅ Tavus API call completed")
        print(f"📊 Tavus result status: {tavus_result.get('status', 'unknown')}")
        
        # Extract Tavus information
        tavus_video_id = tavus_result.get("video_id")
        tavus_url = tavus_result.get("hosted_url") or tavus_result.get("video_url")
        download_url = tavus_result.get("download_url")
        final_video_url = tavus_result.get("video_url") or tavus_result.get("download_url")
        
        print(f"🆔 Tavus Video ID: {tavus_video_id}")
        print(f"🌐 Tavus URL: {tavus_url}")
        print(f"🔗 Final Video URL: {final_video_url}")
        
        # Only set content_url if video is truly ready (downloadable URL present)
        update_data = {
            "tavus_url": tavus_url,
            "tavus_video_id": tavus_video_id,
            "status": "ready" if final_video_url else "processing"
        }
        if final_video_url:
            update_data["content_url"] = final_video_url
            update_data["duration"] = tavus_result.get("duration", 180)
        if content_id:
            print(f"💾 Updating database record with Tavus results...")
            supabase_client.table('learning_content').update(update_data).eq("id", content_id).execute()
        
        # Return response
        response_data = {
            "id": content_id or f"video_{int(time.time())}",
            "tavus_url": tavus_url,
            "tavus_video_id": tavus_video_id,
            "status": "ready" if final_video_url else "processing"
        }
        
        if final_video_url:
            response_data["video_url"] = final_video_url
            response_data["duration"] = tavus_result.get("duration", 180)
        elif tavus_url:
            # If we have a hosted_url but no final video_url, the video is still processing
            # but we can provide the hosted_url for immediate access
            response_data["hosted_url"] = tavus_url
            response_data["message"] = "Video is still processing. You can access it via the hosted URL or wait for completion."
        
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Analyze chapter content for potential KlingAI risk control issues"""
    try:
        # Get chapter details
        chapter_response = supabase_client.table("chapters").select("*").eq("id", request.chapter_id).execute()
        
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        chapter = chapter_response.data[0]
        chapter_content = chapter.get("content", "")
        chapter_title = chapter.get("title", "")
        
        # Analyze content safety
        video_service = VideoService(supabase_client)
        safety_analysis = video_service.analyze_chapter_content_safety(chapter_content, chapter_title)
        
        return {
            "success": True,
            "analysis": safety_analysis,
            "chapter_id": request.chapter_id,
            "chapter_title": chapter_title
        }
        
    except Exception as e:
        print(f"Error analyzing chapter safety: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing chapter safety: {str(e)}")

@router.get("/check-video-status/{content_id}")
async def check_video_status(
    content_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Check the status of video generation and handle completion"""
    try:
        content_response = supabase_client.table('learning_content').select('*').eq('id', content_id).single().execute()
        if not content_response.data:
            raise HTTPException(status_code=404, detail="Content not found")
        content_data = content_response.data
        if content_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
        # If status is already ready and content_url is present, return the data
        if content_data['status'] == 'ready' and content_data.get('content_url'):
            return {
                "id": content_id,
                "status": "ready",
                "video_url": content_data['content_url'],
                "tavus_url": content_data.get('tavus_url'),
                "duration": content_data.get('duration', 180)
            }
        # If status is processing and we have a Tavus video ID, check its status
        if content_data['status'] == 'processing' and content_data.get('tavus_video_id'):
            video_service = VideoService(supabase_client)
            tavus_status = await video_service._poll_video_status(
                content_data['tavus_video_id'],
                f"Video for content {content_id}"
            )
            if tavus_status['status'] in ['completed', 'ready']:
                video_url = tavus_status.get('video_url') or tavus_status.get('download_url')
                if video_url:
                    final_video_url = await video_service._download_and_store_video(
                        video_url,
                        f"video_{content_id}.mp4",
                        current_user['id']
                    )
                    supabase_client.table('learning_content').update({
                        "status": "ready",
                        "content_url": final_video_url,
                        "duration": tavus_status.get('duration', 180)
                    }).eq("id", content_id).execute()
                    return {
                        "id": content_id,
                        "status": "ready",
                        "video_url": final_video_url,
                        "tavus_url": content_data.get('tavus_url'),
                        "duration": tavus_status.get('duration', 180)
                    }
                else:
                    return {
                        "id": content_id,
                        "status": "completed_no_download",
                        "tavus_url": content_data.get('tavus_url'),
                        "message": "Video completed but download URL not available"
                    }
            elif tavus_status['status'] == 'failed':
                supabase_client.table('learning_content').update({
                    "status": "failed",
                    "error_message": tavus_status.get('error', 'Video generation failed')
                }).eq("id", content_id).execute()
                return {
                    "id": content_id,
                    "status": "failed",
                    "error": tavus_status.get('error', 'Video generation failed')
                }
            elif tavus_status['status'] == 'timeout':
                return {
                    "id": content_id,
                    "status": "timeout",
                    "tavus_url": content_data.get('tavus_url'),
                    "message": tavus_status.get('message', 'Video generation timed out')
                }
            else:
                return {
                    "id": content_id,
                    "status": "processing",
                    "tavus_url": content_data.get('tavus_url'),
                    "tavus_video_id": content_data.get('tavus_video_id'),
                    "progress": tavus_status.get('generation_progress', '0/100')
                }
        # Return current status
        return {
            "id": content_id,
            "status": content_data['status'],
            "tavus_url": content_data.get('tavus_url'),
            "error_message": content_data.get('error_message')
        }
    except Exception as e:
        print(f"Error checking video status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/learning-content/{chapter_id}")
async def get_learning_content(
    chapter_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get existing learning content for a chapter"""
    try:
        # Get all learning content for this chapter
        content_response = supabase_client.table('learning_content').select('*').eq('chapter_id', chapter_id).execute()
        
        if not content_response.data:
            return {
                "chapter_id": chapter_id,
                "content": []
            }
        
        # Filter content by user access
        user_content = []
        for content in content_response.data:
            if content['user_id'] == current_user['id']:
                user_content.append({
                    "id": content['id'],
                    "content_type": content['content_type'],
                    "content_url": content.get('content_url'),
                    "tavus_url": content.get('tavus_url'),
                    "status": content['status'],
                    "duration": content.get('duration', 180),
                    "created_at": content['created_at'],
                    "updated_at": content['updated_at']
                })
        
        return {
            "chapter_id": chapter_id,
            "content": user_content
        }
        
    except Exception as e:
        print(f"Error getting learning content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/combine-videos")
async def combine_videos(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Combine multiple videos using FFmpeg"""
    try:
        video_urls = request.get("video_urls", [])
        if not video_urls or len(video_urls) < 2:
            raise HTTPException(status_code=400, detail="At least 2 video URLs are required")
        
        video_service = VideoService(supabase_client)
        
        # Combine videos using FFmpeg
        combined_video_url = await video_service._combine_videos_with_ffmpeg(
            video_urls, 
            f"combined_video_{int(time.time())}.mp4",
            current_user['id']
        )
        
        if not combined_video_url:
            raise HTTPException(status_code=500, detail="Failed to combine videos")
        
        return {
            "combined_video_url": combined_video_url,
            "source_videos": video_urls,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error combining videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/combine-tavus-videos")
async def combine_tavus_videos(
    request: dict,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Combine Tavus video segments and process hosted_url"""
    try:
        print(f"🎬 Starting Tavus video combination for user: {current_user['id']}")
        
        content_id = request.get("content_id")
        if not content_id:
            print("❌ Missing content_id in request")
            raise HTTPException(status_code=400, detail="content_id is required")
        
        print(f"📖 Processing content: {content_id}")
        
        # Verify content access
        content_response = supabase_client.table('learning_content').select('*').eq('id', content_id).single().execute()
        if not content_response.data:
            print(f"❌ Content not found: {content_id}")
            raise HTTPException(status_code=404, detail="Content not found")
        
        content_data = content_response.data
        
        # Check access permissions
        if content_data['user_id'] != current_user['id']:
            print(f"❌ Access denied for content: {content_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
        
        # Check if content has a Tavus URL
        tavus_url = content_data.get('tavus_url')
        if not tavus_url:
            print(f"❌ No Tavus URL found for content: {content_id}")
            raise HTTPException(status_code=400, detail="No Tavus URL found for this content")
        
        print(f"🌐 Tavus URL found: {tavus_url}")
        
        # Combine videos using the video service
        video_service = VideoService(supabase_client)
        result = await video_service.combine_tavus_videos(content_id, supabase_client)
        
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate only the AI script and scene descriptions for a chapter using OpenRouter (no video generation)"""
    try:
        # Extract from request body
        chapter_id = request.get('chapter_id')
        script_style = validate_script_style(request.get('script_style', 'cinematic'))
        script_name = request.get('script_name')  # Optional custom name for the script
        plot_context = request.get('plot_context')  # Optional plot context for enhanced generation

        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")

        chapter_data = chapter_response.data
        book_data = chapter_data['books']

        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")

        # ✅ NEW: Check subscription tier and limits
        subscription_manager = SubscriptionManager(supabase_client)
        user_tier = await subscription_manager.get_user_tier(current_user['id'])
        tier_check = await subscription_manager.can_user_generate_video(current_user['id'])

        if not tier_check['can_generate']:
            raise HTTPException(
                status_code=402,
                detail=f"Monthly limit reached. You have used {tier_check['videos_used']} out of {tier_check['videos_limit']} videos. Please upgrade your subscription."
            )

        # Map subscription tier to model tier
        model_tier_mapping = {
            "free": ModelTier.FREE,
            "basic": ModelTier.BASIC,
            "standard": ModelTier.STANDARD,
            "premium": ModelTier.PREMIUM,
            "professional": ModelTier.PROFESSIONAL
        }
        user_model_tier = model_tier_mapping.get(user_tier.value, ModelTier.FREE)

        print(f"[OpenRouter] Generating {script_style} script for {user_tier.value} tier user")

        # Initialize OpenRouter service
        openrouter_service = OpenRouterService()

        # Get chapter context for enhanced content
        rag_service = RAGService(supabase_client)
        chapter_context = await rag_service.get_chapter_with_context(chapter_id, include_adjacent=True)

        # Prepare content for OpenRouter based on script style
        content_for_script = chapter_context.get('total_context', chapter_data['content'])

        # Enhance with plot context if provided
        plot_enhanced = False
        plot_info = None
        if plot_context:
            try:
                plot_info = await enhance_with_plot_context(
                    supabase_client=supabase_client,
                    user_id=current_user['id'],
                    book_id=chapter_data['book_id'],
                    chapter_content=content_for_script
                )
                if plot_info and plot_info['enhanced_content']:
                    content_for_script = plot_info['enhanced_content']
                    plot_enhanced = True
                    print(f"[PlotService] Enhanced script generation with plot context for chapter {chapter_id}")

            except Exception as plot_error:
                print(f"[PlotService] Warning: Could not enhance with plot context: {str(plot_error)}")
                # Continue with original content if plot enhancement fails

        # Extract target duration from request
        target_duration = request.get('target_duration', 'auto')
        if target_duration == 'auto':
            target_duration = 'auto'
        elif isinstance(target_duration, str) and target_duration.isdigit():
            target_duration = int(target_duration)
        else:
            target_duration = None

        # ✅ Generate script using OpenRouter with tier-appropriate model
        script_result = await openrouter_service.generate_script(
            content=chapter_data['content'],  # Use original content, plot context is handled separately
            user_tier=user_model_tier,
            script_type=script_style,
            target_duration=target_duration,
            plot_context=plot_info if plot_info and plot_info.get('enhanced_content') else None
        )

        if script_result.get('status') != 'success':
            raise HTTPException(
                status_code=500,
                detail=f"OpenRouter script generation failed: {script_result.get('error', 'Unknown error')}"
            )

        script = script_result.get('content', '')
        usage = script_result.get('usage', {})

        # ✅ Generate scene breakdown using OpenRouter
        scene_breakdown_result = await openrouter_service.analyze_content(
            content=f"Please break down this script into 5-8 detailed scene descriptions for video generation. Format each scene as 'Scene X: [Detailed description]' where X is the scene number:\n\n{script}",
            user_tier=user_model_tier,
            analysis_type="summary"  # Use summary type but with scene-specific prompt
        )

        scene_descriptions = []
        if scene_breakdown_result.get('status') == 'success':
            # Parse scene descriptions from the analysis result with improved logic
            analysis_result = scene_breakdown_result.get('result', '')
            scene_descriptions = parse_scene_descriptions(analysis_result)

        # Limit to reasonable number of scenes
        scene_descriptions = scene_descriptions[:10]

        # ✅ Generate character analysis using OpenRouter
        character_analysis_result = await openrouter_service.analyze_content(
            content=f"Extract and describe all characters mentioned in this script. Format as 'Character Name: [brief description/role]':\n\n{script}",
            user_tier=user_model_tier,
            analysis_type="characters"
        )

        characters = []
        character_details = ""
        if character_analysis_result.get('status') == 'success':
            character_details = character_analysis_result.get('result', '')
            # Extract character names with improved logic, filtered by script style
            characters = extract_characters(character_details, script_style)

        # Generate default script name if not provided
        if not script_name:
            script_name = f"{script_style.title()} Script - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Enhanced script data with metadata
        script_data = {
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "script_name": script_name,
            "user_id": current_user['id'],
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "total_scenes": len(scene_descriptions),
                "estimated_duration": len(script) * 0.01,  # Rough estimate
                "has_characters": len(characters) > 0,
                "script_length": len(script),
                "model_used": script_result.get('model_used', 'unknown'),
                "tier": user_tier.value,
                "tokens_used": usage.get('total_tokens', 0),
                "estimated_cost": usage.get('estimated_cost', 0)
            }
        }

        # Store in chapters table (your existing approach)
        ai_content = chapter_data.get('ai_generated_content') or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user['id']}:{script_style}"
        ai_content[key] = script_data

        supabase_client.table('chapters').update({
            "ai_generated_content": ai_content
        }).eq('id', chapter_id).execute()

        # Create a dedicated scripts table entry for easier access
        # Allow multiple scripts per chapter by not checking for existing ones
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user['id'],
            "script_style": script_style,
            "script_name": script_name,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "metadata": script_data["metadata"],
            "status": "ready",
            "service_used": "openrouter"
        }

        # Always insert new script (allow multiple scripts per chapter)
        script_result = supabase_client.table('scripts').insert(script_record).execute()
        script_id = script_result.data[0]['id']

        # ✅ Record usage for billing/limits
        await subscription_manager.record_usage(
            user_id=current_user['id'],
            resource_type='script',
            cost_usd=usage.get('estimated_cost', 0.0),
            metadata={
                'script_style': script_style,
                'model_used': script_result.get('model_used'),
                'tokens_used': usage.get('total_tokens', 0)
            }
        )

        print(f"[OpenRouter] Successfully generated {script_style} script with {len(characters)} characters and {len(scene_descriptions)} scenes")

        return {
            'chapter_id': chapter_id,
            'script_id': script_id,
            'script_name': script_name,
            'script': script,
            'scene_descriptions': scene_descriptions,
            'characters': characters,
            'character_details': character_details,
            'script_style': script_style,
            'metadata': script_data["metadata"],
            'service_used': 'openrouter',
            'tier': user_tier.value,
            'plot_enhanced': plot_enhanced,
            'plot_info': plot_info['plot_info'] if plot_info else None,
            'usage_info': {
                'tokens_used': usage.get('total_tokens', 0),
                'estimated_cost': usage.get('estimated_cost', 0),
                'model_used': script_result.get('model_used')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating script and scenes with OpenRouter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-script-and-scenes")
async def generate_script_and_scenes_with_gpt(
    request: dict = Body(...),  # Accept body instead of query params
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate only the AI script and scene descriptions for a chapter (no video generation)"""
    try:
          # Extract from request body
        chapter_id = request.get('chapter_id')
        script_style = request.get('script_style', 'cinematic_movie')
       
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")

        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        # Check access permissions
        if book_data['status'] != 'published' and book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this chapter")
        # Generate script using RAGService
        rag_service = RAGService(supabase_client)
        chapter_context = await rag_service.get_chapter_with_context(chapter_id, include_adjacent=True)
        script_result = await rag_service.generate_video_script(chapter_context, video_style=book_data.get('book_type', 'realistic'), script_style=script_style)
        script = script_result.get('script', '')
        characters = script_result.get('characters', [])
        character_details = script_result.get('character_details', '')
        # Parse script for scene descriptions
        video_service = VideoService()
        parsed = video_service._parse_script_for_services(script, script_style)
        scene_descriptions = parsed.get('scene_descriptions') or parsed.get('parsed_sections', {}).get('scene_descriptions', [])
        
        # Enhanced script data with metadata
        script_data = {
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "user_id": current_user['id'],
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "total_scenes": len(scene_descriptions),
                "estimated_duration": len(script) * 0.01,  # Rough estimate
                "has_characters": len(characters) > 0,
                "script_length": len(script)
            }
        }
        
        
        # Store in chapters table (your existing approach)
        ai_content = chapter_data.get('ai_generated_content') or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user['id']}:{script_style}"
        ai_content[key] = script_data
        
        supabase_client.table('chapters').update({
            "ai_generated_content": ai_content
        }).eq('id', chapter_id).execute()
        
        # ALSO create a dedicated scripts table entry for easier access
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user['id'],
            "script_style": script_style,
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "metadata": script_data["metadata"],
            "status": "ready"
        }
        
        # Insert or update in scripts table
        existing_script = supabase_client.table('scripts')\
            .select('id')\
            .eq('chapter_id', chapter_id)\
            .eq('user_id', current_user['id'])\
            .eq('script_style', script_style)\
            .execute()
        
        if existing_script.data:
            # Update existing
            script_result = supabase_client.table('scripts')\
                .update(script_record)\
                .eq('id', existing_script.data[0]['id'])\
                .execute()
            script_id = existing_script.data[0]['id']
        else:
            # Insert new
            script_result = supabase_client.table('scripts').insert(script_record).execute()
            script_id = script_result.data[0]['id']
        
        
        return {
            'chapter_id': chapter_id,
            'script_id':script_id,
            'script': script,
            'scene_descriptions': scene_descriptions,
            'characters': characters,
            'character_details': character_details,
            'script_style': script_style,
            'metadata': script_data["metadata"],
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Save a new AI-generated script and scene descriptions for a chapter."""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        if book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to modify this chapter")

        # Generate default script name if not provided
        if not script_name:
            script_name = f"{script_style.title()} Script - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Validate script style
        script_style = validate_script_style(script_style)

        # Create new script record (allow multiple scripts)
        script_record = {
            "chapter_id": chapter_id,
            "user_id": current_user['id'],
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
                "script_length": len(script)
            },
            "status": "ready",
            "service_used": "manual"
        }

        script_result = supabase_client.table('scripts').insert(script_record).execute()
        script_id = script_result.data[0]['id']

        return {
            "message": "Saved",
            "chapter_id": chapter_id,
            "script_id": script_id,
            "script_name": script_name,
            "script_style": script_style
        }
    except Exception as e:
        print(f"Error saving script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-script-and-scenes")
async def get_script_and_scenes(
    chapter_id: str,
    script_style: str = "cinematic_movie",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Fetch the saved AI-generated script and scene descriptions for a chapter (per user)."""
    try:
        chapter_response = supabase_client.table('chapters').select('ai_generated_content').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        ai_content = chapter_response.data.get('ai_generated_content') or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user['id']}:{script_style}"
        result = ai_content.get(key)
        if not result:
            return {"chapter_id": chapter_id, "script_style": script_style, "content": None}
        return {"chapter_id": chapter_id, "script_style": script_style, "content": result}
    except Exception as e:
        print(f"Error fetching script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-script/{script_id}")
async def delete_script(
    script_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete a specific script by ID."""
    try:
        # Verify script ownership
        script_response = supabase_client.table('scripts').select('*').eq('id', script_id).single().execute()
        if not script_response.data:
            raise HTTPException(status_code=404, detail="Script not found")

        script_data = script_response.data
        if script_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this script")

        # Delete the script
        supabase_client.table('scripts').delete().eq('id', script_id).execute()

        return {
            "message": "Script deleted successfully",
            "script_id": script_id,
            "script_name": script_data.get('script_name', 'Unnamed Script')
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting script: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add the missing pipeline status endpoint (around line 450)
@router.get("/pipeline-status/{video_gen_id}")
async def get_pipeline_status(
    video_gen_id: str,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get detailed pipeline status for video generation"""
    try:
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        video_data = video_response.data
        
        # Get pipeline steps
        steps_response = supabase_client.table('pipeline_steps')\
            .select('*').eq('video_generation_id', video_gen_id)\
            .order('step_order').execute()
        
        pipeline_steps = steps_response.data or []
        
        # Calculate progress
        total_steps = len(pipeline_steps) or 5  # Default to 5 steps
        completed_steps = len([s for s in pipeline_steps if s.get('status') == 'completed'])
        failed_steps = len([s for s in pipeline_steps if s.get('status') == 'failed'])
        
        # Determine current step
        current_step = None
        next_step = None
        
        processing_steps = [s for s in pipeline_steps if s.get('status') == 'processing']
        if processing_steps:
            current_step = processing_steps[0].get('step_name')
        else:
            # Find next pending step
            pending_steps = [s for s in pipeline_steps if s.get('status') == 'pending']
            if pending_steps:
                next_step = pending_steps[0].get('step_name')
        
        # Calculate percentage
        percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Determine overall status
        overall_status = video_data.get('generation_status', 'pending')
        
        # Build response
        pipeline_status = {
            'overall_status': overall_status,
            'failed_at_step': video_data.get('failed_at_step'),
            'can_resume': video_data.get('can_resume', False),
            'retry_count': video_data.get('retry_count', 0),
            'progress': {
                'completed_steps': completed_steps,
                'failed_steps': failed_steps,
                'total_steps': total_steps,
                'percentage': percentage,
                'current_step': current_step,
                'next_step': next_step
            },
            'steps': [
                {
                    'step_name': step.get('step_name'),
                    'status': step.get('status', 'pending'),
                    'started_at': step.get('started_at'),
                    'completed_at': step.get('completed_at'),
                    'error_message': step.get('error_message'),
                    'retry_count': step.get('retry_count', 0)
                }
                for step in pipeline_steps
            ]
        }
        
        return pipeline_status
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting pipeline status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/retry-generation/{video_gen_id}")
async def retry_video_generation(
    video_gen_id: str,
    request: dict = Body(default={}),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Retry video generation from failed step or specific step - with smart resume logic"""
    try:
        print(f"🔄 Starting retry for video generation: {video_gen_id}")
        print(f"🔄 Request body: {request}")
        
        # Extract retry_from_step from request body
        retry_from_step = request.get('retry_from_step') if request else None
        
        # Verify access
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).eq('user_id', current_user['id']).single().execute()
        
        if not video_response.data:
            raise HTTPException(status_code=404, detail="Video generation not found")
        
        video_data = video_response.data
        current_status = video_data.get('generation_status')
        
        print(f"🔄 Current status: {current_status}")
        
        # ✅ NEW: Smart step determination based on existing data
        next_step = await determine_next_step_from_database(video_gen_id, video_data, supabase_client)
        
        if retry_from_step:
            try:
                requested_step = PipelineStep(retry_from_step)
                # Warn if they're trying to redo a completed step
                if next_step.value > requested_step.value:
                    print(f"⚠️  WARNING: User requested step {requested_step.value} but {next_step.value} is the next logical step")
                step_to_retry = requested_step
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid step: {retry_from_step}")
        else:
            step_to_retry = next_step
            
        print(f"🔄 Determined retry step: {step_to_retry.value}")
        
        # Update retry count
        retry_count = video_data.get('retry_count', 0) + 1
        
        # Update video generation status based on step
        new_status = get_status_for_step(step_to_retry)
        
        supabase_client.table('video_generations').update({
            'generation_status': new_status,
            'failed_at_step': None,
            'error_message': None,
            'retry_count': retry_count,
            'can_resume': False,
            'updated_at': datetime.now().isoformat()
        }).eq('id', video_gen_id).execute()
        
        # Trigger the appropriate task
        task_id = await trigger_task_for_step(step_to_retry, video_gen_id, supabase_client)
        
        return {
            'message': f'Retrying from step: {step_to_retry.value}',
            'video_generation_id': video_gen_id,
            'retry_step': step_to_retry.value,
            'task_id': task_id,
            'retry_count': retry_count,
            'new_status': new_status,
            'existing_progress': await get_existing_progress_summary(video_gen_id, supabase_client)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in retry: {e}")
        import traceback
        print(f"🔍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def determine_next_step_from_database(video_gen_id: str, video_data: dict, supabase_client: Client) -> PipelineStep:
    """Determine the next step based on existing SUCCESSFUL data in the database"""
    
    print(f"🔍 Analyzing existing data for video generation: {video_gen_id}")
    
    # ✅ FIXED: Check for actual successful completions, not just existence
    audio_files = video_data.get('audio_files') or {}
    
    # Count actual successful audio files
    narrator_count = len(audio_files.get('narrator', []))
    characters_count = len(audio_files.get('characters', []))
    sound_effects_count = len(audio_files.get('sound_effects', []))
    background_music_count = len(audio_files.get('background_music', []))
    total_audio_count = narrator_count + characters_count + sound_effects_count + background_music_count
    
    has_audio = total_audio_count > 0
    
    # ✅ FIXED: Check image statistics for successful generations
    image_data = video_data.get('image_data') or {}
    image_stats = image_data.get('statistics', {})
    successful_images = image_stats.get('total_images_generated', 0)
    character_images_generated = image_stats.get('character_images_generated', 0)
    scene_images_generated = image_stats.get('scene_images_generated', 0)
    
    has_images = successful_images > 0 or (character_images_generated > 0 or scene_images_generated > 0)
    
    # ✅ FIXED: Check video statistics for successful generations  
    video_data_obj = video_data.get('video_data') or {}
    video_stats = video_data_obj.get('statistics', {})
    successful_videos = video_stats.get('videos_generated', 0)
    
    has_videos = successful_videos > 0
    
    # ✅ FIXED: Check for actual final video URL
    has_merged_video = bool(video_data.get('video_url'))
    
    # ✅ FIXED: Check lipsync statistics
    lipsync_data = video_data.get('lipsync_data') or {}
    lipsync_stats = lipsync_data.get('statistics', {})
    lipsync_scenes = lipsync_stats.get('scenes_processed', 0)
    
    has_lipsync = lipsync_scenes > 0
    
    # Also check database tables for more accuracy - but check for COMPLETED status
    try:
        # Check audio_generations table - only count completed
        audio_check = supabase_client.table('audio_generations')\
            .select('id')\
            .eq('video_generation_id', video_gen_id)\
            .eq('status', 'completed')\
            .execute()
        
        db_audio_count = len(audio_check.data or [])
        
        # Check image_generations table - only count completed
        image_check = supabase_client.table('image_generations')\
            .select('id')\
            .eq('video_generation_id', video_gen_id)\
            .eq('status', 'completed')\
            .execute()
            
        db_image_count = len(image_check.data or [])
        
        # Check video_segments table - only count completed
        video_check = supabase_client.table('video_segments')\
            .select('id')\
            .eq('video_generation_id', video_gen_id)\
            .eq('status', 'completed')\
            .execute()
            
        db_video_count = len(video_check.data or [])
        
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
    print(f"   - Images: {'✅' if has_images else '❌'} ({successful_images} generated)")  
    print(f"   - Videos: {'✅' if has_videos else '❌'} ({successful_videos} generated)")
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
    script_data = video_data.get('script_data') or {}
    characters = script_data.get('characters', [])
    character_audio = audio_files.get('characters', [])
    
    needs_lipsync = bool(characters and character_audio)
    
    if needs_lipsync and not has_lipsync:
        print(f"🎯 Next step: LIP_SYNC (missing lipsync for {len(characters)} characters)")
        return PipelineStep.LIP_SYNC
    
    # If everything exists, just return the status-based step
    current_status = video_data.get('generation_status', 'failed')
    if current_status == 'completed':
        print(f"🎯 All steps completed, but retrying LIP_SYNC as final step")
        return PipelineStep.LIP_SYNC
    else:
        print(f"🎯 Defaulting to AUDIO_GENERATION as fallback")
        return PipelineStep.AUDIO_GENERATION

async def get_existing_progress_summary(video_gen_id: str, supabase_client: Client) -> dict:
    """Get a summary of existing progress for the frontend - CORRECTED VERSION"""
    try:
        video_response = supabase_client.table('video_generations')\
            .select('*').eq('id', video_gen_id).single().execute()
            
        if not video_response.data:
            return {}
            
        video_data = video_response.data
        
        # ✅ FIXED: Count actual successful items, not just existence
        audio_files = video_data.get('audio_files') or {}
        image_data = video_data.get('image_data') or {}
        video_data_obj = video_data.get('video_data') or {}
        
        # Count actual audio files
        audio_count = (
            len(audio_files.get('narrator', [])) + 
            len(audio_files.get('characters', [])) + 
            len(audio_files.get('sound_effects', [])) + 
            len(audio_files.get('background_music', []))
        )
        
        # Get actual successful counts from statistics
        image_stats = image_data.get('statistics', {})
        image_count = image_stats.get('total_images_generated', 0)
        
        video_stats = video_data_obj.get('statistics', {})
        video_count = video_stats.get('videos_generated', 0)
        
        return {
            'audio_files_count': audio_count,
            'images_count': image_count, 
            'videos_count': video_count,
            'has_final_video': bool(video_data.get('video_url')),
            'last_completed_step': get_last_completed_step_corrected(video_data),
            'progress_percentage': calculate_progress_percentage_corrected(video_data)
        }
        
    except Exception as e:
        print(f"Error getting progress summary: {e}")
        return {}

def get_last_completed_step_corrected(video_data: dict) -> str:
    """Determine the last completed step - CORRECTED VERSION"""
    
    # Check actual successful counts
    audio_files = video_data.get('audio_files') or {}
    total_audio = (
        len(audio_files.get('narrator', [])) + 
        len(audio_files.get('characters', [])) + 
        len(audio_files.get('sound_effects', [])) + 
        len(audio_files.get('background_music', []))
    )
    
    image_data = video_data.get('image_data') or {}
    image_stats = image_data.get('statistics', {})
    total_images = image_stats.get('total_images_generated', 0)
    
    video_data_obj = video_data.get('video_data') or {}
    video_stats = video_data_obj.get('statistics', {})
    total_videos = video_stats.get('videos_generated', 0)
    
    lipsync_data = video_data.get('lipsync_data') or {}
    lipsync_stats = lipsync_data.get('statistics', {})
    lipsync_scenes = lipsync_stats.get('scenes_processed', 0)
    
    has_final_video = bool(video_data.get('video_url'))
    
    # Return the last successfully completed step
    if lipsync_scenes > 0:
        return 'lipsync_completed'
    elif has_final_video:
        return 'merge_completed'  
    elif total_videos > 0:
        return 'video_completed'
    elif total_images > 0:
        return 'images_completed'
    elif total_audio > 0:
        return 'audio_completed'
    else:
        return 'none'

def calculate_progress_percentage_corrected(video_data: dict) -> float:
    """Calculate overall progress percentage - CORRECTED VERSION"""
    steps_completed = 0
    total_steps = 5  # audio, image, video, merge, lipsync
    
    # Check actual successful completions
    audio_files = video_data.get('audio_files') or {}
    total_audio = (
        len(audio_files.get('narrator', [])) + 
        len(audio_files.get('characters', [])) + 
        len(audio_files.get('sound_effects', [])) + 
        len(audio_files.get('background_music', []))
    )
    
    if total_audio > 0:
        steps_completed += 1
        
    image_data = video_data.get('image_data') or {}
    if image_data.get('statistics', {}).get('total_images_generated', 0) > 0:
        steps_completed += 1
        
    video_data_obj = video_data.get('video_data') or {}
    if video_data_obj.get('statistics', {}).get('videos_generated', 0) > 0:
        steps_completed += 1
        
    if video_data.get('video_url'):
        steps_completed += 1
        
    lipsync_data = video_data.get('lipsync_data') or {}
    if lipsync_data.get('statistics', {}).get('scenes_processed', 0) > 0:
        steps_completed += 1
        
    return (steps_completed / total_steps) * 100


def get_status_for_step(step: PipelineStep) -> str:
    """Get the appropriate status for a pipeline step"""
    status_mapping = {
        PipelineStep.AUDIO_GENERATION: 'generating_audio',
        PipelineStep.IMAGE_GENERATION: 'generating_images', 
        PipelineStep.VIDEO_GENERATION: 'generating_video',
        PipelineStep.AUDIO_VIDEO_MERGE: 'merging_audio',
        PipelineStep.LIP_SYNC: 'applying_lipsync'
    }
    return status_mapping.get(step, 'retrying')

async def trigger_task_for_step(step: PipelineStep, video_gen_id: str, supabase_client: Client) -> str:
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
        supabase_client.table('video_generations').update({
            'generation_status': 'failed',
            'error_message': f"Failed to start retry task: {str(task_error)}",
            'can_resume': True
        }).eq('id', video_gen_id).execute()
        
        raise HTTPException(status_code=500, detail=f"Failed to start retry task: {str(task_error)}")

