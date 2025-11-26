import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Response
from datetime import datetime, timedelta, timezone

from app.core.config import settings
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


def generate_otp(length: int = 6) -> str:
    otp = "".join(random.choices(string.digits, k=length))
    return otp

def generate_password_hash(password: str) -> str:
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


def create_activation_token(id: uuid.UUID) -> str:
    payload = {
        "id": str(id),
        "type": "activation",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACTIVATION_TOKEN_EXPIRATION_MINUTES), "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

def create_jwt_token(id: uuid.UUID, type: str = settings.COOKIE_ACCESS_NAME)-> str:
    if type == settings.COOKIE_ACCESS_NAME:
        expire_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES)
    else:
        expire_delta = timedelta(days= settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES)
        
    payload ={
        "id": str(id),
        "type": type,
        "exp": datetime.now(timezone.utc) + expire_delta,
        "iat":datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SIGNING_KEY, algorithm=settings.JWT_ALGORITHM)

def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str | None = None
) -> None:
    cookie_settings = {
        "path": settings.COOKIE_PATH,
        "secure": settings.COOKIE_SECURE,
        "httponly": settings.COOKIE_HTTP_ONLY,
        "samesite": settings.COOKIE_SAMESITE,
    }
    access_cookie_settings = cookie_settings.copy()
    access_cookie_settings["max_age"]=(
        settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES * 60
    )
    response.set_cookie(
        settings.COOKIE_ACCESS_NAME,
        access_token,
        **access_cookie_settings
    )
    
    if refresh_token:
        refresh_cookie_settings = cookie_settings.copy()
        refresh_cookie_settings["max_age"] =(
            settings.JWT_REFRESH_TOKEN_EXPIRATION_DAYS * 24 * 60 * 60
        )
        response.set_cookie(
            settings.COOKIE_REFRESH_NAME,
            refresh_token,
            **refresh_cookie_settings,
        )
        
    logged_in_cookie_settings = cookie_settings.copy()
    logged_in_cookie_settings["httponly"] = False
    logged_in_cookie_settings["max_age"] = (
        settings.JWT_ACCESS_TOKEN_EXPIRATION_MINUTES * 60
    )
    
    response.set_cookie(
        settings.COOKIE_LOGGED_IN_NAME, "true", **logged_in_cookie_settings,
    )
    
def delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.COOKIE_ACCESS_NAME)
    response.delete_cookie(settings.COOKIE_REFRESH_NAME)
    response.delete_cookie(settings.COOKIE_LOGGED_IN_NAME)

def create_password_reset_token(id: uuid.UUID) -> str:
    payload ={
        "id": str(id),
        "type": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


# async def get_current_superadmin(current_user: dict = Depends(get_current_active_user)) -> dict:
#     """Get current user if they are a superadmin"""
#     user_roles = current_user.get('roles', [])
#     user_email = current_user.get('email')

#     if 'superadmin' not in user_roles and user_email != "support@litinkai.com":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Superadmin access required"
#         )
#     return current_user


# def is_superadmin(user: dict) -> bool:
#     """Check if a user is a superadmin"""
#     user_roles = user.get('roles', [])
#     return 'superadmin' in user_roles or user.get('email') == "support@litinkai.com"

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     """
#     Create JWT access token for user sessions.
#     Used after successful login to maintain user session.
#     """
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.now(timezone.utc) + expires_delta
#     else:
#         expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
#     to_encode.update({
#         "exp": expire,
#         "iat": datetime.now(timezone.utc),
#         "type": "access"
#     })
    
#     return jwt.encode(
#         to_encode,
#         settings.JWT_SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM
#     )

# def create_password_reset_token(user_id: uuid.UUID) -> str:
#     """
#     Create JWT token for password reset flow.
#     Token expires after 1 hour.
#     """
#     payload = {
#         "id": str(user_id),
#         "type": "password_reset",
#         "exp": datetime.now(timezone.utc) + timedelta(hours=1),
#         "iat": datetime.now(timezone.utc),
#     }
    
#     return jwt.encode(
#         payload,
#         settings.JWT_SECRET_KEY,
#         algorithm=settings.JWT_ALGORITHM
#     )
