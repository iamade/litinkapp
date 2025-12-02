from fastapi import APIRouter, Depends, HTTPException
from typing import List
from supabase import Client

from app.badges.schemas import Badge, BadgeCreate

from app.core.database import get_supabase
from app.core.auth import get_current_active_user

router = APIRouter()


@router.post("/", response_model=Badge, status_code=201)
async def create_badge(
    badge: BadgeCreate,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new badge (admin-only in a real app)"""
    response = supabase_client.table("badges").insert(badge.dict()).execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data[0]


@router.get("/", response_model=List[Badge])
async def get_all_badges(supabase_client: Client = Depends(get_supabase)):
    """Get all available badges"""
    response = supabase_client.table("badges").select("*").execute()
    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)
    return response.data


@router.get("/{badge_id}", response_model=Badge)
async def get_badge(badge_id: int, supabase_client: Client = Depends(get_supabase)):
    """Get a badge by its ID"""
    response = (
        supabase_client.table("badges")
        .select("*")
        .eq("id", badge_id)
        .single()
        .execute()
    )
    if response.error:
        raise HTTPException(status_code=404, detail="Badge not found")
    return response.data


@router.post("/award/{user_id}/{badge_id}", response_model=dict)
async def award_badge_to_user(
    user_id: str,
    badge_id: int,
    supabase_client: Client = Depends(get_supabase),
    current_user: dict = Depends(get_current_active_user),
):
    """Award a badge to a user (admin-only in a real app)"""
    award_data = {"user_id": user_id, "badge_id": badge_id}
    response = supabase_client.table("user_badges").insert(award_data).execute()

    if response.error:
        if "duplicate key value" in response.error.message:
            raise HTTPException(status_code=409, detail="User already has this badge")
        raise HTTPException(status_code=400, detail=response.error.message)

    return {"message": "Badge awarded successfully"}


@router.get("/user/{user_id}", response_model=List[Badge])
async def get_user_badges(
    user_id: str, supabase_client: Client = Depends(get_supabase)
):
    """Get all badges for a specific user"""
    response = (
        supabase_client.table("user_badges")
        .select("badges(*)")
        .eq("user_id", user_id)
        .execute()
    )

    if response.error:
        raise HTTPException(status_code=400, detail=response.error.message)

    user_badges = [item["badges"] for item in response.data if item.get("badges")]

    return user_badges
