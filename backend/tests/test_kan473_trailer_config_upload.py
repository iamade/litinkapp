"""KAN-473: trailer_config must persist on the upload-create path.

Root cause: the upload route declared no `trailer_config` Form param, so the
FE's KAN-147 forward (trailer_config JSON + explicit output_type="trailer")
was silently dropped by FastAPI — and the KAN-146 detection path only ran
when output_type was None. Result: real trailer runs persisted
trailer_config={} (PSQ project 5ce1c598) while output_type persisted.

Fix contract under test:
1. Explicit output_type="trailer" + trailer_config JSON form field: config
   persists with the provided keys merged over defaults.
2. Explicit trailer + malformed/absent form JSON: falls back to consultation
   agreements, then defaults — NEVER empty on a real trailer run.
3. Non-trailer explicit output_type: config stays empty even if form JSON
   present.
4. output_type absent: legacy KAN-146 detection path unchanged.
5. Unknown keys in form JSON are filtered to the known three.
"""

import json
import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.datastructures import UploadFile

from app.api.routes.projects import routes as project_routes
from app.auth.models import User
from app.main import app
from app.projects.models import Project, ProjectType

pytestmark = pytest.mark.asyncio

OWNER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")


class _Result:
    def __init__(self, *, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeSession:
    def __init__(self, results):
        self._results = list(results)
        self.added = []
        self.commits = 0
        self.refreshes = 0

    async def exec(self, statement):
        if not self._results:
            raise AssertionError(f"Unexpected query: {statement}")
        return self._results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        self.refreshes += 1


class _FakeFileService:
    async def upload_file(self, temp_path, remote_path):
        import os

        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return f"https://storage.test/{remote_path}"


def _user(user_id=OWNER_ID):
    return User(
        id=user_id,
        email=f"{user_id}@example.test",
        is_active=True,
        full_name="KAN 473 User",
    )


def _project_added(fake_session) -> Project:
    projects = [a for a in fake_session.added if isinstance(a, Project)]
    assert projects, "no Project was persisted"
    return projects[-1]


async def _post_upload(fake_session, monkeypatch, data: dict):
    """POST /api/v1/projects/upload with faked deps; return the response."""

    async def override_session():
        return fake_session

    async def override_user():
        return _user()

    async def fake_background(*args, **kwargs):
        return None

    monkeypatch.setattr(
        project_routes, "_process_project_upload_background", fake_background
    )
    monkeypatch.setattr("app.core.services.file.FileService", _FakeFileService)

    upload_route = None
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.endswith("/projects/upload") and "POST" in getattr(
            route, "methods", set()
        ):
            upload_route = route
            break
    assert upload_route is not None, "upload route not found"

    app.dependency_overrides[project_routes.get_session] = override_session
    app.dependency_overrides[project_routes.get_current_user] = override_user
    try:
        for dep in upload_route.dependant.dependencies:
            if dep.call in (
                project_routes.get_session,
                project_routes.get_current_user,
            ):
                continue

            async def _credit_override():
                return uuid.uuid4()

            app.dependency_overrides[dep.call] = _credit_override

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/projects/upload",
                files={
                    "files": ("trailer_script.txt", b"INT. TEST - DAY", "text/plain")
                },
                data=data,
            )
    finally:
        app.dependency_overrides.clear()

    return response


# ---------------------------------------------------------------------------
# 1. Explicit trailer run: form-JSON config persists (the ticket's bug)
# ---------------------------------------------------------------------------


async def test_upload_create_explicit_trailer_persists_form_config(monkeypatch):
    """FE KAN-147 forward: output_type=trailer + trailer_config JSON."""
    fake_session = _FakeSession(results=[])
    form_config = {
        "target_duration_seconds": 45,
        "tone": "dramatic",
        "style": "animated",
    }
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "trailer",
            "trailer_config": json.dumps(form_config),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 45,
        "tone": "dramatic",
        "style": "animated",
    }


async def test_upload_create_explicit_trailer_partial_config_gets_defaults(
    monkeypatch,
):
    """Form JSON with a subset of keys: missing keys fall back to defaults."""
    fake_session = _FakeSession(results=[])
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "trailer",
            "trailer_config": json.dumps({"tone": "mysterious"}),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 90,
        "tone": "mysterious",
        "style": "cinematic",
    }


async def test_upload_create_explicit_trailer_malformed_json_never_empty(
    monkeypatch,
):
    """Malformed JSON form field: config must still be non-empty (defaults)."""
    fake_session = _FakeSession(results=[])
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "trailer",
            "trailer_config": "{not-json",
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    # Real trailer run + unusable form JSON → defaults guarantee.
    assert project.trailer_config == {
        "target_duration_seconds": 90,
        "tone": "epic",
        "style": "cinematic",
    }


async def test_upload_create_explicit_trailer_no_form_field_consultation_fallback(
    monkeypatch,
):
    """No form trailer_config: explicit trailer run falls back to consultation
    agreements config (not empty)."""
    fake_session = _FakeSession(results=[])
    consultation_data = {
        "action_to_take": "trailer_promo",
        "agreements": {
            "content_type": "trailer",
            "tone": "romantic",
            "target_duration_seconds": 30,
        },
    }
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "trailer",
            "consultation_data": json.dumps(consultation_data),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 30,
        "tone": "romantic",
        "style": "cinematic",
    }


# ---------------------------------------------------------------------------
# 2. Non-trailer explicit output_type: config stays empty
# ---------------------------------------------------------------------------


async def test_upload_create_explicit_non_trailer_ignores_form_config(monkeypatch):
    fake_session = _FakeSession(results=[])
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "short_clip",
            "trailer_config": json.dumps({"tone": "epic"}),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "short_clip"
    assert project.trailer_config == {}


# ---------------------------------------------------------------------------
# 3. Legacy detection path preserved (output_type absent)
# ---------------------------------------------------------------------------


async def test_upload_create_absent_output_type_still_detects(monkeypatch):
    fake_session = _FakeSession(results=[])
    consultation_data = {
        "action_to_take": "cinematic_universe",
        "agreements": {"content_type": "trailer", "tone": "dark"},
    }
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "consultation_data": json.dumps(consultation_data),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 90,
        "tone": "dark",
        "style": "cinematic",
    }


async def test_upload_create_absent_output_type_no_intent_defaults(monkeypatch):
    fake_session = _FakeSession(results=[])
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={"project_type": "entertainment"},
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "full_production"
    assert project.trailer_config == {}


# ---------------------------------------------------------------------------
# 4. Unknown-key filtering + resolution helper unit tests
# ---------------------------------------------------------------------------


async def test_upload_create_form_config_unknown_keys_filtered(monkeypatch):
    fake_session = _FakeSession(results=[])
    form_config = {
        "target_duration_seconds": 120,
        "universe_name": "SHOULD-BE-FILTERED",
        "arbitrary": "dropped",
    }
    response = await _post_upload(
        fake_session,
        monkeypatch,
        data={
            "project_type": "entertainment",
            "output_type": "trailer",
            "trailer_config": json.dumps(form_config),
        },
    )
    assert response.status_code == 202, response.text

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 120,
        "tone": "epic",
        "style": "cinematic",
    }
    assert "universe_name" not in project.trailer_config
    assert "arbitrary" not in project.trailer_config


def test_resolve_trailer_output_form_json_beats_consultation():
    """Form JSON takes precedence over consultation agreements."""
    resolve = project_routes._resolve_trailer_output
    output_type, config = resolve(
        "trailer",
        json.dumps({"tone": "action"}),
        {"agreements": {"content_type": "trailer", "tone": "romantic"}},
    )
    assert output_type == "trailer"
    assert config["tone"] == "action"


def test_resolve_trailer_output_contract_matrix():
    resolve = project_routes._resolve_trailer_output

    # Absent output_type → legacy detection
    assert resolve(None, None, None) == (None, {})
    assert resolve(None, None, {"action_to_take": "promo"})[0] == "trailer"

    # Explicit non-trailer → empty config regardless
    assert resolve("full_production", json.dumps({"tone": "epic"}), None) == (
        "full_production",
        {},
    )

    # Explicit trailer, nothing provided → defaults, never empty
    ot, cfg = resolve("trailer", None, None)
    assert ot == "trailer"
    assert cfg == {
        "target_duration_seconds": 90,
        "tone": "epic",
        "style": "cinematic",
    }

    # Non-dict JSON values are ignored safely
    ot, cfg = resolve("trailer", json.dumps([1, 2, 3]), None)
    assert ot == "trailer"
    assert cfg["tone"] == "epic"
