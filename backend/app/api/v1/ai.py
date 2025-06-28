from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.schemas import AIRequest, AIResponse, QuizGenerationRequest, User
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
    text: str,
    background_music: str = "ambient",
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate complete audio narration with background music"""
    try:
        elevenlabs_service = ElevenLabsService()
        audio_url = await elevenlabs_service.generate_audio_narration(
            text=text,
            background_music=background_music,
            voice_id=voice_id,
            user_id=current_user['id']
        )
        
        return {"audio_url": audio_url}
        
    except Exception as e:
        print(f"Error generating audio narration: {e}")
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