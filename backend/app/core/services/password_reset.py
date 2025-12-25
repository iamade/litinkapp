import uuid
from app.core.config import settings
from app.core.emails.base import EmailTemplate
from app.auth.utils import create_password_reset_token


class PasswordResetEmail(EmailTemplate):
    template_name = "password_reset.html"
    template_name_plain = "password_reset.txt"
    subject = "Reset Your password"


async def send_password_reset_email(email: str, user_id: uuid.UUID) -> None:
    reset_token = create_password_reset_token(user_id)

    # Link to FRONTEND with token - not backend API
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    context = {
        "reset_url": reset_url,
        "expiry_time": settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES,
        "site_name": settings.SITE_NAME,
        "support_email": settings.SUPPORT_EMAIL,
    }

    await PasswordResetEmail.send_email(email_to=email, context=context)
