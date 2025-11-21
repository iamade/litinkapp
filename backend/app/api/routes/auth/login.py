from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.schema import UserLoginRequestSchema, TokenSchema
# from app.auth.utils import create_access_token
from app.api.services.user_auth import UserAuthService, user_auth_service
from app.core.logging import get_logger

logger = get_logger()
router = APIRouter()

@router.post("/login", response_model=TokenSchema, status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLoginRequestSchema,
    auth_service: UserAuthService = Depends(lambda: user_auth_service)
):
    """
    Login with email and password using Supabase Auth.
    Custom lockout and activation checks are performed.
    """
    email = login_data.email
    password = login_data.password

    # Step 1: Check if user exists in profiles (for custom validation)
    user = await auth_service.get_user_by_email(email, include_inactive=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Invalid credentials",
                "action": "Please check your email and password"
            }
        )

    # Step 2: Custom validation (activation and lockout)
    try:
        await auth_service.validate_user_status(user)
        await auth_service.check_user_lockout(user)
    except HTTPException:
        raise

    # Step 3: Verify password using Supabase Auth
    try:
        # Use Supabase Auth to verify credentials
        auth_response = auth_service.supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not auth_response.user:
            raise Exception("Authentication failed")

    except Exception as e:
        logger.error(f"Supabase auth failed for {email}: {e}")
        # Increment failed login attempts
        await auth_service.increment_failed_login_attempts(user["id"], user_email=user.get("email"))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "message": "Invalid credentials",
                "action": "Please check your email and password"
            }
        )

    # Step 4: Password valid - reset failed attempts
    await auth_service.reset_user_state(user["id"], clear_otp=True)

    # Step 5: Generate custom access token
    access_token = create_access_token({"sub": str(user["id"])})

    logger.info(f"User {email} logged in successfully")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": ""  # Not implementing refresh tokens yet
    }
