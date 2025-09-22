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
    script: str
    scene_descriptions: List[str]
    characters: List[str]
    character_details: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    status: str
    service_used: Optional[str] = None
    created_at: str
    updated_at: str