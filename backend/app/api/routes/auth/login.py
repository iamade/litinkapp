from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.auth.schema import UserLoginRequestSchema
from app.auth.utils import create_jwt_token, set_auth_cookies
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.config import settings

# from app.auth.utils import create_access_token
from app.api.services.user_auth import user_auth_service
from app.core.logging import get_logger

logger = get_logger()
router = APIRouter(prefix="/auth")


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLoginRequestSchema,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    try:
        user = await user_auth_service.get_user_by_email(
            login_data.email, session, include_inactive=True
        )

        if user:
            await user_auth_service.check_user_lockout(user, session)

            if not await user_auth_service.verify_user_password(
                login_data.password, user.hashed_password
            ):
                await user_auth_service.increment_failed_login_attempts(user, session)
                remaining_attempts = (
                    settings.LOGIN_ATTEMPTS - user.failed_login_attempts
                )

                if remaining_attempts > 0:
                    error_message = (
                        f"Invalid credentials. You have {remaining_attempts} "
                        f"attempt{'s' if remaining_attempts != 1 else ''} remaining  before"
                        "your account is temporarily locked."
                    )
                else:
                    error_message = (
                        "Invalid credentials. Your account has been temporarily locked due"
                        f" to too many failed attempts. Please try again after {settings.LOCKOUT_DURATION_MINUTES} minutes."
                    )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "status": "error",
                        "message": error_message,
                        "action": "Please check your email and password and try again",
                        "remaining_attempts": remaining_attempts,
                    },
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "error",
                        "message": "Your account is not activated",
                        "action": "Please activate your account first",
                    },
                )
            await user_auth_service.reset_user_state(user, session, log_action=True)

            access_token = create_jwt_token(user.id)
            refresh_token = create_jwt_token(user.id, type=settings.COOKIE_REFRESH_NAME)
            set_auth_cookies(response, access_token, refresh_token)

            return {
                "message": "Login successful",
                "user": {
                    "email": user.email,
                    "display_name": user.display_name,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "roles": user.roles,
                },
            }
        return {"message": "Something went wrong with your email or password"}

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Failed to verify login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to process login request",
                "action": "Please try again later",
            },
        )
