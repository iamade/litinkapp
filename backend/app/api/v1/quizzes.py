from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.quiz import Quiz, QuizAttempt
from app.models.book import Chapter
from app.schemas.quiz import Quiz as QuizSchema, QuizCreate, QuizAttempt as QuizAttemptSchema, QuizAttemptCreate
from app.services.badge_service import BadgeService

router = APIRouter()


@router.post("/", response_model=QuizSchema)
async def create_quiz(
    quiz_data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new quiz"""
    # Verify chapter exists and user has access
    chapter = await Chapter.get_by_id(db, quiz_data.chapter_id)
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found"
        )
    
    quiz = await Quiz.create(db, **quiz_data.dict())
    return quiz


@router.get("/chapter/{chapter_id}", response_model=List[QuizSchema])
async def get_chapter_quizzes(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quizzes for a chapter"""
    quizzes = await Quiz.get_by_chapter(db, chapter_id)
    return quizzes


@router.post("/attempts", response_model=QuizAttemptSchema)
async def submit_quiz_attempt(
    attempt_data: QuizAttemptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a quiz attempt"""
    # Calculate score
    quiz = await Quiz.get_by_id(db, attempt_data.quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Create quiz attempt
    attempt = await QuizAttempt.create(
        db,
        user_id=str(current_user.id),
        **attempt_data.dict()
    )
    
    # Check for badge eligibility
    badge_service = BadgeService()
    await badge_service.check_quiz_badges(db, current_user.id, attempt.score)
    
    return attempt


@router.get("/attempts/me", response_model=List[QuizAttemptSchema])
async def get_my_quiz_attempts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's quiz attempts"""
    attempts = await QuizAttempt.get_by_user(db, str(current_user.id))
    return attempts


@router.get("/{quiz_id}", response_model=QuizSchema)
async def get_quiz(
    quiz_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quiz by ID"""
    quiz = await Quiz.get_by_id(db, quiz_id)
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    return quiz