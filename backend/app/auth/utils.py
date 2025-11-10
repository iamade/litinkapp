import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta, timezone
from supabase import Client

from app.core.config import settings
from app.core.database import get_supabase
from .schema import TokenDataSchema

# Password hashing with Argon2 (primary) and bcrypt (fallback for existing hashes)
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],  # Try argon2 first, fall back to bcrypt
    deprecated="auto",  # Auto-migrate from bcrypt to argon2
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=2,  # 2 iterations
    argon2__parallelism=4,  # 4 threads
    argon2__hash_len=32,  # 32 byte hash
)

# Security
security = HTTPBearer()

def generate_otp(length: int = 6) -> str:
    otp = "".join(random.choices(string.digits, k=length))
    return otp

def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2 (new hashes).
    All new passwords will be hashed with Argon2.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Automatically detects whether hash is argon2 or bcrypt.
    Returns True if password matches, False otherwise.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def generate_display_name()-> str:
    app_name = settings.SITE_NAME
    words = app_name.split()
    prefix = "".join([word[0] for word in words]).upper()
    remaining_length = 12 - len(prefix) - 1
    random_string = "".join(
        random.choices(string.ascii_uppercase + string.digits,k=remaining_length)
        )
    display_name = f"{prefix}-{random_string}"
    
    return display_name


# def create_activation_token(id: uuid.UUID) -> str:
#     payload = {
#         "id": str(id),
#         "type": "activation",
#         "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACTIVATION_TOKEN_EXPIRATION_MINUTES), "iat": datetime.now(timezone.utc),
#     }
    
#     return jwt.encode(
#         payload, settings.JWT_SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM
#     )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase)
):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # Get user from Supabase
    try:
        response = supabase.table('profiles').select('*').eq('id', token_data.user_id).single().execute()
        if not response.data:
            raise credentials_exception
        
        user_data = response.data

        # --- Data Correction ---
        # The User schema expects 'display_name', which the DB provides.
        # Add other missing fields required by the User schema.
        user_data['is_active'] = True
        user_data['is_verified'] = user_data.get('email_verified', False)

        # Ensure email_verified field exists (backward compatibility)
        if 'email_verified' not in user_data:
            user_data['email_verified'] = False
        # -----------------------

        return user_data
    except Exception:
        raise credentials_exception


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current active user"""
    # In Supabase, users are active by default unless explicitly disabled
    return current_user


async def get_current_author(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Get current user if they are an author"""
    user_roles = current_user.get('roles', [])
    if 'author' not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions - author role required"
        )
    return current_user


async def get_current_superadmin(current_user: dict = Depends(get_current_active_user)) -> dict:
    """Get current user if they are a superadmin"""
    user_roles = current_user.get('roles', [])
    user_email = current_user.get('email')

    if 'superadmin' not in user_roles and user_email != "support@litinkai.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user


def is_superadmin(user: dict) -> bool:
    """Check if a user is a superadmin"""
    user_roles = user.get('roles', [])
    return 'superadmin' in user_roles or user.get('email') == "support@litinkai.com"