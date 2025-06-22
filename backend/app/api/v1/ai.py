from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.schemas import AIRequest, AIResponse, QuizGenerationRequest, User
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.video_service import VideoService
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
    response = await ai_service.generate_text_content(request.prompt, request.context)
    return AIResponse(text=response)


@router.post("/generate-quiz", response_model=AIResponse)
async def generate_quiz_from_book(
    request: QuizGenerationRequest,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Generate a quiz from a book's content"""
    book_response = supabase_client.table('books').select('content').eq('id', request.book_id).single().execute()
    if book_response.error or not book_response.data:
        raise HTTPException(status_code=404, detail="Book not found")

    book_content = book_response.data['content']

    ai_service = AIService()
    quiz_json = await ai_service.generate_quiz(
        book_content,
        request.num_questions,
        request.difficulty
    )
    return AIResponse(text=quiz_json)


@router.post("/generate-voice")
async def generate_voice(
    text: str,
    character: str = "narrator",
    emotion: str = "neutral",
    current_user: dict = Depends(get_current_active_user)
):
    """Generate AI voice for text"""
    voice_service = VoiceService()
    voices = await voice_service.get_available_voices()
    character_voice = next((v for v in voices if v["name"].lower() == character.lower()), voices[0])
    
    audio_url = await voice_service.generate_speech(
        text,
        character_voice,
        emotion
    )
    return {"audio_url": audio_url}


@router.get("/voices")
async def get_available_voices(
    current_user: dict = Depends(get_current_active_user)
):
    """Get available AI voices"""
    voice_service = VoiceService()
    voices = await voice_service.get_available_voices()
    return {"voices": voices}