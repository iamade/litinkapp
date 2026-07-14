from datetime import datetime, timedelta
from app.core.config import settings
from app.core.emails.base import EmailTemplate
from app.auth.models import User

class AccountLockoutEmail(EmailTemplate):
    template_name = "account_lockout.html"
    template_name_plain = "account_lockout.txt"
    subject = "Account Security Alert - Temporary Lock"


def _duration_label(minutes: int) -> str:
    unit = "minute" if minutes == 1 else "minutes"
    return f"{minutes} {unit}"


async def send_account_lockout_email(
    email: str,
    lockout_time: datetime,
    user: User | None = None,
) -> None:
    unlock_time = lockout_time + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
    lockout_duration_minutes = settings.LOCKOUT_DURATION_MINUTES

    context = {
        "first_name": user.first_name if user else None,
        "display_name": user.display_name if user else None,
        "lockout_duration": _duration_label(lockout_duration_minutes),
        "lockout_duration_minutes": lockout_duration_minutes,
        "lockout_time": lockout_time.strftime("%B %d, %Y at %I:%M %p UTC"),
        "unlock_time": unlock_time.strftime("%B %d, %Y at %I:%M %p UTC"),
        "support_email": settings.SUPPORT_EMAIL,
        "site_name": "LitInkAI",
        "security_action_url": f"{settings.FRONTEND_URL.rstrip('/')}/reset-password",
    }

    await AccountLockoutEmail.send_email(email_to=email, context=context)