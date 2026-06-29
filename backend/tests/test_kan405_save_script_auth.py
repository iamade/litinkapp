import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.ai import routes as ai_routes
from app.auth.models import User
from app.books.models import Book, Chapter
from app.main import app
from app.projects.models import (
    Artifact,
    ArtifactType,
    Project,
    ProjectType,
    WorkflowMode,
)
from app.videos.models import Script


pytestmark = pytest.mark.asyncio


OWNER_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class _Result:
    def __init__(self, *, first=None, one=None):
        self._first = first
        self._one = one

    def first(self):
        return self._first

    def one(self):
        return self._one


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


def _user(user_id=OWNER_ID):
    return User(
        id=user_id,
        email=f"{user_id}@example.test",
        is_active=True,
        full_name="KAN 405 User",
    )


def _book(user_id=OWNER_ID):
    return Book(
        id=uuid.uuid4(),
        user_id=user_id,
        title="KAN 405 Book",
        book_type="epub",
        status="completed",
    )


def _chapter(book):
    chapter = Chapter(
        id=uuid.uuid4(),
        book_id=book.id,
        title="Chapter 1",
        content="Chapter content",
        chapter_number=1,
    )
    chapter.book = book
    return chapter


def _project(user_id=OWNER_ID, book_id=None):
    return Project(
        id=uuid.uuid4(),
        user_id=user_id,
        title="KAN 405 Project",
        project_type=ProjectType.ENTERTAINMENT,
        workflow_mode=WorkflowMode.CREATOR,
        book_id=book_id,
    )


def _artifact(project_id, chapter_number=1):
    return Artifact(
        id=uuid.uuid4(),
        project_id=project_id,
        artifact_type=ArtifactType.CHAPTER,
        content={"chapter_number": chapter_number},
    )


def _payload(chapter_id):
    return {
        "chapter_id": str(chapter_id),
        "script": "INT. KAN-405 TEST - DAY",
        "scene_descriptions": ["A real endpoint test scene"],
        "characters": ["Ada"],
        "character_details": "Ada is persistent.",
        "script_style": "cinematic_movie",
    }


async def _post_save_script(fake_session, user, chapter_id):
    async def override_session():
        return fake_session

    async def override_user():
        return user

    app.dependency_overrides[ai_routes.get_session] = override_session
    app.dependency_overrides[ai_routes.get_current_active_user] = override_user
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.post(
                "/api/v1/ai/save-script-and-scenes",
                json=_payload(chapter_id),
            )
    finally:
        app.dependency_overrides.clear()


def _saved_script(fake_session):
    scripts = [item for item in fake_session.added if isinstance(item, Script)]
    assert len(scripts) == 1
    return scripts[0]


async def test_owner_chapter_succeeds_and_persists_script_with_video_style():
    book = _book(OWNER_ID)
    chapter = _chapter(book)
    session = _FakeSession([_Result(first=chapter), _Result(one=0)])

    response = await _post_save_script(session, _user(OWNER_ID), chapter.id)

    assert response.status_code == 200
    saved = _saved_script(session)
    assert saved.chapter_id == chapter.id
    assert saved.user_id == OWNER_ID
    assert saved.script == "INT. KAN-405 TEST - DAY"
    assert saved.script_style == "cinematic"
    assert saved.video_style == "cinematic"
    assert saved.status == "ready"
    assert session.commits == 1
    assert session.refreshes == 1


async def test_non_owner_chapter_returns_403_not_500_and_does_not_persist():
    book = _book(OTHER_ID)
    chapter = _chapter(book)
    session = _FakeSession([_Result(first=chapter)])

    response = await _post_save_script(session, _user(OWNER_ID), chapter.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to modify this chapter"
    assert session.added == []
    assert session.commits == 0


async def test_owned_artifact_resolves_real_chapter_and_persists_script():
    book = _book(OWNER_ID)
    real_chapter = _chapter(book)
    project = _project(OWNER_ID, book.id)
    artifact = _artifact(project.id, chapter_number=real_chapter.chapter_number)
    session = _FakeSession(
        [
            _Result(first=None),
            _Result(first=artifact),
            _Result(first=project),
            _Result(first=real_chapter),
            _Result(one=0),
        ]
    )

    response = await _post_save_script(session, _user(OWNER_ID), artifact.id)

    assert response.status_code == 200
    saved = _saved_script(session)
    assert saved.chapter_id == real_chapter.id
    assert saved.script_style == "cinematic"
    assert saved.video_style == "cinematic"


async def test_non_owner_artifact_returns_403_not_500_and_does_not_persist():
    project = _project(OTHER_ID)
    artifact = _artifact(project.id)
    session = _FakeSession(
        [_Result(first=None), _Result(first=artifact), _Result(first=project)]
    )

    response = await _post_save_script(session, _user(OWNER_ID), artifact.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this chapter"
    assert session.added == []
    assert session.commits == 0


async def test_prompt_only_owned_project_succeeds_and_persists_virtual_chapter_id():
    project = _project(OWNER_ID)
    session = _FakeSession(
        [_Result(first=None), _Result(first=None), _Result(first=project), _Result(one=0)]
    )

    response = await _post_save_script(session, _user(OWNER_ID), project.id)

    assert response.status_code == 200
    saved = _saved_script(session)
    assert saved.chapter_id == project.id
    assert saved.script_style == "cinematic"
    assert saved.video_style == "cinematic"


async def test_prompt_only_non_owner_project_returns_403_not_500():
    project = _project(OTHER_ID)
    session = _FakeSession(
        [_Result(first=None), _Result(first=None), _Result(first=project)]
    )

    response = await _post_save_script(session, _user(OWNER_ID), project.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this project"
    assert session.added == []


async def test_unknown_id_returns_404_not_500_and_does_not_persist():
    unknown_id = uuid.uuid4()
    session = _FakeSession(
        [_Result(first=None), _Result(first=None), _Result(first=None)]
    )

    response = await _post_save_script(session, _user(OWNER_ID), unknown_id)

    assert response.status_code == 404
    assert response.json()["detail"] == "Chapter not found"
    assert session.added == []
    assert session.commits == 0
