import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AudiobookGenerateRequest(BaseModel):
    book_id: uuid.UUID
    voice_id: Optional[str] = None


class AudiobookChapterResponse(BaseModel):
    id: uuid.UUID
    audiobook_id: uuid.UUID
    chapter_id: uuid.UUID
    chapter_number: int
    status: str
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = 0.0
    credits_used: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AudiobookResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    book_id: uuid.UUID
    title: str
    status: str
    voice_id: Optional[str] = None
    total_chapters: int = 0
    completed_chapters: int = 0
    total_duration_seconds: Optional[float] = 0.0
    error_message: Optional[str] = None
    credits_reserved: int = 0
    credits_used: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AudiobookDetailResponse(AudiobookResponse):
    chapters: List[AudiobookChapterResponse] = []


class VoiceOptionResponse(BaseModel):
    voice_id: str
    name: Optional[str] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    preview_url: Optional[str] = None
