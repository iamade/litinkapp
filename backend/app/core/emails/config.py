from fastapi_mail import FastMail, ConnectionConfig
from pydantic import SecretStr
from pathlib import Path
from app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent / "templates"

if settings.ENVIRONMENT == "production":
    email_conf = ConnectionConfig(
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAILGUN_SMTP_PORT,
        MAIL_SERVER=settings.MAILGUN_SMTP_SERVER,
        MAIL_USERNAME=settings.MAILGUN_SMTP_USERNAME,
        MAIL_PASSWORD=SecretStr(settings.MAILGUN_SMTP_PASSWORD),
        MAIL_SSL_TLS=False,
        MAIL_STARTTLS=True,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TEMPLATE_FOLDER=TEMPLATES_DIR,
    )
else:
    email_conf = ConnectionConfig(
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_USERNAME="",
        MAIL_PASSWORD=SecretStr(""),
        MAIL_SSL_TLS=False,
        MAIL_STARTTLS=False,
        USE_CREDENTIALS=False,
        VALIDATE_CERTS=False,
        TEMPLATE_FOLDER=TEMPLATES_DIR,
    )

fastamail = FastMail(email_conf)
