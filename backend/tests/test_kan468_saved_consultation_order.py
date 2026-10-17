import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("MAIL_FROM", "test@example.com")

try:
    from app.api.routes.projects import routes as project_routes
except Exception:
    pytest = __import__("pytest")
    pytest.skip("app imports unavailable in this environment", allow_module_level=True)

import uuid
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.asyncio


class _OwnedProject:
    def __init__(self, user_id):
        self.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        self.user_id = user_id


class _FakeProjectService:
    def __init__(self, session):
        pass

    async def get_project(self, project_id):
        return _OwnedProject(USER_ID)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.last_stmt = None

    async def exec(self, stmt):
        self.last_stmt = stmt
        return _FakeResult(self._rows)


def _artifact(status, created_at, consultation=None):
    content = {"type": "cinematic_universe_consultation", "status": status}
    if consultation is not None:
        content["consultation"] = consultation
    return SimpleNamespace(content=content, created_at=created_at)


USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PID = "11111111-1111-1111-1111-111111111111"


async def test_parse_error_artifact_never_wins(monkeypatch):
    """KAN-468: a stale failed consultation must not shadow successful runs."""
    monkeypatch.setattr(project_routes, "ProjectService", _FakeProjectService)
    good = _artifact("success", "2026-09-16T10:00:00", {"suggested_names": ["Moby World"]})
    stale = _artifact("parse_error", "2026-09-16T12:00:00")
    session = _FakeSession([stale, good])  # newest-first as ordered by the fixed query
    res = await project_routes.get_saved_consultation(
        project_id=PID, current_user=SimpleNamespace(id=USER_ID), session=session
    )
    assert res["consultation"] == {"suggested_names": ["Moby World"]}


async def test_newest_successful_consultation_returned(monkeypatch):
    """KAN-468: with multiple successes the newest (query-ordered first) wins."""
    monkeypatch.setattr(project_routes, "ProjectService", _FakeProjectService)
    older = _artifact("success", "2026-09-10T10:00:00", {"suggested_names": ["Old"]})
    newer = _artifact("success", "2026-09-15T10:00:00", {"suggested_names": ["New"]})
    session = _FakeSession([newer, older])
    res = await project_routes.get_saved_consultation(
        project_id=PID, current_user=SimpleNamespace(id=USER_ID), session=session
    )
    assert res["consultation"] == {"suggested_names": ["New"]}


async def test_no_consultation_returns_none(monkeypatch):
    """KAN-468: only a parse_error artifact present -> no saved consultation."""
    monkeypatch.setattr(project_routes, "ProjectService", _FakeProjectService)
    stale = _artifact("parse_error", "2026-09-16T12:00:00")
    session = _FakeSession([stale])
    res = await project_routes.get_saved_consultation(
        project_id=PID, current_user=SimpleNamespace(id=USER_ID), session=session
    )
    assert res["consultation"] is None


async def test_query_orders_by_created_at_desc(monkeypatch):
    """KAN-468: the query must carry an explicit created_at DESC ordering."""
    monkeypatch.setattr(project_routes, "ProjectService", _FakeProjectService)
    session = _FakeSession([])
    await project_routes.get_saved_consultation(
        project_id=PID, current_user=SimpleNamespace(id=USER_ID), session=session
    )
    compiled = str(session.last_stmt)
    assert "created_at DESC" in compiled or "ORDER BY artifacts.created_at DESC" in compiled


def _real_artifact(consultation, created_at):
    """Artifact in the exact shape written by ConsultationService._store_consultation_result."""
    return SimpleNamespace(
        content={"type": "cinematic_universe_consultation", "consultation": consultation},
        created_at=created_at,
    )


async def test_real_shape_parse_error_never_wins(monkeypatch):
    """KAN-468: persisted shape nests parse_error inside consultation (no top-level status)."""
    monkeypatch.setattr(project_routes, "ProjectService", _FakeProjectService)
    good = _real_artifact({"suggested_names": ["Moby World"]}, "2026-09-16T10:00:00")
    stale = _real_artifact(
        {"suggested_names": ["Untitled Universe"], "ai_commentary": "x", "parse_error": True},
        "2026-09-16T12:00:00",
    )
    session = _FakeSession([stale, good])
    res = await project_routes.get_saved_consultation(
        project_id=PID, current_user=SimpleNamespace(id=USER_ID), session=session
    )
    assert res["consultation"] == {"suggested_names": ["Moby World"]}


async def test_store_skips_parse_error_result():
    """KAN-468: failed consultations are not persisted (write-side guard)."""
    from app.api.services.consultation import ConsultationService

    class _S:
        def __init__(self):
            self.added = []
            self.commits = 0

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            self.commits += 1

    svc = ConsultationService.__new__(ConsultationService)
    svc.session = _S()
    pid = uuid.UUID(PID)
    await svc._store_consultation_result(pid, {"suggested_names": ["U"], "parse_error": True})
    assert svc.session.added == [] and svc.session.commits == 0
    await svc._store_consultation_result(pid, {"suggested_names": ["Ok"]})
    assert len(svc.session.added) == 1 and svc.session.commits == 1
