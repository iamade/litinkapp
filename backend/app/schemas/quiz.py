from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class QuizBase(BaseModel):
    title: str
    questions: List[Dict[str, Any]]
    difficulty: str = "medium"


class QuizCreate(QuizBase):
    chapter_id: str


class Quiz(QuizBase):
    id: str
    chapter_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuizAttemptBase(BaseModel):
    answers: List[Dict[str, Any]]
    score: int
    time_taken: Optional[int] = None


class QuizAttemptCreate(QuizAttemptBase):
    quiz_id: str


class QuizAttempt(QuizAttemptBase):
    id: str
    user_id: str
    quiz_id: str
    completed_at: datetime

    class Config:
        from_attributes = True