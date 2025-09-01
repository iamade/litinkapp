from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class VideoGenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    GENERATING_IMAGES = "generating_images"
    GENERATING_VIDEO = "generating_video"
    COMBINING = "combining"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoQualityTier(str, Enum):
    BASIC = "basic"
    STANDARD = "standard"
    STANDARD_2 = "standard_2"
    PRO = "pro"
    MASTER = "master"

class AudioType(str, Enum):
    NARRATOR = "narrator"
    CHARACTER = "character"
    SOUND_EFFECTS = "sound_effects"
    BACKGROUND_MUSIC = "background_music"

class VideoGenerationRequest(BaseModel):
    chapter_id: str
    quality_tier: VideoQualityTier = VideoQualityTier.BASIC
    video_style: str = "realistic"

class VideoGenerationResponse(BaseModel):
    video_generation_id: str
    script_id: str
    status: str
    audio_task_id: Optional[str] = None
    task_status: Optional[str] = None
    message: str
    script_info: Dict[str, Any]

class AudioGeneration(BaseModel):
    id: str
    video_generation_id: str
    audio_type: AudioType
    scene_id: Optional[str] = None
    character_name: Optional[str] = None
    text_content: Optional[str] = None
    voice_id: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str = "pending"
    created_at: datetime

class ImageGeneration(BaseModel):
    id: str
    video_generation_id: str
    scene_id: Optional[str] = None
    shot_index: int = 0
    scene_description: Optional[str] = None
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    status: str = "pending"
    created_at: datetime

class VideoGeneration(BaseModel):
    id: str
    chapter_id: str
    script_id: Optional[str] = None
    user_id: str
    generation_status: VideoGenerationStatus
    quality_tier: VideoQualityTier
    video_url: Optional[str] = None
    audio_task_id: Optional[str] = None
    task_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime