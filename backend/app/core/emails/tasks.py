import asyncio
from fastapi_mail import MessageSchema, MessageType, MultipartSubtypeEnum
from app.tasks.celery_app import celery_app
from app.core.logging import get_logger
from app.core.emails.config import fastamail
from app.core.config import settings

logger = get_logger()


@celery_app.task(
    name="send_email_task",
    bind=True,
    max_retries=3,
    soft_time_limit=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
)
def send_email_task(
    self, *, recipients: list[str], subject: str, html_content: str, plain_content: str
) -> bool:
    try:
        # Build headers that improve email deliverability and reduce spam scoring
        headers = {
            "X-Mailer": f"{settings.SITE_NAME}",
            "X-Priority": "3",  # Normal priority
            "MIME-Version": "1.0",
        }
        # Add List-Unsubscribe if support email is configured (required by Gmail/Yahoo)
        if settings.SUPPORT_EMAIL:
            headers["List-Unsubscribe"] = (
                f"<mailto:{settings.SUPPORT_EMAIL}?subject=unsubscribe>"
            )
            headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            body=html_content,
            subtype=MessageType.html,
            alternative_body=plain_content,
            multipart_subtype=MultipartSubtypeEnum.alternative,
            headers=headers,
        )
        asyncio.run(fastamail.send_message(message))
        logger.info(f"Email successfully sent to {recipients} with subject {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: Error: {str(e)}")
        return False
