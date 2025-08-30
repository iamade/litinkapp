from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
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
 
@router.post("/generate-entertainment-video")
async def generate_entertainment_video(
    request: dict = Body(...),
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate entertainment video using already saved script"""
    try:
        # Extract parameters from request body
        chapter_id = request.get('chapter_id')
        quality_tier = request.get('quality_tier', 'basic')
        video_style = request.get('video_style', 'realistic')  # This is for visual styling
        
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
        video_generation = supabase_client.table('video_generations').insert({
            'chapter_id': chapter_id,
            'script_id': script_data['id'],
            'user_id': current_user['id'],
            'generation_status': 'pending',
            'quality_tier': quality_tier,
            'script_data': {
                'script': script_data['script'],
                'scene_descriptions': script_data['scene_descriptions'],
                'characters': script_data['characters'],
                'script_style': script_data['script_style'],  # Preserve original style
                'video_style': video_style  # New: visual styling for video generation
            }
        }).execute()

        video_gen_id = video_generation.data[0]['id']

        # Step 3: Start audio generation (first step in pipeline)
        from app.tasks.audio_tasks import generate_all_audio_for_video
        generate_all_audio_for_video.delay(video_gen_id)
        
        return {
            "video_generation_id": video_gen_id,
            "script_id": script_data['id'],
            "status": "queued",
            "message": "Video generation started using saved script",
            "script_info": {
                "script_style": script_data['script_style'],  # What type of script (movie/narration)
                "video_style": video_style,  # How the video should look (realistic/cinematic/etc)
                "scenes": len(script_data.get('scene_descriptions', [])),
                "characters": len(script_data.get('characters', [])),
                "created_at": script_data['created_at']
            }
        }

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
        
        # Base response
        result = {
            'status': status,
            'quality_tier': data['quality_tier'],
            'video_url': data.get('video_url'),
            'created_at': data['created_at'],
            'script_id': data.get('script_id')
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
            width = video.get('width', 1024)
            height = video.get('height', 576)
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

@router.post("/generate-character-voice")
async def generate_character_voice(
    text: str,
    character_name: str,
    character_traits: str = "",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate character-specific voice"""
    try:
        elevenlabs_service = ElevenLabsService()
        audio_url = await elevenlabs_service.generate_character_voice(
            text=text,
            character_name=character_name,
            character_traits=character_traits,
            user_id=current_user['id']
        )
        
        return {"audio_url": audio_url}
        
    except Exception as e:
        print(f"Error generating character voice: {e}")
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

@router.post("/generate-script-and-scenes")
async def generate_script_and_scenes(
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
            'metadata': script_data["metadata"]
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
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Save or update the AI-generated script and scene descriptions for a chapter (per user)."""
    try:
        # Verify chapter access
        chapter_response = supabase_client.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        chapter_data = chapter_response.data
        book_data = chapter_data['books']
        if book_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to modify this chapter")
        # Prepare new content
        new_content = {
            "script": script,
            "scene_descriptions": scene_descriptions,
            "characters": characters,
            "character_details": character_details,
            "script_style": script_style,
            "user_id": current_user['id']
        }
        # Update ai_generated_content (per user, per script_style)
        ai_content = chapter_data.get('ai_generated_content') or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user['id']}:{script_style}"
        ai_content[key] = new_content
        supabase_client.table('chapters').update({"ai_generated_content": ai_content}).eq('id', chapter_id).execute()
        return {"message": "Saved", "chapter_id": chapter_id, "script_style": script_style}
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

@router.delete("/delete-script-and-scenes")
async def delete_script_and_scenes(
    chapter_id: str,
    script_style: str = "cinematic_movie",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Delete the saved AI-generated script and scene descriptions for a chapter (per user)."""
    try:
        chapter_response = supabase_client.table('chapters').select('ai_generated_content').eq('id', chapter_id).single().execute()
        if not chapter_response.data:
            raise HTTPException(status_code=404, detail="Chapter not found")
        ai_content = chapter_response.data.get('ai_generated_content') or {}
        if not isinstance(ai_content, dict):
            ai_content = {}
        key = f"{current_user['id']}:{script_style}"
        if key in ai_content:
            del ai_content[key]
            supabase_client.table('chapters').update({"ai_generated_content": ai_content}).eq('id', chapter_id).execute()
        return {"message": "Deleted", "chapter_id": chapter_id, "script_style": script_style}
    except Exception as e:
        print(f"Error deleting script and scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))