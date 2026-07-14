from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import Optional
from urllib.parse import urlencode, urlsplit, urlunsplit
import httpx
import jwt
import secrets
from app.core.config import settings
from app.core.database import get_session
from app.core.logging import get_logger
from app.auth.models import User
from app.auth.schema import RoleChoicesSchema, AccountStatusSchema
from app.auth.oauth_models import UserOAuth, OAuthProvider
from app.auth.oauth_state import oauth_state_store
from app.auth.utils import create_jwt_token, set_auth_cookies

router = APIRouter(prefix="/auth")
logger = get_logger()

# Google Configuration
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _absolute_oauth_redirect_uri(request: Request, provider: str) -> str:
    """Build the exact absolute callback URI used for both OAuth phases."""
    for base_url in (settings.OAUTH_REDIRECT_BASE_URL, settings.API_BASE_URL):
        parsed = urlsplit(base_url.rstrip('/')) if base_url else None
        if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue

        base_path = parsed.path.rstrip('/')
        callback_path = (
            f"{base_path}/{provider}"
            if base_path.endswith("/auth")
            else f"{base_path}/auth/{provider}"
        )
        candidate = urlunsplit(
            (parsed.scheme, parsed.netloc, callback_path, "", "")
        )
        return candidate

    # Render may not define either optional base URL. Starlette builds this
    # from the incoming host/scheme and includes the mounted /api/v1 prefix.
    derived = str(request.url_for("oauth_callback", provider=provider))
    parsed = urlsplit(derived)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        logger.error("Unable to build an absolute OAuth callback URI")
        raise HTTPException(
            status_code=500,
            detail="OAuth callback URL is not configured correctly",
        )
    return derived


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """
    Redirects the user to the OAuth provider's login page.
    """
    redirect_uri = _absolute_oauth_redirect_uri(request, provider)

    # Generate a cryptographically random per-request CSRF state.
    state = secrets.token_urlsafe(32)
    oauth_state_store.store_state(state)

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
            "state": state,
            "prompt": "select_account",
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return RedirectResponse(url=url)

    elif provider == OAuthProvider.APPLE:
        raise HTTPException(status_code=501, detail="Apple login not implemented yet")

    raise HTTPException(status_code=404, detail="Provider not supported")


# Callback route matches Google Console: /api/v1/auth/{provider}
@router.get("/{provider}", name="oauth_callback")
async def callback(
    provider: str,
    response: Response,
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Handles the callback from the OAuth provider.
    """
    # Providers return an OAuth error instead of ``code`` when the selected
    # account cannot complete sign-in (for example, a removed Google account).
    # Redirect to the app so users see a useful message instead of FastAPI's
    # raw missing-query-parameter JSON response.
    if error or not code:
        logger.warning(
            "OAuth callback rejected for provider=%s error=%s",
            provider,
            error or "missing_code",
        )
        params = {"oauth_error": "account_unavailable"}
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth?{urlencode(params)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Validate OAuth CSRF state before processing the callback.
    if not state:
        logger.error("OAuth callback missing state parameter (provider=%s)", provider)
        raise HTTPException(
            status_code=400,
            detail="Missing state parameter — CSRF validation failed",
        )
    if not oauth_state_store.consume_state(state):
        logger.error(
            "OAuth state validation failed (provider=%s, state_prefix=%s…)",
            provider,
            state[:8] if len(state) > 8 else state,
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state parameter — CSRF validation failed",
        )

    redirect_uri = _absolute_oauth_redirect_uri(request, provider)

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

    # Preserve cookies set by set_auth_cookies on the injected response.
    # A fresh RedirectResponse would drop the Set-Cookie headers, so mutate
    # the existing response object into a 307 redirect instead.
    response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    response.headers["Location"] = target_url
    return response
