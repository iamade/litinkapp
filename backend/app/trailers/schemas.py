"""
Trailer schemas for API request/response handling.
KAN-149: Scene selection
KAN-150: Script + narration generation
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


# ==================== Request Schemas ====================

class TrailerAnalyzeRequest(BaseModel):
    """Request to analyze a project for trailer scene selection"""
    project_id: UUID
    target_duration_seconds: int = Field(default=90, ge=30, le=300)
    tone: str = Field(default="epic")  # epic, dramatic, romantic, action, mysterious
    style: str = Field(default="cinematic")  # cinematic, documentary, animated
    max_scenes: int = Field(default=15, ge=5, le=30)
    prefer_action: bool = Field(default=False)
    prefer_dialogue: bool = Field(default=False)
    prefer_emotional: bool = Field(default=False)


class TrailerGenerateRequest(BaseModel):
    """Request to generate trailer script and narration"""
    trailer_generation_id: UUID
    include_narration: bool = Field(default=True)
    narration_voice: str = Field(default="male_deep")  # male_deep, female_soft, etc.
    title_cards: Optional[Dict[str, Any]] = Field(default=None)  # series_name, tagline, cta_text


class SceneSelectionRequest(BaseModel):
    """Request to manually select scenes for trailer"""
    trailer_generation_id: UUID
    scene_ids: List[UUID]
    ordering: Optional[List[int]] = Field(default=None)  # Custom ordering


# ==================== Response Schemas ====================

class SceneScore(BaseModel):
    """Individual scene scoring from AI analysis"""
    chapter_id: Optional[UUID] = None
    artifact_id: Optional[UUID] = None
    scene_title: Optional[str] = None
    scene_description: str
    action_score: float
    emotional_score: float
    visual_score: float
    narrative_score: float
    overall_score: float
    is_recommended: bool
    selection_reason: Optional[str] = None


class TrailerAnalyzeResponse(BaseModel):
    """Response from scene analysis"""
    trailer_generation_id: UUID
    project_id: UUID
    status: str
    total_scenes_analyzed: int
    scenes: List[SceneScore]
    recommended_scene_count: int
    estimated_duration_seconds: float
    created_at: datetime


class TrailerScript(BaseModel):
    """Generated trailer script"""
    title: str
    duration_seconds: int
    scenes: List[Dict[str, Any]]  # Scene sequence with timing
    narration_text: Optional[str] = None
    narration_timing: Optional[List[Dict[str, Any]]] = None  # Timing markers


class TrailerGenerateResponse(BaseModel):
    """Response from trailer generation"""
    trailer_generation_id: UUID
    project_id: UUID
    status: str
    script: Optional[TrailerScript] = None
    narration_audio_url: Optional[str] = None
    video_url: Optional[str] = None
    credits_used: int
    created_at: datetime


class TrailerStatusResponse(BaseModel):
    """Trailer generation status check"""
    trailer_generation_id: UUID
    project_id: UUID
    status: str
    progress_percent: float
    current_step: str
    total_scenes: int
    scenes_completed: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


# ==================== Internal Schemas ====================

class SceneAnalysisResult(BaseModel):
    """Internal result from scene analysis"""
    chapter_id: UUID
    chapter_title: str
    chapter_number: int
    scenes: List[SceneScore]
    chapter_summary: str


class TrailerConfig(BaseModel):
    """Configuration for trailer generation"""
    target_duration_seconds: int = 90
    tone: str = "epic"
    style: str = "cinematic"
    max_scenes: int = 15
    selection_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "action": 0.3,
            "emotional": 0.25,
            "visual": 0.25,
            "narrative": 0.2,
        }
    )