"""Focused tests for KAN-442: account-lockout email branding, MIME, and copy."""

import os
import re
from datetime import datetime, timezone
from email import message_from_bytes
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent.parent / "app" / "core" / "emails" / "templates"


@pytest.fixture
def lockout_context():
    return {
        "first_name": "Ade",
        "display_name": "Ade Koiki",
        "lockout_duration": "2 minutes",
        "lockout_duration_minutes": 2,
        "lockout_time": "July 14, 2026 at 09:42 PM UTC",
        "unlock_time": "July 14, 2026 at 09:44 PM UTC",
        "support_email": "support@litinkai.com",
        "site_name": "LitInkAI",
        "security_action_url": "https://app.litinkai.com/reset-password",
    }


class TestAccountLockoutTemplate:
    def test_html_has_branded_header(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "LitInkAI" in html
        assert "Lit-Ink Ai" not in html
        assert "Lit-Link Ai" not in html
        assert "Account Security Alert" in html

    def test_html_has_email_safe_lock_icon_no_unicode_emoji(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "&#128274;" not in html
        assert "🔒" not in html
        # Badge is a single 56px table, not an expanded 5x5 or 8x8 pixel grid.
        assert "Email-safe lock icon" in html
        assert 'class="lock-badge"' in html
        assert 'class="lb-cell"' in html
        assert 'class="lb-fill"' in html
        assert "width=\"56\"" in html
        assert "height=\"56\"" in html
        assert html.count("background-color: #B45309") <= 15
        assert 'role="presentation"' in html

    def test_html_lock_badge_mobile_zero_padding_override(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert ".lock-badge td" in html
        assert "padding: 0 !important" in html
        assert ".lock-badge .lb-cell" in html
        # Mobile media query keeps icon cells at 7px despite .email-wrapper td padding.
        assert "max-width: 600px" in html
        assert re.search(r"\.lock-badge\s*,\s*\.lock-badge td", html) is not None

    def test_html_has_security_icon_and_cta(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "Secure my account" in html
        assert "reset-password" in html
        assert 'role="presentation"' in html

    def test_html_duration_has_units(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "2 minutes" in html
        assert "automatically unlocked after 2" not in html

    def test_html_has_personalized_greeting(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "Hi Ade," in html

    def test_html_readable_timestamps(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "July 14, 2026 at 09:42 PM UTC" in html
        assert "July 14, 2026 at 09:44 PM UTC" in html
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", html) is None

    def test_html_escapes_user_input(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        lockout_context["first_name"] = "<script>alert(1)</script>"
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_no_raw_unsubscribe_in_body(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        html = env.get_template("account_lockout.html").render(**lockout_context)
        assert "List-Unsubscribe" not in html
        assert "unsubscribe" not in html.lower()

    def test_plain_text_has_units_and_branding(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        text = env.get_template("account_lockout.txt").render(**lockout_context)
        assert "2 minutes" in text
        assert "LitInkAI" in text
        assert "Lit-Ink Ai" not in text
        assert "Lit-Link Ai" not in text

    def test_plain_text_is_accessible_fallback(self, lockout_context):
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        text = env.get_template("account_lockout.txt").render(**lockout_context)
        assert "Hi Ade," in text
        assert "LOCKED AT" in text
        assert "UNLOCKS AT" in text
        assert "LOCKOUT DURATION" in text
        assert "Secure my account" in text or "SECURE MY ACCOUNT" in text


class TestAccountLockoutMime:
    @pytest.mark.asyncio
    async def test_multipart_alternative_prefers_html(self, lockout_context):
        env_html = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        env_text = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        html = env_html.get_template("account_lockout.html").render(**lockout_context)
        text = env_text.get_template("account_lockout.txt").render(**lockout_context)

        from fastapi_mail.schemas import MessageSchema, MessageType, MultipartSubtypeEnum
        from fastapi_mail.msg import MailMsg

        message = MessageSchema(
            subject="Account Security Alert - Temporary Lock",
            recipients=["user@example.com"],
            body=text,
            subtype=MessageType.plain,
            alternative_body=html,
            multipart_subtype=MultipartSubtypeEnum.alternative,
            headers={
                "X-Mailer": "LitInkAI",
                "List-Unsubscribe": "<mailto:support@litinkai.com?subject=unsubscribe>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        msg = MailMsg(message)
        built = await msg._message("no-reply@litinkai.com")

        # Drill into the multipart/related -> multipart/alternative children
        alternative = built.get_payload()[0]
        assert alternative.get_content_type() == "multipart/alternative"
        parts = alternative.get_payload()
        assert parts[0].get_content_type() == "text/plain"
        assert parts[-1].get_content_type() == "text/html"
        html_payload = parts[-1].get_payload(decode=True).decode("utf-8")
        assert "LitInkAI" in html_payload

    @pytest.mark.asyncio
    async def test_list_unsubscribe_in_headers(self, lockout_context):
        env_html = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        env_text = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        html = env_html.get_template("account_lockout.html").render(**lockout_context)
        text = env_text.get_template("account_lockout.txt").render(**lockout_context)

        from fastapi_mail.schemas import MessageSchema, MessageType, MultipartSubtypeEnum
        from fastapi_mail.msg import MailMsg

        message = MessageSchema(
            subject="Account Security Alert - Temporary Lock",
            recipients=["user@example.com"],
            body=text,
            subtype=MessageType.plain,
            alternative_body=html,
            multipart_subtype=MultipartSubtypeEnum.alternative,
            headers={
                "List-Unsubscribe": "<mailto:support@litinkai.com?subject=unsubscribe>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            },
        )
        msg = MailMsg(message)
        built = await msg._message("no-reply@litinkai.com")
        assert "<mailto:support@litinkai.com?subject=unsubscribe>" in built["List-Unsubscribe"]
        assert "List-Unsubscribe=One-Click" in built["List-Unsubscribe-Post"]
