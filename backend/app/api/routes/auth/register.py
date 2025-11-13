from fastapi import APIRouter,HTTPException,status,Depends
from app.core.database import get_supabase
from supabase import Client
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
    supabase_client: Client = Depends(get_supabase)
):
    """Register a new user with email verification"""
    try:
        # Check if user with this email already exists
        if await user_auth_service.check_user_email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "User with this email already exists",
                    "action": "Please use a different email or try logging in"
                }
            )
        
        # Create new user (handles password hashing, activation email, etc.)
        new_user = await user_auth_service.create_user(user_data)
        
        logger.info(
            f"New user {new_user['email']} registered successfully, awaiting activation"
        )
        
        # Format response to match UserReadSchema
        return {
            "id": new_user["id"],
            "email": new_user["email"],
            "display_name": new_user["display_name"],
            "avatar_url": new_user.get("avatar_url"),
            "bio": new_user.get("bio"),
            "first_name": new_user["first_name"],
            "middle_name": new_user.get("middle_name"),
            "last_name": new_user["last_name"],
            "roles": new_user["roles"],
            "is_active": new_user["is_active"],
            "is_superuser": new_user.get("is_superuser", False),
            "security_question": new_user["security_question"],
            "security_answer": new_user["security_answer"],
            "account_status": new_user["account_status"],
            "full_name": f"{new_user['first_name']} {new_user.get('middle_name', '')} {new_user['last_name']}".replace("  ", " ").strip()
        }
    
    except HTTPException:
        raise
    
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
