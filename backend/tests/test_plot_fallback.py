"""KAN-167: plot-lookup project_id fallback regression tests.

Defect (COS 2026-09-29 20:28Z): ``enhance_with_plot_context`` calls
``plot_service.get_plot_overview(user_id=..., book_id=book_id)``. In Creator
mode plots are stored with book_id=project_id, but script generation resolves
artifacts to real chapters and passes the actual book_id, so the lookup misses
and script gen silently loses full-book plot context.

Fix: on book_id miss, look up Project by book_id and retry
``get_plot_overview`` with project.id. These tests pin the three behaviors:

1. book_id hit -> plot returned, fallback NOT fired;
2. book_id miss + Project exists -> project-stored plot returned via retry;
3. book_id miss + no Project -> None result (pre-fix behavior preserved).
"""

import os
import uuid

# Test-safe env BEFORE app imports (KAN-470/471/477 pattern).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.routes.ai.routes import enhance_with_plot_context

pytestmark = pytest.mark.asyncio

USER_ID = "user-1"
BOOK_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_ID = "22222222-2222-2222-2222-222222222222"


def _make_plot(plot_id=BOOK_ID):
    return SimpleNamespace(
        id=plot_id,
        logline="A test logline",
        themes=["redemption"],
        story_type="Novel",
        genre="Fantasy",
        tone="Epic",
        setting="A distant land",
        target_audience="Adults",
        conflict_type="Person vs Self",
        stakes="The kingdom",
    )


def _make_project(project_id=PROJECT_ID, book_id=BOOK_ID):
    return SimpleNamespace(id=project_id, book_id=book_id)


def _make_session(project=None):
    """session.exec(...) -> result.first() returns project (or None)."""
    session = MagicMock()
    session.exec = AsyncMock(return_value=SimpleNamespace(first=lambda: project))
    return session


def _make_services(plot_overview):
    """PlotService/CharacterService factory mocks matching routes.py imports."""
    plot_service = MagicMock()
    plot_service.get_plot_overview = AsyncMock(return_value=plot_overview)
    plot_service_cls = MagicMock(return_value=plot_service)
    character_service = MagicMock()
    character_service.get_characters_by_plot = AsyncMock(return_value=[])
    character_service_cls = MagicMock(return_value=character_service)
    return plot_service_cls, character_service_cls, plot_service


class TestEnhanceWithPlotContext:
    async def test_book_id_hit_no_fallback(self):
        """Plot found by book_id directly: fallback (session.exec) must not fire."""
        plot = _make_plot()
        session = _make_session(project=_make_project())
        plot_cls, char_cls, plot_service = _make_services(plot)
        with patch("app.api.routes.ai.routes.PlotService", plot_cls), patch(
            "app.api.routes.ai.routes.CharacterService", char_cls
        ):
            result = await enhance_with_plot_context(
                session, user_id=USER_ID, book_id=BOOK_ID, chapter_content="Chapter text"
            )
        assert result["plot_info"]["plot_id"] == BOOK_ID
        assert "A test logline" in result["enhanced_content"]
        plot_service.get_plot_overview.assert_awaited_once_with(
            user_id=USER_ID, book_id=BOOK_ID
        )
        session.exec.assert_not_awaited()

    async def test_book_id_miss_project_fallback_returns_plot(self):
        """Miss by book_id + Project links to book: retry with project.id succeeds."""
        plot = _make_plot(plot_id=PROJECT_ID)
        session = _make_session(project=_make_project())
        plot_cls, char_cls, plot_service = _make_services(plot)
        plot_service.get_plot_overview = AsyncMock(
            side_effect=[None, plot]  # book_id miss, then project_id hit
        )
        with patch("app.api.routes.ai.routes.PlotService", plot_cls), patch(
            "app.api.routes.ai.routes.CharacterService", char_cls
        ):
            result = await enhance_with_plot_context(
                session, user_id=USER_ID, book_id=BOOK_ID, chapter_content="Chapter text"
            )
        assert plot_service.get_plot_overview.await_count == 2
        assert plot_service.get_plot_overview.await_args_list[1].kwargs == {
            "user_id": USER_ID,
            "book_id": PROJECT_ID,
        }
        assert result["plot_info"]["plot_id"] == PROJECT_ID
        assert "A test logline" in result["enhanced_content"]
        session.exec.assert_awaited_once()

    async def test_book_id_miss_no_project_returns_none(self):
        """Miss by book_id + no Project: returns None result (pre-fix behavior)."""
        session = _make_session(project=None)
        plot_cls, char_cls, plot_service = _make_services(None)
        with patch("app.api.routes.ai.routes.PlotService", plot_cls), patch(
            "app.api.routes.ai.routes.CharacterService", char_cls
        ):
            result = await enhance_with_plot_context(
                session, user_id=USER_ID, book_id=BOOK_ID, chapter_content="Chapter text"
            )
        assert result == {"enhanced_content": None, "plot_info": None}
        plot_service.get_plot_overview.assert_awaited_once_with(
            user_id=USER_ID, book_id=BOOK_ID
        )
