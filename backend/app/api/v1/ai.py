from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.book import Chapter
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.video_service import VideoService

router = APIRouter()


@router.post("/generate-quiz")
async def generate_quiz(
    chapter_id: str,
    difficulty: str = "medium",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI quiz for a chapter"""
    chapter = await Chapter.get_by_id(db, chapter_id)
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found"
        )
    
    ai_service = AIService()
    quiz_questions = await ai_service.generate_quiz(
        chapter.content,
        difficulty
    )
    
    return {"questions": quiz_questions}


@router.post("/generate-lesson")
async def generate_lesson(
    chapter_id: str,
    topic: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI lesson for a chapter"""
    chapter = await Chapter.get_by_id(db, chapter_id)
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found"
        )
    
    ai_service = AIService()
    lesson_content = await ai_service.generate_lesson(
        chapter.content,
        topic
    )
    
    return lesson_content


@router.post("/generate-voice")
async def generate_voice(
    text: str,
    character: str = "narrator",
    emotion: str = "neutral",
    current_user: User = Depends(get_current_user)
):
    """Generate AI voice for text"""
    voice_service = VoiceService()
    
    # Get character voice configuration
    voices = await voice_service.get_available_voices()
    character_voice = next((v for v in voices if v["name"].lower() == character.lower()), voices[0])
    
    audio_url = await voice_service.generate_speech(
        text,
        character_voice,
        emotion
    )
    
    return {"audio_url": audio_url}


@router.post("/generate-video-scene")
async def generate_video_scene(
    scene_description: str,
    dialogue: str,
    avatar_style: str = "realistic",
    current_user: User = Depends(get_current_user)
):
    """Generate AI video scene"""
    video_service = VideoService()
    
    video_scene = await video_service.generate_story_scene(
        scene_description,
        dialogue,
        avatar_style
    )
    
    return video_scene


@router.get("/voices")
async def get_available_voices(
    current_user: User = Depends(get_current_user)
):
    """Get available AI voices"""
    voice_service = VoiceService()
    voices = await voice_service.get_available_voices()
    return {"voices": voices}


@router.get("/avatars")
async def get_available_avatars(
    current_user: User = Depends(get_current_user)
):
    """Get available AI avatars"""
    video_service = VideoService()
    avatars = await video_service.get_available_avatars()
    return {"avatars": avatars}


@router.post("/analyze-content")
async def analyze_content(
    content: str,
    analysis_type: str = "summary",
    current_user: User = Depends(get_current_user)
):
    """Analyze content using AI"""
    ai_service = AIService()
    
    if analysis_type == "summary":
        result = await ai_service.generate_summary(content)
    elif analysis_type == "keywords":
        result = await ai_service.extract_keywords(content)
    elif analysis_type == "difficulty":
        result = await ai_service.assess_difficulty(content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis type"
        )
    
    return {"result": result}