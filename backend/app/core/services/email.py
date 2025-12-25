import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email service that supports both Mailpit (development) and Mailgun (production)
    """

    def __init__(self):
        self.mail_service = settings.MAIL_SERVICE.lower()
        logger.info(f"Initialized EmailService with provider: {self.mail_service}")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using the configured email service

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text version of the email (optional)

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            if self.mail_service == "mailpit":
                return await self._send_via_mailpit(to_email, subject, html_content, text_content)
            elif self.mail_service == "mailgun":
                return await self._send_via_mailgun(to_email, subject, html_content, text_content)
            else:
                logger.error(f"Unknown email service: {self.mail_service}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def _send_via_mailpit(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Mailpit SMTP server (development)"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.MAILGUN_SENDER_NAME} <{settings.MAILGUN_SENDER_EMAIL}>"
            msg['To'] = to_email

            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)

            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)

            with smtplib.SMTP(settings.MAILPIT_SMTP_HOST, settings.MAILPIT_SMTP_PORT) as server:
                server.send_message(msg)

            logger.info(f"Email sent via Mailpit to {to_email}")
            logger.info(f"View email at: http://{settings.MAILPIT_SMTP_HOST}:{settings.MAILPIT_WEB_UI_PORT}")
            return True

        except Exception as e:
            logger.error(f"Mailpit email send failed: {e}")
            return False

    async def _send_via_mailgun(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Mailgun API (production)"""
        if not settings.MAILGUN_API_KEY or not settings.MAILGUN_DOMAIN:
            logger.error("Mailgun credentials not configured")
            return False

        try:
            url = f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages"
            auth = ("api", settings.MAILGUN_API_KEY)

            data = {
                "from": f"{settings.MAILGUN_SENDER_NAME} <{settings.MAILGUN_SENDER_EMAIL}>",
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }

            if text_content:
                data["text"] = text_content

            async with httpx.AsyncClient() as client:
                response = await client.post(url, auth=auth, data=data, timeout=30.0)

                if response.status_code == 200:
                    logger.info(f"Email sent via Mailgun to {to_email}")
                    return True
                else:
                    logger.error(f"Mailgun API error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Mailgun email send failed: {e}")
            return False

    async def send_verification_email(self, to_email: str, verification_link: str) -> bool:
        """Send email verification email"""
        subject = "Verify Your Email - Litink"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Litink!</h1>
                </div>
                <div class="content">
                    <p>Hi there,</p>
                    <p>Thank you for signing up for Litink! To complete your registration and start creating amazing content, please verify your email address.</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #4F46E5;">{verification_link}</p>
                    <p>This verification link will expire in 24 hours.</p>
                    <p>If you didn't create an account with Litink, you can safely ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Litink. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Welcome to Litink!

        Thank you for signing up for Litink! To complete your registration and start creating amazing content, please verify your email address.

        Verify your email by visiting this link:
        {verification_link}

        This verification link will expire in 24 hours.

        If you didn't create an account with Litink, you can safely ignore this email.

        © 2025 Litink. All rights reserved.
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_welcome_email(self, to_email: str, display_name: str) -> bool:
        """Send welcome email after successful verification"""
        subject = "Welcome to Litink - Let's Get Started!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #10B981; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Email Verified!</h1>
                </div>
                <div class="content">
                    <p>Hi {display_name},</p>
                    <p>Your email has been successfully verified! You're all set to start using Litink.</p>
                    <p>Here's what you can do now:</p>
                    <ul>
                        <li>Upload your first book or content</li>
                        <li>Generate AI-powered scripts and videos</li>
                        <li>Explore our learning and entertainment modes</li>
                        <li>Join our creative community</li>
                    </ul>
                    <p style="text-align: center;">
                        <a href="{settings.FRONTEND_URL}/dashboard" class="button">Go to Dashboard</a>
                    </p>
                    <p>Need help getting started? Check out our documentation or reach out to our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Litink. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Email Verified!

        Hi {display_name},

        Your email has been successfully verified! You're all set to start using Litink.

        Here's what you can do now:
        - Upload your first book or content
        - Generate AI-powered scripts and videos
        - Explore our learning and entertainment modes
        - Join our creative community

        Visit your dashboard: {settings.FRONTEND_URL}/dashboard

        Need help getting started? Check out our documentation or reach out to our support team.

        © 2025 Litink. All rights reserved.
        """

        return await self.send_email(to_email, subject, html_content, text_content)


# Singleton instance
email_service = EmailService()
