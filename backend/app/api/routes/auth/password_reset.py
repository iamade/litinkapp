from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.auth.schema import PasswordResetRequestSchema, PasswordResetConfirmSchema, SecurityQuestionsSchema
# from app.auth.utils import create_password_reset_token, verify_password
from app.api.services.user_auth import UserAuthService, user_auth_service
from app.core.logging import get_logger
import uuid

logger = get_logger()
router = APIRouter()

class SecurityAnswerVerifySchema(BaseModel):
    email: EmailStr
    security_answer: str

@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: PasswordResetRequestSchema,
    auth_service: UserAuthService = Depends(lambda: user_auth_service)
):
    """
    Step 1: Request password reset - Returns security question
    """
    email = request.email

    # Check if user exists
    user = await auth_service.get_user_by_email(email, include_inactive=True)

    # Always return success to prevent email enumeration
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {email}")
        return {
            "status": "success",
            "message": "If the email exists, you will receive password reset instructions",
            "security_question": None
        }

    # Return security question
    security_question = user.get("security_question", "mother_maiden_name")
    security_question_text = SecurityQuestionsSchema.get_description(
        SecurityQuestionsSchema(security_question)
    )

    logger.info(f"Password reset requested for {email}")

    return
