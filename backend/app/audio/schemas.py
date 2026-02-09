from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AudioGenerationRequest(BaseModel):
    """Request model for generating audio"""

    text: Optional[str] = None
    voice_id: Optional[str] = None
    emotion: Optional[str] = "neutral"
    speed: Optional[float] = 1.0
    duration: Optional[float] = None
    custom_prompt: Optional[str] = None
    script_id: Optional[str] = None
    # Shot information for audio-to-scene mapping
    shot_type: Optional[str] = "key_scene"  # 'key_scene' or 'suggested_shot'
    shot_index: Optional[int] = 0  # 0 = key scene, 1+ = suggested shots


class AudioGenerationResponse(BaseModel):
    """Response model for single audio generation"""

    record_id: str
    audio_url: str
    prompt_used: str
    metadata: Dict[str, Any]
    duration: Optional[float] = None
    generation_time: Optional[float] = None
    message: str


class AudioGenerationQueuedResponse(BaseModel):
    """Response model for queued audio generation"""

    task_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = None
    record_id: Optional[str] = None


class AudioRecord(BaseModel):
    """Model for audio generation record"""

    id: str
    user_id: str
    chapter_id: Optional[str] = None
    audio_type: str
    text_content: Optional[str] = None
    voice_id: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    generation_status: str
    sequence_order: Optional[int] = None
    model_id: Optional[str] = None
    metadata: Dict[str, Any]
    created_at: str
    updated_at: Optional[str] = None
    error_message: Optional[str] = None


class ChapterAudioResponse(BaseModel):
    """Response model for listing chapter audio"""

    chapter_id: str
    audio_files: List[AudioRecord]
    total_count: int


class AudioExportRequest(BaseModel):
    """Request model for audio export"""

    format: str = "mp3"
    include_narration: bool = True
    include_music: bool = True
    include_effects: bool = True
    include_ambiance: bool = True
    include_dialogue: bool = True
    mix_settings: Optional[Dict[str, Any]] = None


class AudioExportResponse(BaseModel):
    """Response model for audio export"""

    export_id: str
    status: str
    message: str
    download_url: Optional[str] = None
    estimated_time_seconds: Optional[int] = None


class DeleteAudioResponse(BaseModel):
    """Response model for audio deletion"""

    success: bool
    message: str
    record_id: str


class AudioStatusResponse(BaseModel):
    """Response model for checking audio generation status"""

    record_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    audio_url: Optional[str] = None
    error_message: Optional[str] = None
    duration: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None


class AudioReassignRequest(BaseModel):
    """Request model for reassigning audio to a different shot"""

    shot_index: int  # 0 = key scene, 1+ = suggested shots
    shot_type: Optional[str] = (
        None  # 'key_scene' or 'suggested_shot' - auto-set if not provided
    )


class AudioReassignResponse(BaseModel):
    """Response model for audio reassignment"""

    audio_id: str
    previous_shot_index: int
    new_shot_index: int
    new_shot_type: str
    message: str
