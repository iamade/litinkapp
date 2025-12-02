from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# PlotOverview Schemas
class PlotOverviewBase(BaseModel):
    logline: Optional[str] = Field(None, max_length=1000, description="One-sentence summary of the plot")
    themes: Optional[List[str]] = Field(None, description="Key themes in the story")
    story_type: Optional[str] = Field(None, max_length=100, description="Type of story (e.g., adventure, mystery)")
    script_story_type: Optional[str] = Field(None, max_length=100, description="Script story type (e.g., fiction, non-fiction, documentary)")
    genre: Optional[str] = Field(None, max_length=100, description="Primary genre")
    tone: Optional[str] = Field(None, max_length=100, description="Overall tone of the story")
    audience: Optional[str] = Field(None, max_length=100, description="Target audience")
    setting: Optional[str] = Field(None, max_length=500, description="Story setting")
    generation_method: Optional[str] = Field(None, max_length=100, description="Method used for generation")
    model_used: Optional[str] = Field(None, max_length=100, description="AI model used")
    generation_cost: Optional[Decimal] = Field(None, description="Cost of generation")
    status: str = Field("pending", max_length=50, description="Current status")
    version: int = Field(1, description="Version number")


class PlotOverviewCreate(PlotOverviewBase):
    book_id: str = Field(..., description="ID of the associated book")
    user_id: str = Field(..., description="ID of the user creating the plot overview")


class PlotOverviewUpdate(BaseModel):
    logline: Optional[str] = Field(None, max_length=1000)
    themes: Optional[List[str]] = None
    story_type: Optional[str] = Field(None, max_length=100)
    script_story_type: Optional[str] = Field(None, max_length=100)
    genre: Optional[str] = Field(None, max_length=100)
    tone: Optional[str] = Field(None, max_length=100)
    audience: Optional[str] = Field(None, max_length=100)
    setting: Optional[str] = Field(None, max_length=500)
    generation_method: Optional[str] = Field(None, max_length=100)
    model_used: Optional[str] = Field(None, max_length=100)
    generation_cost: Optional[Decimal] = None
    status: Optional[str] = Field(None, max_length=50)
    version: Optional[int] = None
    
# Character Schemas
class CharacterBase(BaseModel):
    name: str = Field(..., max_length=255, description="Character name")
    role: Optional[str] = Field(None, max_length=100, description="Character's role in the story")
    character_arc: Optional[str] = Field(None, max_length=1000, description="Character's development arc")
    physical_description: Optional[str] = Field(None, max_length=1000, description="Physical appearance")
    personality: Optional[str] = Field(None, max_length=1000, description="Personality traits")
    archetypes: Optional[List[str]] = Field(None, description="Character archetypes")
    want: Optional[str] = Field(None, max_length=500, description="What the character wants")
    need: Optional[str] = Field(None, max_length=500, description="What the character needs")
    lie: Optional[str] = Field(None, max_length=500, description="The lie the character believes")
    ghost: Optional[str] = Field(None, max_length=500, description="Past trauma or ghost")
    image_url: Optional[str] = Field(None, max_length=500, description="URL of character image")
    image_generation_prompt: Optional[str] = Field(None, max_length=1000, description="Prompt used for image generation")
    image_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for generated image")
    generation_method: Optional[str] = Field(None, max_length=100, description="Method used for generation")
    model_used: Optional[str] = Field(None, max_length=100, description="AI model used")



class CharacterResponse(CharacterBase):
    id: str = Field(..., description="Unique identifier")
    plot_overview_id: str
    book_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlotOverviewResponse(PlotOverviewBase):
    id: str = Field(..., description="Unique identifier")
    book_id: str
    user_id: str
    characters: List[CharacterResponse] = Field(..., description="Generated characters")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



class CharacterCreate(CharacterBase):
    plot_overview_id: str = Field(..., description="ID of the associated plot overview")
    book_id: str = Field(..., description="ID of the associated book")
    user_id: str = Field(..., description="ID of the user creating the character")


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    role: Optional[str] = Field(None, max_length=100)
    character_arc: Optional[str] = Field(None, max_length=1000)
    physical_description: Optional[str] = Field(None, max_length=1000)
    personality: Optional[str] = Field(None, max_length=1000)
    archetypes: Optional[List[str]] = None
    want: Optional[str] = Field(None, max_length=500)
    need: Optional[str] = Field(None, max_length=500)
    lie: Optional[str] = Field(None, max_length=500)
    ghost: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    image_generation_prompt: Optional[str] = Field(None, max_length=1000)
    image_metadata: Optional[Dict[str, Any]] = None
    generation_method: Optional[str] = Field(None, max_length=100)
    model_used: Optional[str] = Field(None, max_length=100)




class CharacterArchetypeMatch(BaseModel):
    character_id: str = Field(..., description="ID of the character")
    archetype_id: str = Field(..., description="ID of the matching archetype")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the match")
    matched_traits: List[str] = Field(..., description="Traits that matched")
    analysis: Optional[str] = Field(None, description="Detailed analysis of the match")


# ChapterScript Schemas
class ChapterScriptBase(BaseModel):
    plot_enhanced: bool = Field(False, description="Whether plot has been enhanced")
    character_enhanced: bool = Field(False, description="Whether characters have been enhanced")
    scenes: Optional[Dict[str, Any]] = Field(None, description="Scene descriptions")
    acts: Optional[Dict[str, Any]] = Field(None, description="Act structure")
    beats: Optional[Dict[str, Any]] = Field(None, description="Story beats")
    character_details: Optional[Dict[str, Any]] = Field(None, description="Character details in script")
    character_arcs: Optional[Dict[str, Any]] = Field(None, description="Character arcs in script")
    status: str = Field("pending", max_length=50, description="Current status")
    version: int = Field(1, description="Version number")
    generation_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata from generation")


class ChapterScriptCreate(ChapterScriptBase):
    chapter_id: str = Field(..., description="ID of the associated chapter")
    plot_overview_id: Optional[str] = Field(None, description="ID of the associated plot overview")
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
    description: Optional[str] = Field(None, max_length=1000, description="Archetype description")
    category: Optional[str] = Field(None, max_length=100, description="Archetype category")
    traits: Optional[Dict[str, Any]] = Field(None, description="Key traits of the archetype")
    typical_roles: Optional[Dict[str, Any]] = Field(None, description="Typical roles for this archetype")
    example_characters: Optional[str] = Field(None, max_length=1000, description="Example characters")
    is_active: bool = Field(True, description="Whether the archetype is active")


class CharacterArchetypeResponse(CharacterArchetypeBase):
    id: str = Field(..., description="Unique identifier")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Additional Supporting Schemas
class PlotGenerationRequest(BaseModel):
    book_id: Optional[str] = Field(None, description="ID of the book to generate plot for")
    user_id: Optional[str] = Field(None, description="ID of the user requesting generation")
    prompt: Optional[str] = Field(None, max_length=2000, description="Custom prompt for generation")
    genre: Optional[str] = Field(None, max_length=100, description="Desired genre")
    tone: Optional[str] = Field(None, max_length=100, description="Desired tone")
    audience: Optional[str] = Field(None, max_length=100, description="Target audience")


class PlotGenerationResponse(BaseModel):
    plot_overview: PlotOverviewResponse
    characters: List[CharacterResponse] = Field(..., description="Generated characters")
    message: str = Field(..., description="Response message")


class ArchetypeAnalysisRequest(BaseModel):
    character_id: str = Field(..., description="ID of the character to analyze")
    user_id: str = Field(..., description="ID of the user requesting analysis")


class ImageGenerationRequest(BaseModel):
    character_id: str = Field(..., description="ID of the character for image generation")
    user_id: str = Field(..., description="ID of the user requesting generation")
    prompt: Optional[str] = Field(None, max_length=1000, description="Custom prompt for image generation")
    style: Optional[str] = Field("realistic", max_length=100, description="Desired art style (realistic, cinematic, animated, fantasy)")
    aspect_ratio: Optional[str] = Field("3:4", max_length=10, description="Image aspect ratio (3:4 for portrait, 16:9 for landscape)")