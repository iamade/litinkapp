from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body
from supabase import Client
from gotrue.errors import AuthApiError
from postgrest.exceptions import APIError

from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from app.core.config import settings
from app.core.database import get_supabase
from app.schemas.auth import Token, UserLogin, UserRegister
from app.schemas.user import User as UserSchema, UserCreate

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=201)
async def register(
    user_data: UserCreate,
    supabase_client: Client = Depends(get_supabase)
):
    """Register a new user"""
    try:
        response = supabase_client.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "display_name": user_data.display_name
                }
            }
        })
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if response.user is None:
        raise HTTPException(status_code=400, detail="Could not create user.")
    
    # Manually create the user profile after successful auth sign-up
    profile_data = {
        "id": response.user.id,
        "email": user_data.email,
        "display_name": user_data.display_name,
        "role": user_data.role
    }
    
    try:
        profile_response = supabase_client.table('profiles').insert(profile_data).execute()
        
        # Add missing fields to align with the User response model
        new_profile = profile_response.data[0]
        new_profile['is_active'] = True
        new_profile['is_verified'] = True
        
        return new_profile
    except APIError as e:
        # If profile creation fails, we should ideally delete the auth user
        # This is a complex operation, for now, we'll raise an error
        raise HTTPException(status_code=500, detail=f"User created in auth, but profile creation failed: {e.message}")


@router.post("/login", response_model=Token)
async def login(
    user_data: UserLogin,
    supabase: Client = Depends(get_supabase)
):
    """Login user and return access token"""
    try:
        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": auth_response.user.id}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": auth_response.session.refresh_token,
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    supabase: Client = Depends(get_supabase)
):
    """Refresh access token using a refresh token"""
    try:
        response = supabase.auth.refresh_session(refresh_token)
        if not response.session:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": response.user.id}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": response.session.refresh_token,
        }
    except AuthApiError as e:
        raise HTTPException(status_code=401, detail=f"Could not refresh token: {e}")