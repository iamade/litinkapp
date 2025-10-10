from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class VideoGenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING_AUDIO = "generating_audio"
    AUDIO_COMPLETED = "audio_completed"
    GENERATING_IMAGES = "generating_images"
    IMAGES_COMPLETED = "images_completed"
    GENERATING_VIDEO = "generating_video"
    VIDEO_COMPLETED = "video_completed"
    MERGING_AUDIO = "merging_audio"
    APPLYING_LIPSYNC = "applying_lipsync"
    COMBINING = "combining"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class VideoQualityTier(str, Enum):
    FREE = "free"
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
    quality_tier: VideoQualityTier = VideoQualityTier.FREE
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

# ✅ Updated ImageGeneration schema to match actual database structure
class ImageGeneration(BaseModel):
    id: str
    video_generation_id: str
    image_type: Optional[str] = None  # character, scene, etc.
    scene_id: Optional[str] = None
    character_name: Optional[str] = None
    shot_index: Optional[int] = 0
    scene_description: Optional[str] = None
    image_prompt: Optional[str] = None  # This exists in DB
    text_prompt: Optional[str] = None   # This is the new column we're adding
    style: Optional[str] = None         # This is the new column we're adding
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    generation_time_seconds: Optional[float] = None
    sequence_order: Optional[int] = None
    status: str = "pending"
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
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
    # Add the data fields that are used in the code
    script_data: Optional[Dict[str, Any]] = None
    audio_files: Optional[Dict[str, Any]] = None
    image_data: Optional[Dict[str, Any]] = None
    video_data: Optional[Dict[str, Any]] = None
    merge_data: Optional[Dict[str, Any]] = None
    lipsync_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime