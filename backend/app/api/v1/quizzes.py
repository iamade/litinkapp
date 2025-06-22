from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.auth import get_current_active_user
from app.core.database import get_supabase
from app.models.user import User
from app.models.quiz import Quiz, QuizAttempt
from app.models.book import Chapter
from app.schemas.quiz import Quiz as QuizSchema, QuizCreate, QuizAttempt as QuizAttemptSchema, QuizAttemptCreate
from app.services.badge_service import BadgeService

router = APIRouter()


@router.post("/", response_model=QuizSchema, status_code=201)
async def create_quiz(
    quiz_data: QuizCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new quiz, usually linked to a book"""
    quiz_dict = quiz_data.dict()
    response = supabase_client.table('quizzes').insert(quiz_dict).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data[0]


@router.get("/book/{book_id}", response_model=List[QuizSchema])
async def get_quizzes_for_book(
    book_id: int,
    supabase_client: Client = Depends(get_supabase)
):
    """Get all quizzes associated with a book"""
    response = supabase_client.table('quizzes').select('*').eq('book_id', book_id).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/{quiz_id}", response_model=QuizSchema)
async def get_quiz(
    quiz_id: int,
    supabase_client: Client = Depends(get_supabase)
):
    """Get a specific quiz by its ID"""
    response = supabase_client.table('quizzes').select('*').eq('id', quiz_id).single().execute()
    if response.error:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return response.data


@router.post("/attempt", response_model=QuizAttemptSchema, status_code=201)
async def submit_quiz_attempt(
    attempt: QuizAttemptCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: User = Depends(get_current_active_user)
):
    """Submit a user's attempt at a quiz"""
    attempt_data = attempt.dict()
    attempt_data['user_id'] = current_user.id
    
    # Here you might add logic to calculate the score before saving.
    # For simplicity, we assume the client calculates the score.
    
    response = supabase_client.table('quiz_attempts').insert(attempt_data).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
        
    return response.data[0]


@router.get("/attempts/user/{user_id}", response_model=List[QuizAttemptSchema])
async def get_user_quiz_attempts(
    user_id: int,
    supabase_client: Client = Depends(get_supabase)
):
    """Get all quiz attempts for a specific user"""
    response = supabase_client.table('quiz_attempts').select('*').eq('user_id', user_id).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data