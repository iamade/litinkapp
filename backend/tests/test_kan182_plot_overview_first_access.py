"""KAN-182: plot overview first-access create-or-return regression tests.

Pins: (1) first authorized GET returns 200 payload (creates empty overview);
(2) concurrent first GETs persist exactly one row (advisory lock + recheck);
(3) foreign owner still denied 403 and nothing is created.
Session is a fake; the Postgres advisory lock is modelled with an asyncio
lock released at commit (xact-scoped). Not a live-DB concurrency proof.
"""

import os

os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "***")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.services.plot import PlotService
from app.api.routes.plots import routes as plot_routes

pytestmark = pytest.mark.asyncio

OWNER = uuid.uuid4()
PROJECT = uuid.uuid4()


class FakeDB:
    def __init__(self):
        self.rows = []
        self.lock = asyncio.Lock()


class FakeSession:
    def __init__(self, db):
        self.db = db
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        self.pending = []
        self.holds = False

    async def execute(self, stmt, params=None):
        assert "pg_advisory_xact_lock" in str(stmt)
        await self.db.lock.acquire()
        self.holds = True

    def add(self, row):
        self.pending.append(row)

    async def commit(self):
        await asyncio.sleep(0)
        self.db.rows.extend(self.pending)
        self.pending = []
        if self.holds:
            self.holds = False
            self.db.lock.release()


def make_service(db):
    svc = PlotService.__new__(PlotService)
    svc.session = FakeSession(db)

    async def fake_get(user_id, book_id):
        await asyncio.sleep(0)
        for r in db.rows:
            if r.book_id == book_id and r.user_id == user_id:
                return SimpleNamespace(id=str(r.id), book_id=str(r.book_id), status=r.status)
        return None

    svc.get_plot_overview = fake_get
    return svc


async def test_first_access_creates_and_returns_overview():
    db = FakeDB()
    out = await make_service(db).get_or_create_project_plot_overview(OWNER, PROJECT)
    assert out is not None and out.book_id == str(PROJECT)
    assert len(db.rows) == 1 and db.rows[0].status == "pending"
    again = await make_service(db).get_or_create_project_plot_overview(OWNER, PROJECT)
    assert again.id == out.id and len(db.rows) == 1


async def test_concurrent_first_access_single_row():
    db = FakeDB()
    outs = await asyncio.gather(
        *[make_service(db).get_or_create_project_plot_overview(OWNER, PROJECT) for _ in range(8)]
    )
    assert len(db.rows) == 1
    assert len({o.id for o in outs}) == 1


def _route_session(project):
    res = MagicMock()
    res.first.return_value = project
    s = MagicMock()
    s.exec = AsyncMock(return_value=res)
    return s


async def test_route_first_get_200_payload():
    project = SimpleNamespace(id=PROJECT, user_id=OWNER)
    payload = SimpleNamespace(id="x", book_id=str(PROJECT))
    with patch.object(plot_routes, "PlotService") as PS:
        PS.return_value.get_or_create_project_plot_overview = AsyncMock(return_value=payload)
        out = await plot_routes.get_project_plot_overview(
            PROJECT, _route_session(project), SimpleNamespace(id=OWNER)
        )
    assert out is payload


async def test_route_foreign_user_denied_no_create():
    project = SimpleNamespace(id=PROJECT, user_id=OWNER)
    with patch.object(plot_routes, "PlotService") as PS:
        with pytest.raises(HTTPException) as ei:
            await plot_routes.get_project_plot_overview(
                PROJECT, _route_session(project), SimpleNamespace(id=uuid.uuid4())
            )
        assert ei.value.status_code == 403
        PS.return_value.get_or_create_project_plot_overview.assert_not_called()

