from fastapi import APIRouter, Depends, HTTPException
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
    chapter_id: str,
    animation_style: str = "cinematic",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate entertainment video from chapter using RAG system with OpenAI enhancement"""
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
        
        # Generate entertainment video
        video_service = VideoService(supabase_client)
        video_result = await video_service.generate_entertainment_video(
            chapter_id=chapter_id,
            animation_style=animation_style,
            supabase_client=supabase_client
        )
        
        if not video_result:
            raise HTTPException(status_code=500, detail="Failed to generate entertainment video")
        
        return video_result
        
    except Exception as e:
        print(f"Error generating entertainment video: {e}")
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
    """Generate realistic video tutorial using RAG embeddings and Tavus"""
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
        
        # Generate tutorial script using AI
        tutorial_script = await ai_service.generate_tutorial_script(tutorial_prompt)
        
        if not tutorial_script:
            raise HTTPException(status_code=500, detail="Failed to generate tutorial script")
        
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
            "status": "processing"
        }
        
        db_result = supabase_client.table('learning_content').insert(initial_record).execute()
        content_id = db_result.data[0]['id'] if db_result.data else None
        
        # Use Tavus directly with the tutorial script
        tavus_result = await video_service._generate_tavus_video(tutorial_script, "realistic")
        
        if not tavus_result:
            # Update record with failed status
            if content_id:
                supabase_client.table('learning_content').update({
                    "status": "failed",
                    "error_message": "Tavus video generation failed"
                }).eq("id", content_id).execute()
            raise HTTPException(status_code=500, detail="Failed to generate realistic video")
        
        # Extract Tavus information
        tavus_video_id = tavus_result.get("video_id")
        tavus_url = tavus_result.get("hosted_url") or tavus_result.get("video_url")
        download_url = tavus_result.get("download_url")
        final_video_url = tavus_result.get("video_url")
        
        # Update record with Tavus information
        update_data = {
            "tavus_url": tavus_url,
            "tavus_video_id": tavus_video_id,
            "status": "ready" if final_video_url else "processing"
        }
        
        if final_video_url:
            update_data["content_url"] = final_video_url
            update_data["duration"] = tavus_result.get("duration", 180)
        
        if content_id:
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
        
        return response_data
        
    except Exception as e:
        print(f"Error generating realistic video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        # Get content record
        content_response = supabase_client.table('learning_content').select('*').eq('id', content_id).single().execute()
        if not content_response.data:
            raise HTTPException(status_code=404, detail="Content not found")
        
        content_data = content_response.data
        
        # Check access permissions
        if content_data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this content")
        
        # If status is already ready, return the data
        if content_data['status'] == 'ready':
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
            
            # Check Tavus status
            tavus_status = await video_service._poll_video_status(
                content_data['tavus_video_id'], 
                f"Video for content {content_id}"
            )
            
            if tavus_status['status'] == 'completed':
                # Download and process the video
                video_url = tavus_status.get('video_url')
                if video_url:
                    # Download video and upload to Supabase
                    final_video_url = await video_service._download_and_store_video(
                        video_url, 
                        f"video_{content_id}.mp4",
                        current_user['id']
                    )
                    
                    # Update database record
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
                    # Video completed but no download URL
                    return {
                        "id": content_id,
                        "status": "completed_no_download",
                        "tavus_url": content_data.get('tavus_url'),
                        "message": "Video completed but download URL not available"
                    }
            
            elif tavus_status['status'] == 'failed':
                # Update database with failed status
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
                # Still processing
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