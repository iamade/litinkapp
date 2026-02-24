from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional
from urllib.parse import urlencode
import httpx
import jwt
from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger
from app.auth.models import User
from app.auth.schema import RoleChoicesSchema, AccountStatusSchema
from app.auth.oauth_models import UserOAuth, OAuthProvider
from app.auth.utils import create_jwt_token, set_auth_cookies

router = APIRouter(prefix="/auth")
logger = get_logger()

# Google Configuration
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Microsoft Configuration
MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_USER_INFO_URL = "https://graph.microsoft.com/v1.0/me"


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """
    Redirects the user to the OAuth provider's login page.
    """
    # Build callback URL to match what's in Google Console: /api/v1/auth/{provider}
    if settings.OAUTH_REDIRECT_BASE_URL:
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/{provider}"
    else:
        redirect_uri = f"{settings.API_BASE_URL}/auth/{provider}"

    if provider == OAuthProvider.GOOGLE:
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=500, detail="Google Client ID not configured"
            )

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": "random_state_string",
            "prompt": "select_account",
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return RedirectResponse(url=url)

    elif provider == OAuthProvider.MICROSOFT:
        if not settings.MICROSOFT_CLIENT_ID:
            raise HTTPException(
                status_code=500, detail="Microsoft Client ID not configured"
            )

        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "response_mode": "query",
            "state": "random_state_string",
        }
        url = f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"
        return RedirectResponse(url=url)

    elif provider == OAuthProvider.APPLE:
        raise HTTPException(status_code=501, detail="Apple login not implemented yet")

    raise HTTPException(status_code=404, detail="Provider not supported")


# Callback route matches Google Console: /api/v1/auth/{provider}
@router.get("/{provider}")
async def callback(
    provider: str,
    code: str,
    response: Response,
    request: Request,
    state: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Handles the callback from the OAuth provider.
    """
    # Callback URI must match what's in Google Console: /api/v1/auth/{provider}
    if settings.OAUTH_REDIRECT_BASE_URL:
        redirect_uri = f"{settings.OAUTH_REDIRECT_BASE_URL}/{provider}"
    else:
        redirect_uri = f"{settings.API_BASE_URL}/auth/{provider}"

    user_email = None
    provider_user_id = None
    first_name = None
    last_name = None
    avatar_url = None

    if provider == OAuthProvider.GOOGLE:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=500, detail="Google credentials not configured"
            )

        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_data = {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            token_res = await client.post(GOOGLE_TOKEN_URL, data=token_data)
            if token_res.status_code != 200:
                logger.error(f"Google Token Error: {token_res.text}")
                raise HTTPException(
                    status_code=400, detail="Failed to retrieve token from Google"
                )

            tokens = token_res.json()
            access_token = tokens.get("access_token")

            # Get user info
            user_info_res = await client.get(
                GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_info_res.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to retrieve user info from Google"
                )

            user_info = user_info_res.json()
            user_email = user_info.get("email")
            provider_user_id = user_info.get("sub")
            first_name = user_info.get("given_name")
            last_name = user_info.get("family_name")
            avatar_url = user_info.get("picture")

    elif provider == OAuthProvider.MICROSOFT:
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise HTTPException(
                status_code=500, detail="Microsoft credentials not configured"
            )

        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "scope": "openid email profile User.Read",
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
            }
            token_res = await client.post(MICROSOFT_TOKEN_URL, data=token_data)
            if token_res.status_code != 200:
                logger.error(f"Microsoft Token Error: {token_res.text}")
                raise HTTPException(
                    status_code=400, detail="Failed to retrieve token from Microsoft"
                )

            tokens = token_res.json()
            access_token = tokens.get("access_token")

            user_res = await client.get(
                MICROSOFT_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_res.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to retrieve user info from Microsoft",
                )

            user_info = user_res.json()
            user_email = user_info.get("mail") or user_info.get("userPrincipalName")
            provider_user_id = user_info.get("id")
            first_name = user_info.get("givenName")
            last_name = user_info.get("surname")
    else:
        raise HTTPException(status_code=404, detail="Provider not supported")

    if not user_email:
        raise HTTPException(
            status_code=400, detail="Email not found in provider response"
        )

    # DB Operations
    # 1. Check if OAuth link exists
    stmt = select(UserOAuth).where(
        UserOAuth.provider == provider, UserOAuth.provider_user_id == provider_user_id
    )
    result = await session.exec(stmt)
    user_oauth = result.first()

    user = None
    if user_oauth:
        # User exists via OAuth
        user_stmt = select(User).where(User.id == user_oauth.user_id)
        user_result = await session.exec(user_stmt)
        user = user_result.first()
    else:
        # 2. Check if user with email exists
        user_stmt = select(User).where(User.email == user_email)
        user_result = await session.exec(user_stmt)
        user = user_result.first()

        if user:
            # Link existing user
            new_oauth = UserOAuth(
                user_id=user.id,
                provider=OAuthProvider(provider),
                provider_user_id=provider_user_id,
                email=user_email,
            )
            session.add(new_oauth)
            await session.commit()
        else:
            # 3. Create new user
            user = User(
                email=user_email,
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}".strip()
                or user_email.split("@")[0],
                avatar_url=avatar_url,
                is_active=True,
                account_status=AccountStatusSchema.ACTIVE,
                roles=[RoleChoicesSchema.CREATOR],  # Default role
                hashed_password="",  # No password for OAuth users initially
                onboarding_completed=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            new_oauth = UserOAuth(
                user_id=user.id,
                provider=OAuthProvider(provider),
                provider_user_id=provider_user_id,
                email=user_email,
            )
            session.add(new_oauth)
            await session.commit()

    if not user:
        raise HTTPException(status_code=500, detail="Failed to login/create user")

    # Issue Tokens
    access_token = create_jwt_token(user.id)
    refresh_token = create_jwt_token(user.id, type=settings.COOKIE_REFRESH_NAME)
    set_auth_cookies(response, access_token, refresh_token)

    # Determine redirect URL based on roles/status
    target_url = settings.FRONTEND_URL
    if not user.onboarding_completed:
        target_url = f"{settings.FRONTEND_URL}/onboarding"
    elif "creator" in user.roles:
        target_url = f"{settings.FRONTEND_URL}/creator"
    else:
        target_url = f"{settings.FRONTEND_URL}/dashboard"

    return RedirectResponse(url=target_url)
