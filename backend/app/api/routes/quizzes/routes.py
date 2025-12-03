from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid

from app.quizzes.schemas import QuizCreate, QuizAttemptCreate
from app.quizzes.models import Quiz, QuizAttempt
from app.books.models import Chapter

from app.core.database import get_session
from app.core.auth import get_current_active_user

# from app.services.badge_service import BadgeService

router = APIRouter()


@router.post("/", response_model=Quiz, status_code=201)
async def create_quiz(
    quiz_data: QuizCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new quiz, usually linked to a book"""
    try:
        # Fetch chapter to get book_id
        stmt = select(Chapter).where(Chapter.id == quiz_data.chapter_id)
        result = await session.exec(stmt)
        chapter = result.first()

        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        quiz = Quiz(
            chapter_id=uuid.UUID(quiz_data.chapter_id),
            book_id=chapter.book_id,
            title=quiz_data.title,
            questions=quiz_data.questions,
            difficulty=quiz_data.difficulty,
            created_by=uuid.UUID(current_user["id"]),
        )

        session.add(quiz)
        await session.commit()
        await session.refresh(quiz)
        return quiz

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/book/{book_id}", response_model=List[Quiz])
async def get_quizzes_for_book(
    book_id: str, session: AsyncSession = Depends(get_session)
):
    """Get all quizzes associated with a book"""
    try:
        stmt = select(Quiz).where(Quiz.book_id == uuid.UUID(book_id))
        result = await session.exec(stmt)
        quizzes = result.all()
        return quizzes
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{quiz_id}", response_model=Quiz)
async def get_quiz(quiz_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific quiz by its ID"""
    try:
        stmt = select(Quiz).where(Quiz.id == uuid.UUID(quiz_id))
        result = await session.exec(stmt)
        quiz = result.first()

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/attempt", response_model=QuizAttempt, status_code=201)
async def submit_quiz_attempt(
    attempt: QuizAttemptCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Submit a user's attempt at a quiz"""
    try:
        quiz_attempt = QuizAttempt(
            user_id=uuid.UUID(current_user["id"]),
            quiz_id=uuid.UUID(attempt.quiz_id),
            answers=attempt.answers,
            score=attempt.score,
            time_taken=attempt.time_taken,
        )

        session.add(quiz_attempt)
        await session.commit()
        await session.refresh(quiz_attempt)

        # badge_service = BadgeService()
        # await badge_service.check_quiz_badges(session, current_user['id'], attempt.score)

        return quiz_attempt
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/attempts/user/{user_id}", response_model=List[QuizAttempt])
async def get_user_quiz_attempts(
    user_id: str, session: AsyncSession = Depends(get_session)
):
    """Get all quiz attempts for a specific user"""
    try:
        stmt = select(QuizAttempt).where(QuizAttempt.user_id == uuid.UUID(user_id))
        result = await session.exec(stmt)
        attempts = result.all()
        return attempts
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
