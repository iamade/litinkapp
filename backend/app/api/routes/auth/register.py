from fastapi import APIRouter,HTTPException,status,Depends
from app.core.database import get_session
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import get_logger
from app.auth.schema import UserCreateSchema,UserReadSchema
from app.api.services.user_auth import user_auth_service

logger = get_logger()

router = APIRouter(prefix="/auth")

@router.post(
    "/register",
    response_model=UserReadSchema,
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreateSchema,
    session:AsyncSession = Depends(get_session)
):
    """Register a new user with email verification"""
    try:
        # Check if user with this email already exists
        if await user_auth_service.check_user_email_exists(user_data.email, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "User with this email already exists",
                    "action": "Please use a different email or try logging in"
                }
            )
        
        # Create new user (handles password hashing, activation email, etc.)
        new_user = await user_auth_service.create_user(user_data, session)
        
        logger.info(
            f"New user {new_user.email} registered successfully, awaiting activation"
        )
        
        # Format response to match UserReadSchema
        return new_user
    
    except HTTPException as http_ex:
        await session.rollback()
        raise http_ex
    except Exception as e:
        logger.error(f"Failed to register user {user_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Internal server error during registration",
                "action": "Please try again later or contact support"
            }
        )
