from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
import uuid


# PlotOverview Schemas
class PlotOverviewBase(BaseModel):
    logline: Optional[str] = Field(
        None, max_length=1000, description="One-sentence summary of the plot"
    )
    original_prompt: Optional[str] = Field(
        None, max_length=2000, description="The original prompt provided by the user"
    )
    creative_directive: Optional[str] = Field(
        None,
        max_length=3000,
        description="Combined directive: prompt (prioritized) + logline, used for all AI generation",
    )
    themes: Optional[List[str]] = Field(None, description="Key themes in the story")
    story_type: Optional[str] = Field(
        None, max_length=100, description="Type of story (e.g., adventure, mystery)"
    )
    script_story_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Script story type (e.g., fiction, non-fiction, documentary)",
    )
    genre: Optional[str] = Field(None, max_length=100, description="Primary genre")
    tone: Optional[str] = Field(
        None, max_length=100, description="Overall tone of the story"
    )
    audience: Optional[str] = Field(None, max_length=100, description="Target audience")
    setting: Optional[str] = Field(None, max_length=500, description="Story setting")
    medium: Optional[str] = Field(
        None,
        max_length=100,
        description="Production medium (Animation, Live Action, Hybrid, Puppetry, Stop-Motion)",
    )
    format: Optional[str] = Field(
        None,
        max_length=100,
        description="Content format (Film, TV Series, Limited Series, Short Film, etc.)",
    )
    vibe_style: Optional[str] = Field(
        None, max_length=200, description="Vibe/Style (Satire, Cinematic, Sitcom, etc.)"
    )
    generation_method: Optional[str] = Field(
        None, max_length=100, description="Method used for generation"
    )
    model_used: Optional[str] = Field(None, max_length=100, description="AI model used")
    generation_cost: Optional[Decimal] = Field(None, description="Cost of generation")
    status: str = Field("pending", max_length=50, description="Current status")
    version: int = Field(1, description="Version number")


class PlotOverviewCreate(PlotOverviewBase):
    book_id: str = Field(..., description="ID of the associated book")
    user_id: str = Field(..., description="ID of the user creating the plot overview")


class PlotOverviewUpdate(BaseModel):
    logline: Optional[str] = Field(None, max_length=1000)
    original_prompt: Optional[str] = Field(None, max_length=2000)
    creative_directive: Optional[str] = Field(None, max_length=3000)
    themes: Optional[List[str]] = None
    story_type: Optional[str] = Field(None, max_length=100)
    script_story_type: Optional[str] = Field(None, max_length=100)
    genre: Optional[str] = Field(None, max_length=100)
    tone: Optional[str] = Field(None, max_length=100)
    audience: Optional[str] = Field(None, max_length=100)
    setting: Optional[str] = Field(None, max_length=500)
    medium: Optional[str] = Field(None, max_length=100)
    format: Optional[str] = Field(None, max_length=100)
    vibe_style: Optional[str] = Field(None, max_length=200)
    generation_method: Optional[str] = Field(None, max_length=100)
    model_used: Optional[str] = Field(None, max_length=100)
    generation_cost: Optional[Decimal] = None
    status: Optional[str] = Field(None, max_length=50)
    version: Optional[int] = None


class ImageRecord(BaseModel):
    id: str
    image_url: Optional[str]
    status: str
    created_at: datetime
    model_used: Optional[str] = None
    generation_method: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: lambda v: str(v),
        }


# Character Schemas
class CharacterBase(BaseModel):
    name: str = Field(..., max_length=255, description="Character name")
    entity_type: str = Field(
        "character", description="Type of entity: 'character' or 'object'"
    )
    role: Optional[str] = Field(
        None, max_length=100, description="Character's role in the story"
    )
    character_arc: Optional[str] = Field(
        None, max_length=1000, description="Character's development arc"
    )
    physical_description: Optional[str] = Field(
        None, max_length=1000, description="Physical appearance"
    )
    personality: Optional[str] = Field(
        None, max_length=1000, description="Personality traits"
    )
    archetypes: Optional[List[str]] = Field(None, description="Character archetypes")
    want: Optional[str] = Field(
        None, max_length=500, description="What the character wants"
    )
    need: Optional[str] = Field(
        None, max_length=500, description="What the character needs"
    )
    lie: Optional[str] = Field(
        None, max_length=500, description="The lie the character believes"
    )
    ghost: Optional[str] = Field(
        None, max_length=500, description="Past trauma or ghost"
    )
    # Voice/Accent fields for video generation prompts
    accent: str = Field(
        "neutral",
        max_length=50,
        description="Voice accent (neutral, nigerian, british, american, indian, australian, jamaican, french, german)",
    )
    voice_characteristics: Optional[str] = Field(
        None,
        max_length=200,
        description="Voice characteristics (e.g., 'deep and authoritative', 'warm and friendly')",
    )
    voice_gender: str = Field(
        "auto",
        max_length=20,
        description="Voice gender (male, female, auto - inferred from character profile)",
    )
    image_url: Optional[str] = Field(
        None, max_length=500, description="URL of character image"
    )
    image_generation_prompt: Optional[str] = Field(
        None, max_length=1000, description="Prompt used for image generation"
    )
    image_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadata for generated image"
    )
    generation_method: Optional[str] = Field(
        None, max_length=100, description="Method used for generation"
    )
    model_used: Optional[str] = Field(None, max_length=100, description="AI model used")


class CharacterResponse(CharacterBase):
    id: Union[str, uuid.UUID] = Field(..., description="Unique identifier")
    plot_overview_id: Union[str, uuid.UUID]
    book_id: Optional[Union[str, uuid.UUID]] = None
    user_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime
    images: List[ImageRecord] = Field(
        default=[], description="History of generated images"
    )

    class Config:
        from_attributes = True
        # Handle asyncpg UUID serialization
        json_encoders = {
            uuid.UUID: lambda v: str(v),
        }


class PlotOverviewResponse(PlotOverviewBase):
    id: str = Field(..., description="Unique identifier")
    book_id: str
    user_id: str
    characters: List[CharacterResponse] = Field(..., description="Generated characters")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("id", "book_id", "user_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class CharacterCreate(CharacterBase):
    plot_overview_id: str = Field(..., description="ID of the associated plot overview")
    book_id: str = Field(..., description="ID of the associated book")
    user_id: str = Field(..., description="ID of the user creating the character")


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    entity_type: Optional[str] = None
    role: Optional[str] = Field(None, max_length=100)
    character_arc: Optional[str] = Field(None, max_length=1000)
    physical_description: Optional[str] = Field(None, max_length=1000)
    personality: Optional[str] = Field(None, max_length=1000)
    archetypes: Optional[List[str]] = None
    want: Optional[str] = Field(None, max_length=500)
    need: Optional[str] = Field(None, max_length=500)
    lie: Optional[str] = Field(None, max_length=500)
    ghost: Optional[str] = Field(None, max_length=500)
    # Voice/Accent fields for video generation prompts
    accent: Optional[str] = Field(None, max_length=50)
    voice_characteristics: Optional[str] = Field(None, max_length=200)
    voice_gender: Optional[str] = Field(None, max_length=20)
    image_url: Optional[str] = Field(None, max_length=500)
    image_generation_prompt: Optional[str] = Field(None, max_length=1000)
    image_metadata: Optional[Dict[str, Any]] = None
    generation_method: Optional[str] = Field(None, max_length=100)
    model_used: Optional[str] = Field(None, max_length=100)


class CharacterArchetypeMatch(BaseModel):
    character_id: str = Field(..., description="ID of the character")
    archetype_id: str = Field(..., description="ID of the matching archetype")
    match_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score of the match"
    )
    matched_traits: List[str] = Field(..., description="Traits that matched")
    analysis: Optional[str] = Field(None, description="Detailed analysis of the match")


# ChapterScript Schemas
class ChapterScriptBase(BaseModel):
    plot_enhanced: bool = Field(False, description="Whether plot has been enhanced")
    character_enhanced: bool = Field(
        False, description="Whether characters have been enhanced"
    )
    scenes: Optional[Dict[str, Any]] = Field(None, description="Scene descriptions")
    acts: Optional[Dict[str, Any]] = Field(None, description="Act structure")
    beats: Optional[Dict[str, Any]] = Field(None, description="Story beats")
    character_details: Optional[Dict[str, Any]] = Field(
        None, description="Character details in script"
    )
    character_arcs: Optional[Dict[str, Any]] = Field(
        None, description="Character arcs in script"
    )
    status: str = Field("pending", max_length=50, description="Current status")
    version: int = Field(1, description="Version number")
    generation_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Metadata from generation"
    )


class ChapterScriptCreate(ChapterScriptBase):
    chapter_id: str = Field(..., description="ID of the associated chapter")
    plot_overview_id: Optional[str] = Field(
        None, description="ID of the associated plot overview"
    )
    script_id: Optional[str] = Field(None, description="ID of the associated script")
    user_id: str = Field(..., description="ID of the user creating the script")


class ChapterScriptUpdate(BaseModel):
    plot_enhanced: Optional[bool] = None
    character_enhanced: Optional[bool] = None
    scenes: Optional[Dict[str, Any]] = None
    acts: Optional[Dict[str, Any]] = None
    beats: Optional[Dict[str, Any]] = None
    character_details: Optional[Dict[str, Any]] = None
    character_arcs: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, max_length=50)
    version: Optional[int] = None
    generation_metadata: Optional[Dict[str, Any]] = None


class ChapterScriptResponse(ChapterScriptBase):
    id: str = Field(..., description="Unique identifier")
    chapter_id: str
    plot_overview_id: Optional[str]
    script_id: Optional[str]
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# CharacterArchetype Schemas
class CharacterArchetypeBase(BaseModel):
    name: str = Field(..., max_length=255, description="Archetype name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Archetype description"
    )
    category: Optional[str] = Field(
        None, max_length=100, description="Archetype category"
    )
    traits: Optional[Dict[str, Any]] = Field(
        None, description="Key traits of the archetype"
    )
    typical_roles: Optional[Dict[str, Any]] = Field(
        None, description="Typical roles for this archetype"
    )
    example_characters: Optional[str] = Field(
        None, max_length=1000, description="Example characters"
    )
    is_active: bool = Field(True, description="Whether the archetype is active")


class CharacterArchetypeResponse(CharacterArchetypeBase):
    id: str = Field(..., description="Unique identifier")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Additional Supporting Schemas
class PlotGenerationRequest(BaseModel):
    book_id: Optional[str] = Field(
        None, description="ID of the book to generate plot for"
    )
    user_id: Optional[str] = Field(
        None, description="ID of the user requesting generation"
    )
    prompt: Optional[str] = Field(
        None, max_length=2000, description="Custom prompt for generation"
    )
    story_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Type of story structure (e.g., hero's journey, mystery)",
    )
    genre: Optional[str] = Field(None, max_length=100, description="Desired genre")
    tone: Optional[str] = Field(None, max_length=100, description="Desired tone")
    audience: Optional[str] = Field(None, max_length=100, description="Target audience")
    refinement_prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="Follow-up prompt to refine/customize an existing plot (e.g., 'generate more characters')",
    )


class ProjectPlotGenerationRequest(BaseModel):
    """Request schema for generating plots from projects (prompt-based, no book required)"""

    project_id: Optional[str] = Field(
        None, description="ID of the project to generate plot for"
    )
    input_prompt: Optional[str] = Field(
        None, max_length=2000, description="The user's creative prompt"
    )
    project_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Type of project (advert, entertainment, etc.)",
    )
    story_type: Optional[str] = Field(
        None, max_length=100, description="Type of story structure"
    )
    genre: Optional[str] = Field(None, max_length=100, description="Desired genre")
    tone: Optional[str] = Field(None, max_length=100, description="Desired tone")
    audience: Optional[str] = Field(None, max_length=100, description="Target audience")
    refinement_prompt: Optional[str] = Field(
        None,
        max_length=2000,
        description="Follow-up prompt to refine/customize an existing plot (e.g., 'Make it Boondocks style')",
    )


class PlotGenerationResponse(BaseModel):
    plot_overview: PlotOverviewResponse
    characters: List[CharacterResponse] = Field(..., description="Generated characters")
    message: str = Field(..., description="Response message")


class ArchetypeAnalysisRequest(BaseModel):
    character_id: str = Field(..., description="ID of the character to analyze")
    user_id: str = Field(..., description="ID of the user requesting analysis")


class ImageGenerationRequest(BaseModel):
    character_id: str = Field(
        ..., description="ID of the character for image generation"
    )
    user_id: str = Field(..., description="ID of the user requesting generation")
    prompt: Optional[str] = Field(
        None, max_length=1000, description="Custom prompt for image generation"
    )
    style: Optional[str] = Field(
        "realistic",
        max_length=100,
        description="Desired art style (realistic, cinematic, animated, fantasy)",
    )
    aspect_ratio: Optional[str] = Field(
        "3:4",
        max_length=10,
        description="Image aspect ratio (3:4 for portrait, 16:9 for landscape)",
    )
