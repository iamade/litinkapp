from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AIRequest(BaseModel):
    prompt: str
    context: str | None = None


class AIResponse(BaseModel):
    text: str


class QuizGenerationRequest(BaseModel):
    book_id: int
    num_questions: int = 5
    difficulty: str = "medium"


class AnalyzeChapterSafetyRequest(BaseModel):
    chapter_id: str


class ScriptGenerationRequest(BaseModel):
    chapter_id: str
    script_style: str = "cinematic_movie"
    service_provider: Optional[str] = "deepseek"


class CharacterDetail(BaseModel):
    name: str
    description: str
    personality: str
    role: str


class ScriptMetadata(BaseModel):
    genre: Optional[str] = None
    tone: Optional[str] = None
    target_audience: Optional[str] = None
    estimated_duration: Optional[str] = None


class ScriptResponse(BaseModel):
    chapter_id: str
    script_id: str
    script_name: str
    script: str
    scene_descriptions: List[str]
    characters: List[str]
    character_details: List[CharacterDetail]
    script_style: str
    metadata: ScriptMetadata
    service_used: str


class ScriptRetrievalResponse(BaseModel):
    id: str
    chapter_id: str
    user_id: str
    script_style: str
    script_name: str
    script: str
    scene_descriptions: List[str]
    characters: List[str]
    character_details: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    status: str
    service_used: Optional[str] = None
    created_at: str
    updated_at: str


class EnhanceScenePromptRequest(BaseModel):
    """Request to enhance a scene description for image generation"""

    scene_description: str
    scene_context: Optional[str] = None  # Additional context from the script
    characters_in_scene: Optional[List[str]] = None  # Character names present
    shot_type: Optional[str] = None  # e.g., "close-up", "wide shot"
    style: str = "cinematic"


class EnhanceScenePromptResponse(BaseModel):
    """Response with enhanced scene description"""

    original_description: str
    enhanced_description: str
    detected_shot_type: Optional[str] = None
    suggested_shot_types: List[str] = []
    enhancement_notes: Optional[str] = None


class EmotionalMapEntry(BaseModel):
    """Detailed emotional mapping for a single line of dialogue"""

    line_id: str
    character: str
    dialogue: str
    scene: Optional[int] = 1  # Scene number for grouping audio design
    emotional_state: str  # e.g. "Angry", "Hesitant", "Joyful"
    emotional_intensity: int  # 1-10 scale
    subtext: str  # The hidden meaning or internal thought
    vocal_direction: (
        str  # Instructions for the voice actor/TTS (e.g. "Whispered", "Fast paced")
    )
    facial_expression: (
        str  # Visual cue for video generation (e.g. "Furrowed brow", "Wide smile")
    )
    body_language: Optional[str] = None  # e.g. "Clenching fists", "Looking away"
    sound_effects: List[str] = []  # Ambient sounds and action-based SFX for the scene
    background_music: Optional[str] = None  # Music mood/style description for the scene


class EmotionalMapRequest(BaseModel):
    script_content: str
    characters: List[str]
    script_id: Optional[str] = None


class EmotionalMapResponse(BaseModel):
    entries: List[EmotionalMapEntry]
