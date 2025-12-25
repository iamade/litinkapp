from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class SceneImageRequest(BaseModel):
    """Request model for generating scene images"""
    scene_description: str
    style: str = "cinematic"
    aspect_ratio: str = "16:9"
    custom_prompt: Optional[str] = None
    script_id: Optional[str] = None


class CharacterImageRequest(BaseModel):
    """Request model for generating character images"""
    character_name: str
    character_description: str
    style: str = "realistic"
    aspect_ratio: str = "3:4"
    custom_prompt: Optional[str] = None
    script_id: Optional[str] = None


class BatchImageRequest(BaseModel):
    """Request model for batch image generation"""
    images: List[Dict[str, Any]]


class ImageGenerationResponse(BaseModel):
    """Response model for single image generation"""
    record_id: str
    image_url: str
    prompt_used: str
    metadata: Dict[str, Any]
    generation_time: Optional[float] = None
    message: str


class ImageGenerationQueuedResponse(BaseModel):
    """Response model for queued image generation"""
    task_id: str
    status: str
    message: str
    estimated_time_seconds: Optional[int] = None
    record_id: Optional[str] = None
    # Scene-related fields for async tracking
    scene_number: Optional[int] = None
    retry_count: int = 0


class BatchImageResponse(BaseModel):
    """Response model for batch image generation"""
    results: List[Dict[str, Any]]
    successful_count: int
    total_count: int


class ImageRecord(BaseModel):
    """Model for image generation record"""
    id: str
    user_id: str
    image_type: str
    scene_description: Optional[str] = None
    character_name: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_prompt: Optional[str] = None
    script_id: Optional[str] = None
    # Scene-related fields for async tracking
    chapter_id: Optional[UUID] = None
    scene_number: Optional[int] = None
    retry_count: int = 0
    status: str
    generation_time_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    metadata: Dict[str, Any]
    created_at: str
    updated_at: Optional[str] = None


class ChapterImagesResponse(BaseModel):
    """Response model for listing chapter images"""
    chapter_id: str
    images: List[ImageRecord]
    total_count: int


class BatchStatusResponse(BaseModel):
    """Response model for batch generation status"""
    batch_id: str
    status: str
    completed_count: int
    total_count: int
    results: List[Dict[str, Any]]
    created_at: str


class DeleteImageResponse(BaseModel):
    """Response model for image deletion"""
    success: bool
    message: str
    record_id: Optional[str] = None


class ImageStatusResponse(BaseModel):
    """Response model for checking image generation status"""
    record_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    image_url: Optional[str] = None
    prompt: Optional[str] = None
    script_id: Optional[str] = None
    # Scene-related fields for async tracking
    scene_number: Optional[int] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    generation_time_seconds: Optional[float] = None
    created_at: str
    updated_at: Optional[str] = None