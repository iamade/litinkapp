from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.progress import UserProgress
from app.schemas.user import User as UserSchema, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    update_data = user_data.dict(exclude_unset=True)
    await current_user.update(db, **update_data)
    return current_user


@router.get("/me/progress")
async def get_user_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's reading progress"""
    progress_list = await UserProgress.get_by_user(db, str(current_user.id))
    
    # Calculate statistics
    total_books = len(progress_list)
    completed_books = len([p for p in progress_list if p.completed_at])
    total_time = sum(p.time_spent for p in progress_list)
    
    return {
        "total_books": total_books,
        "completed_books": completed_books,
        "total_time_minutes": total_time,
        "progress": progress_list
    }


@router.get("/me/stats")
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user statistics"""
    from app.models.badge import UserBadge
    from app.models.nft import UserCollectible
    from app.models.quiz import QuizAttempt
    
    # Get user progress
    progress_list = await UserProgress.get_by_user(db, str(current_user.id))
    
    # Get user badges
    badges = await UserBadge.get_by_user(db, str(current_user.id))
    
    # Get user collectibles
    collectibles = await UserCollectible.get_by_user(db, str(current_user.id))
    
    # Get quiz attempts
    quiz_attempts = await QuizAttempt.get_by_user(db, str(current_user.id))
    
    # Calculate statistics
    stats = {
        "books_read": len([p for p in progress_list if p.completed_at]),
        "books_in_progress": len([p for p in progress_list if not p.completed_at]),
        "total_time_hours": sum(p.time_spent for p in progress_list) // 60,
        "badges_earned": len(badges),
        "nfts_collected": len(collectibles),
        "quizzes_taken": len(quiz_attempts),
        "average_quiz_score": sum(qa.score for qa in quiz_attempts) / len(quiz_attempts) if quiz_attempts else 0,
        "current_streak": 0,  # TODO: Calculate reading streak
        "total_points": sum(badge.badge.points for badge in badges if hasattr(badge, 'badge'))
    }
    
    return stats


@router.post("/me/progress/{book_id}")
async def update_reading_progress(
    book_id: str,
    chapter: int,
    progress_percentage: int,
    time_spent: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's reading progress for a book"""
    progress = await UserProgress.create_or_update(
        db,
        str(current_user.id),
        book_id,
        current_chapter=chapter,
        progress_percentage=progress_percentage,
        time_spent=time_spent
    )
    
    return {"message": "Progress updated successfully", "progress": progress}