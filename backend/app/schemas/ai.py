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