from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime


class MergeInputSource(str, Enum):
    PIPELINE_OUTPUT = "pipeline_output"
    CUSTOM_UPLOAD = "custom_upload"


class MergeQualityTier(str, Enum):
    WEB = "web"
    MEDIUM = "medium"
    HIGH = "high"
    CUSTOM = "custom"


class MergeOutputFormat(str, Enum):
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"


class FFmpegVideoCodec(str, Enum):
    LIBX264 = "libx264"
    LIBX265 = "libx265"
    LIBVPX_VP9 = "libvpx-vp9"


class FFmpegAudioCodec(str, Enum):
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "libopus"


class FFmpegParameters(BaseModel):
    """FFmpeg parameters for video processing"""
    video_codec: Optional[FFmpegVideoCodec] = Field(None, description="Video codec to use")
    audio_codec: Optional[FFmpegAudioCodec] = Field(None, description="Audio codec to use")
    video_bitrate: Optional[str] = Field(None, description="Video bitrate (e.g., '2M', '5000k')")
    audio_bitrate: Optional[str] = Field(None, description="Audio bitrate (e.g., '128k', '256k')")
    resolution: Optional[str] = Field(None, description="Output resolution (e.g., '1920x1080', '1280x720')")
    fps: Optional[int] = Field(None, ge=1, le=120, description="Frames per second")
    preset: Optional[str] = Field(None, description="Encoding preset (ultrafast, fast, medium, slow)")
    crf: Optional[int] = Field(None, ge=0, le=51, description="Constant Rate Factor (0-51, lower = higher quality)")
    custom_filters: Optional[List[str]] = Field(None, description="Custom FFmpeg filter strings")

    @validator('video_bitrate', 'audio_bitrate')
    def validate_bitrate(cls, v):
        if v is None:
            return v
        # Basic validation for bitrate format
        import re
        if not re.match(r'^\d+[kKmM]$', v):
            raise ValueError('Bitrate must be in format like "128k", "2M", etc.')
        return v

    @validator('resolution')
    def validate_resolution(cls, v):
        if v is None:
            return v
        # Basic validation for resolution format
        import re
        if not re.match(r'^\d+x\d+$', v):
            raise ValueError('Resolution must be in format "WIDTHxHEIGHT" (e.g., "1920x1080")')
        return v


class MergeInputFile(BaseModel):
    """Input file for merge operation"""
    url: str = Field(..., description="URL of the input file")
    type: str = Field(..., description="Type of file (video, audio, image)")
    duration: Optional[float] = Field(None, description="Duration in seconds")
    start_time: Optional[float] = Field(0, ge=0, description="Start time offset in seconds")
    end_time: Optional[float] = Field(None, ge=0, description="End time offset in seconds")
    volume: Optional[float] = Field(1.0, ge=0, le=2.0, description="Volume multiplier (0.0-2.0)")
    fade_in: Optional[float] = Field(0, ge=0, description="Fade in duration in seconds")
    fade_out: Optional[float] = Field(0, ge=0, description="Fade out duration in seconds")


class MergeManualRequest(BaseModel):
    """Request model for manual merge operation"""
    video_generation_id: Optional[str] = Field(None, description="ID of video generation to use as base")
    input_sources: List[MergeInputFile] = Field(..., description="List of input files to merge")
    quality_tier: MergeQualityTier = Field(MergeQualityTier.WEB, description="Quality tier for output")
    output_format: MergeOutputFormat = Field(MergeOutputFormat.MP4, description="Output format")
    ffmpeg_params: Optional[FFmpegParameters] = Field(None, description="Custom FFmpeg parameters")
    merge_name: Optional[str] = Field(None, description="Name for this merge operation")
    add_transitions: Optional[bool] = Field(True, description="Whether to add automatic transitions")
    normalize_audio: Optional[bool] = Field(True, description="Whether to normalize audio levels")


class MergePreviewRequest(BaseModel):
    """Request model for merge preview operation"""
    input_sources: List[MergeInputFile] = Field(..., min_items=1, max_items=2, description="Input files for preview (max 2)")
    quality_tier: MergeQualityTier = Field(MergeQualityTier.WEB, description="Quality tier for preview")
    preview_duration: Optional[float] = Field(10.0, ge=1, le=30, description="Preview duration in seconds")
    ffmpeg_params: Optional[FFmpegParameters] = Field(None, description="Custom FFmpeg parameters")


class MergeStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MergeOperation(BaseModel):
    """Merge operation model"""
    id: str
    user_id: str
    video_generation_id: Optional[str]
    status: MergeStatus
    input_sources: List[MergeInputFile]
    quality_tier: MergeQualityTier
    output_format: MergeOutputFormat
    ffmpeg_params: Optional[FFmpegParameters]
    merge_name: Optional[str]
    output_url: Optional[str]
    preview_url: Optional[str]
    error_message: Optional[str]
    processing_stats: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class MergeManualResponse(BaseModel):
    """Response model for manual merge operation"""
    merge_id: str
    status: MergeStatus
    message: str
    estimated_duration: Optional[float]
    queue_position: Optional[int]


class MergeStatusResponse(BaseModel):
    """Response model for merge status check"""
    merge_id: str
    status: MergeStatus
    progress_percentage: Optional[float]
    current_step: Optional[str]
    output_url: Optional[str]
    preview_url: Optional[str]
    error_message: Optional[str]
    processing_stats: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class MergePreviewResponse(BaseModel):
    """Response model for merge preview"""
    preview_url: str
    preview_duration: float
    status: str
    message: str


class MergeDownloadResponse(BaseModel):
    """Response model for merge download"""
    download_url: str
    file_size_bytes: Optional[int]
    content_type: str
    filename: str
    expires_at: Optional[datetime]


class MergeError(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str]
    code: Optional[str]