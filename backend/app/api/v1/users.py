from fastapi import APIRouter, Depends, HTTPException
from typing import List
from supabase import Client

from app.schemas import User, UserCreate, UserUpdate
from app.core.database import get_supabase
from app.core.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=User, status_code=201)
async def create_user(
    user_data: UserCreate,
    supabase_client: Client = Depends(get_supabase)
):
    """Create a new user (public-facing registration)"""
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
    
    profile_response = supabase_client.table('profiles').select('*').eq('id', response.user.id).single().execute()
    
    if profile_response.error:
        raise HTTPException(status_code=500, detail="User created, but failed to fetch profile.")

    return profile_response.data

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    """Get the current user's profile"""
    return current_user

@router.get("/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: str,
    supabase_client: Client = Depends(get_supabase)
):
    """Get a user's public profile by ID"""
    response = supabase_client.table('profiles').select('*').eq('id', user_id).single().execute()
    if response.error or not response.data:
        raise HTTPException(status_code=404, detail="User not found")
    return response.data

@router.put("/me", response_model=User)
async def update_user_me(
    user_update: UserUpdate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user)
):
    """Update the current user's profile"""
    update_data = user_update.dict(exclude_unset=True)
    
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
    
    books_progress_req = supabase_client.table('user_progress').select('completed_at, time_spent').eq('user_id', user_id).execute()
    badges_req = supabase_client.table('user_badges').select('badge_id', count='exact').eq('user_id', user_id).execute()
    quizzes_req = supabase_client.table('quiz_attempts').select('score').eq('user_id', user_id).execute()

    books_progress = books_progress_req.data
    badges_count = badges_req.count if badges_req.count is not None else 0
    quizzes = quizzes_req.data

    books_read = len([p for p in books_progress if p.get('completed_at')])
    total_time_minutes = sum(p.get('time_spent', 0) for p in books_progress)
    
    stats = {
        "books_read": books_read,
        "books_in_progress": len(books_progress) - books_read,
        "total_time_hours": total_time_minutes // 60,
        "badges_earned": badges_count,
        "quizzes_taken": len(quizzes),
        "average_quiz_score": sum(q.get('score', 0) for q in quizzes) / len(quizzes) if quizzes else 0
    }
    
    return stats