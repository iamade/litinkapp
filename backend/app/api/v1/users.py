from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client

from app.core.auth import get_current_active_user, get_password_hash
from app.core.database import get_supabase
from app.models.user import User
from app.models.progress import UserProgress
from app.schemas.user import User as UserSchema, UserUpdate, UserCreate

router = APIRouter()


@router.post("/", response_model=UserSchema, status_code=201)
async def create_user(
    user_data: UserCreate,
    supabase_client: Client = Depends(get_supabase)
):
    """Create a new user (public-facing registration)"""
    
    # Use Supabase Auth to create the user
    response = supabase_client.auth.sign_up({
        "email": user_data.email,
        "password": user_data.password,
        "options": {
            "data": {
                "username": user_data.username,
                "profile_picture_url": user_data.profile_picture_url
            }
        }
    })

    if response.user is None:
        raise HTTPException(status_code=400, detail="Could not create user.")
        
    # After sign_up, Supabase automatically creates an entry in the 'profiles' table
    # via a trigger. We can query for that profile.
    profile_response = supabase_client.table('profiles').select('*').eq('id', response.user.id).single().execute()
    
    if profile_response.error:
        raise HTTPException(status_code=500, detail="User created, but failed to fetch profile.")

    return profile_response.data


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    """Get the current user's profile"""
    return current_user


@router.get("/{user_id}", response_model=UserSchema)
async def get_user_by_id(
    user_id: str,
    supabase_client: Client = Depends(get_supabase)
):
    """Get a user's public profile by ID"""
    response = supabase_client.table('profiles').select('*').eq('id', user_id).single().execute()
    if response.error or not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    return response.data


@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_update: UserUpdate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Update the current user's profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    # Supabase doesn't allow updating the password directly via table update for security.
    # This should be handled via the auth-specific methods if needed.
    if "password" in update_data:
        del update_data["password"]

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    response = supabase_client.table('profiles').update(update_data).eq('id', current_user['id']).execute()

    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
        
    return response.data[0]


@router.get("/me/stats", response_model=dict)
async def get_user_stats(
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Get aggregated statistics for the current user."""
    user_id = current_user['id']
    
    # This is a complex query. We can use RPC calls for this in Supabase for better performance.
    # For now, we do separate queries.
    
    books_progress = supabase_client.table('user_progress').select('completed_at, time_spent').eq('user_id', user_id).execute()
    badges = supabase_client.table('user_badges').select('count').eq('user_id', user_id).execute()
    quizzes = supabase_client.table('quiz_attempts').select('score').eq('user_id', user_id).execute()

    books_read = len([p for p in books_progress.data if p.get('completed_at')])
    total_time_minutes = sum(p.get('time_spent', 0) for p in books_progress.data)
    
    stats = {
        "books_read": books_read,
        "books_in_progress": len(books_progress.data) - books_read,
        "total_time_hours": total_time_minutes // 60,
        "badges_earned": badges.data[0]['count'] if badges.data else 0,
        "quizzes_taken": len(quizzes.data),
        "average_quiz_score": sum(q.get('score', 0) for q in quizzes.data) / len(quizzes.data) if quizzes.data else 0
    }
    
    return stats


@router.post("/me/progress/{book_id}")
async def update_reading_progress(
    book_id: str,
    chapter: int,
    progress_percentage: int,
    time_spent: int = 0,
    db: AsyncSession = Depends(get_supabase),
    current_user: User = Depends(get_current_active_user)
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