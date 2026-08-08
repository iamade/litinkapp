"""
GET /auth/session — lightweight session check with refresh-on-expiry.
"""

import uuid

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.services.user_auth import user_auth_service
from app.auth.utils import create_jwt_token, set_auth_cookies
from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth")


@router.get("/session", status_code=status.HTTP_200_OK)
async def get_session(
    response: Response,
    session: AsyncSession = Depends(get_session),
    access_token: str | None = Cookie(None, alias=settings.COOKIE_ACCESS_NAME),
    refresh_token: str | None = Cookie(None, alias=settings.COOKIE_REFRESH_NAME),
) -> dict:
    user = None

    # Try access_token first
    if access_token:
        try:
            payload = jwt.decode(
                access_token,
                settings.SIGNING_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id_str = payload.get("id")
            if user_id_str:
                user = await user_auth_service.get_user_by_id(
                    uuid.UUID(user_id_str), session, include_inactive=True
                )
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass

    # Try refresh-on-expiry
    if user is None and refresh_token:
        try:
            refresh_payload = jwt.decode(
                refresh_token,
                settings.SIGNING_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if refresh_payload.get("type") != settings.COOKIE_REFRESH_NAME:
                raise jwt.InvalidTokenError("wrong token type")
            refresh_user_id = refresh_payload.get("id")
            if not refresh_user_id:
                raise jwt.InvalidTokenError("missing id")
            user = await user_auth_service.get_user_by_id(
                uuid.UUID(refresh_user_id), session, include_inactive=True
            )
            if user and user.is_active:
                new_access_token = create_jwt_token(user.id)
                set_auth_cookies(response, new_access_token)
                logger.info(f"Session refreshed for {user.email}")
            else:
                user = None
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass

    if user is not None:
        return {
            "is_authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "display_name": user.display_name,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"status": "error", "message": "No valid session", "action": "Please log in"},
    )
