from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, Cookie
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.api.services.user_auth import user_auth_service
from app.auth.models import User
from app.core.logging import get_logger

logger = get_logger()


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    access_token: Optional[str] = Cookie(None, alias=settings.COOKIE_ACCESS_NAME),
) -> User:
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            access_token, settings.SIGNING_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_auth_service.get_user_by_id(
        user_id, session, include_inactive=True
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_author(
    current_user: User = Depends(get_current_active_user),
) -> User:
    # For now, we assume any active user can be an author.
    # You can add role checks here if needed.
    return current_user


async def get_current_superadmin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Verify that the current user has superadmin privileges"""
    from app.auth.schema import RoleChoicesSchema

    # Check if user has superadmin role or is_superuser flag
    has_superadmin_role = current_user.has_role(RoleChoicesSchema.SUPER_ADMIN)
    is_superuser = getattr(current_user, "is_superuser", False)

    if not has_superadmin_role and not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required"
        )
    return current_user
