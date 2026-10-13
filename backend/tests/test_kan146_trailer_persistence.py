"""KAN-146 / KAN-147: trailer_config + output_type persistence tests.

Covers:
1. Upload create path: consultation_data agreements.content_type="trailer"
   persists output_type="trailer" + populated trailer_config.
2. Upload create path with no consultation_data: defaults
   (output_type="full_production", trailer_config={}).
3. PATCH path: ProjectUpdate with output_type + partial trailer_config
   persists via update_project (exclude_unset semantics; untouched fields
   are left alone).
4. ProjectUpdate output_type validator rejects unknown values.
5. consultation.py decision/guided prompts allow trailer_promo/trailer and
   include trailer-specific follow-up questions (KAN-147).
"""

import inspect
import json
import os
import uuid
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from app.api.routes.projects import routes as project_routes
from app.auth.models import User
from app.main import app
from app.projects.models import Project, ProjectType, WorkflowMode
from app.projects.schemas import ProjectCreate, ProjectUpdate

pytestmark = pytest.mark.asyncio

OWNER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class _Result:
    def __init__(self, *, first=None):
        self._first = first

    def first(self):
        return self._first


class _FakeSession:
    """Queued-result fake session (mirrors test_kan405 pattern)."""

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
    """Stands in for FileService during create path tests."""

    async def upload_file(self, temp_path, remote_path):
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return f"https://storage.test/{remote_path}"


def _user(user_id=OWNER_ID):
    return User(
        id=user_id,
        email=f"{user_id}@example.test",
        is_active=True,
        full_name="KAN 146 User",
    )


def _upload_file(name="trailer_script.txt", content=b"INT. TEST - DAY"):
    return UploadFile(file=BytesIO(content), filename=name)


def _project_added(fake_session) -> Project:
    projects = [a for a in fake_session.added if isinstance(a, Project)]
    assert projects, "no Project was persisted"
    return projects[-1]


# ---------------------------------------------------------------------------
# 1. Detection helper (create path trailer intent + trailer_config build)
# ---------------------------------------------------------------------------


async def test_detect_trailer_intent_via_agreements_content_type():
    payload = {
        "action_to_take": "cinematic_universe",
        "agreements": {"content_type": "Trailer"},
    }
    output_type, config = project_routes._detect_trailer_intent(payload)
    assert output_type == "trailer"
    assert config == {
        "target_duration_seconds": 90,
        "tone": "epic",
        "style": "cinematic",
    }


async def test_detect_trailer_intent_case_insensitive_with_overrides():
    payload = {
        "recommended_action": "cinematic_universe",
        "agreements": {
            "content_type": "  TRAILER ",
            "tone": "dark",
            "target_duration_seconds": 60,
            "universe_name": "ignored-key",
        },
    }
    output_type, config = project_routes._detect_trailer_intent(payload)
    assert output_type == "trailer"
    # Only the three known keys are honored; extras ignored; casing handled.
    assert config == {
        "target_duration_seconds": 60,
        "tone": "dark",
        "style": "cinematic",
    }


async def test_detect_trailer_intent_via_action_and_recommended():
    assert project_routes._detect_trailer_intent(
        {"action_to_take": "trailer_promo"}
    )[0] == "trailer"
    assert project_routes._detect_trailer_intent(
        {"recommended_action": "promo"}
    )[0] == "trailer"
    assert project_routes._detect_trailer_intent(
        {"agreements": {"content_type": "single_script"}}
    ) == (None, {})
    assert project_routes._detect_trailer_intent(None) == (None, {})


# ---------------------------------------------------------------------------
# 2. Upload create path — full route through create_project_shell
# ---------------------------------------------------------------------------


async def test_upload_create_persists_trailer_output_and_config(monkeypatch):
    fake_session = _FakeSession(results=[])

    async def override_session():
        return fake_session

    async def override_user():
        return _user()

    async def fake_background(*args, **kwargs):
        return None

    monkeypatch.setattr(
        project_routes, "_process_project_upload_background", fake_background
    )
    monkeypatch.setattr(
        "app.core.services.file.FileService", _FakeFileService
    )

    consultation_data = {
        "action_to_take": "cinematic_universe",
        "agreements": {
            "content_type": "trailer",
            "tone": "dark",
            "target_duration_seconds": 60,
        },
    }

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
                files={"files": ("trailer_script.txt", b"INT. TEST - DAY", "text/plain")},
                data={
                    "project_type": "entertainment",
                    "consultation_data": json.dumps(consultation_data),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202, response.text
    assert response.json()["status"] == "processing"

    # KAN-146 core assertion: trailer intent detected via agreements.content_type
    # was persisted on the Project shell (output_type + populated trailer_config).
    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 60,
        "tone": "dark",
        "style": "cinematic",
    }


async def test_create_project_shell_persists_trailer_fields():
    fake_session = _FakeSession(results=[])

    from app.core.services import file as file_mod

    original = file_mod.FileService
    file_mod.FileService = _FakeFileService
    try:
        import app.projects.services as services_mod

        service = services_mod.ProjectService(fake_session)
        project, file_data, is_multi_script = await service.create_project_shell(
            [_upload_file()],
            OWNER_ID,
            ProjectType.ENTERTAINMENT,
            None,
            None,
            output_type="trailer",
            trailer_config={
                "target_duration_seconds": 60,
                "tone": "dark",
                "style": "cinematic",
            },
        )
    finally:
        file_mod.FileService = original

    assert is_multi_script is False
    assert len(file_data) == 1
    assert project.output_type == "trailer"
    assert project.trailer_config == {
        "target_duration_seconds": 60,
        "tone": "dark",
        "style": "cinematic",
    }


async def test_create_project_shell_defaults_without_trailer():
    fake_session = _FakeSession(results=[])

    import app.projects.services as services_mod
    from app.core.services import file as file_mod

    original = file_mod.FileService
    file_mod.FileService = _FakeFileService
    try:
        service = services_mod.ProjectService(fake_session)
        project, _, _ = await service.create_project_shell(
            [_upload_file()],
            OWNER_ID,
            ProjectType.ENTERTAINMENT,
            None,
            None,
        )
    finally:
        file_mod.FileService = original

    assert project.output_type == "full_production"
    assert project.trailer_config == {}


# ---------------------------------------------------------------------------
# 3. Schema create path (POST /projects) — ProjectCreate.trailer_config
# ---------------------------------------------------------------------------


async def test_project_create_schema_persists_trailer_config():
    fake_session = _FakeSession(results=[_Result(first=None)])
    import app.projects.services as services_mod

    service = services_mod.ProjectService(fake_session)
    project_in = ProjectCreate(
        title="Trailer Project",
        project_type=ProjectType.ENTERTAINMENT,
        workflow_mode=WorkflowMode.CREATOR,
        output_type="trailer",
        trailer_config={"tone": "epic", "style": "cinematic"},
    )
    await service.create_project(project_in, OWNER_ID)

    project = _project_added(fake_session)
    assert project.output_type == "trailer"
    assert project.trailer_config == {"tone": "epic", "style": "cinematic"}


# ---------------------------------------------------------------------------
# 4. PATCH path — update_project exclude_unset semantics
# ---------------------------------------------------------------------------


async def test_update_project_persists_output_type_and_trailer_config():
    existing = Project(
        id=uuid.uuid4(),
        user_id=OWNER_ID,
        title="Original Title",
        project_type=ProjectType.ENTERTAINMENT,
        workflow_mode=WorkflowMode.CREATOR,
        output_type="full_production",
        trailer_config={"target_duration_seconds": 90, "tone": "epic"},
        current_step="plot",
    )
    fake_session = _FakeSession(results=[_Result(first=existing), _Result(first=existing)])
    import app.projects.services as services_mod

    service = services_mod.ProjectService(fake_session)
    update = ProjectUpdate(
        output_type="trailer",
        trailer_config={"tone": "dark"},
    )
    updated = await service.update_project(existing.id, update)

    # exclude_unset: only the two provided fields were applied.
    assert updated.title == "Original Title"
    assert updated.current_step == "plot"
    assert updated.output_type == "trailer"
    assert updated.trailer_config == {"tone": "dark"}


async def test_update_project_empty_payload_changes_nothing():
    existing = Project(
        id=uuid.uuid4(),
        user_id=OWNER_ID,
        title="Original Title",
        project_type=ProjectType.ENTERTAINMENT,
        workflow_mode=WorkflowMode.CREATOR,
        output_type="trailer",
        trailer_config={"tone": "epic"},
    )
    fake_session = _FakeSession(results=[_Result(first=existing), _Result(first=existing)])
    import app.projects.services as services_mod

    service = services_mod.ProjectService(fake_session)
    updated = await service.update_project(existing.id, ProjectUpdate())
    assert updated.output_type == "trailer"
    assert updated.trailer_config == {"tone": "epic"}


# ---------------------------------------------------------------------------
# 5. Validator — ProjectUpdate.output_type restricted
# ---------------------------------------------------------------------------


async def test_project_update_output_type_validator_rejects_bogus():
    with pytest.raises(ValidationError):
        ProjectUpdate(output_type="bogus")
    # Valid values pass.
    assert ProjectUpdate(output_type="short_clip").output_type == "short_clip"
    assert ProjectUpdate(output_type="ad").output_type == "ad"
    # None allowed (field omitted from PATCH).
    assert ProjectUpdate().output_type is None


# ---------------------------------------------------------------------------
# 6. consultation.py prompt-level assertions (KAN-147)
# ---------------------------------------------------------------------------


def _consultation_source() -> str:
    from app.api.services import consultation as consultation_mod

    return inspect.getsource(consultation_mod)


async def test_decision_prompt_allows_trailer_promo_and_trailer_content_type():
    src = _consultation_source()
    assert (
        '"action_to_take": "cinematic_universe" | "script_expansion" | '
        '"storyboard" | "trailer_promo" | null' in src
    )
    assert '"content_type": "cinematic_universe" | "single_script" | "ad" | "trailer"' in src


async def test_decision_prompt_includes_trailer_follow_up_questions():
    src = _consultation_source()
    assert 'If action_to_take is "trailer_promo"' in src
    assert "animation style" in src
    assert "30-120" in src
    assert "tone" in src
    assert "key scenes" in src


async def test_guided_analysis_mentions_trailer_questions_for_trailer_promo():
    src = _consultation_source()
    assert (
        'If you recommend or the user chooses "trailer_promo" (Trailer / Promo)' in src
    )
    assert "follow_up_questions MUST cover: animation style" in src


async def test_book_upload_context_suggests_trailer_mode_for_rich_source():
    src = _consultation_source()
    assert "rich source material" in src
    assert "trailer mode" in src


async def test_trailer_promo_label_preserved():
    src = _consultation_source()
    assert '"label": "Trailer / Promo"' in src