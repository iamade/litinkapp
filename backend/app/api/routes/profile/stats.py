from fastapi import APIRouter, Depends
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.books.models import Book

# Using imports as seen in badge.py, assuming they map correctly at runtime
from app.models.progress import UserProgress
from app.models.badge import UserBadge
from app.models.quiz import QuizAttempt

router = APIRouter()


@router.get("/me/stats", response_model=dict)
async def get_user_stats(
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_active_user),
):
    """Get aggregated statistics for the current user."""
    user_id = current_user["id"]

    # Books Progress
    # Count books read (completed_at is not None)
    stmt_books_read = select(func.count()).where(
        UserProgress.user_id == user_id, UserProgress.completed_at != None
    )
    books_read_result = await session.exec(stmt_books_read)
    books_read = books_read_result.one()

    # Count books in progress (completed_at is None)
    stmt_books_in_progress = select(func.count()).where(
        UserProgress.user_id == user_id, UserProgress.completed_at == None
    )
    books_in_progress_result = await session.exec(stmt_books_in_progress)
    books_in_progress = books_in_progress_result.one()

    # Total time spent
    stmt_time = select(func.sum(UserProgress.time_spent)).where(
        UserProgress.user_id == user_id
    )
    time_result = await session.exec(stmt_time)
    total_time_minutes = time_result.one() or 0

    # Badges earned
    stmt_badges = select(func.count()).where(UserBadge.user_id == user_id)
    badges_result = await session.exec(stmt_badges)
    badges_earned = badges_result.one()

    # Quizzes taken and average score
    stmt_quizzes = select(QuizAttempt.score).where(QuizAttempt.user_id == user_id)
    quizzes_result = await session.exec(stmt_quizzes)
    quizzes = quizzes_result.all()

    quizzes_taken = len(quizzes)
    average_quiz_score = sum(quizzes) / quizzes_taken if quizzes_taken > 0 else 0

    # Books uploaded
    stmt_books_uploaded = select(func.count()).where(Book.user_id == user_id)
    books_uploaded_result = await session.exec(stmt_books_uploaded)
    books_uploaded = books_uploaded_result.one()

    stats = {
        "books_read": books_read,
        "books_in_progress": books_in_progress,
        "books_uploaded": books_uploaded,
        "total_time_hours": total_time_minutes // 60,
        "badges_earned": badges_earned,
        "quizzes_taken": quizzes_taken,
        "average_quiz_score": average_quiz_score,
    }

    return stats
