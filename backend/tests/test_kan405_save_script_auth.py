from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.api.routes.ai import routes


class _Result:
    def __init__(self, *, first=None, all_items=None):
        self._first = first
        self._all_items = all_items or []

    def first(self):
        return self._first

    def all(self):
        return self._all_items


class _Session:
    def __init__(self, *, first=None, all_items=None):
        self._first = first
        self._all_items = all_items or []
        self.exec_count = 0

    async def exec(self, statement):
        self.exec_count += 1
        return _Result(first=self._first, all_items=self._all_items)


@pytest.mark.asyncio
async def test_save_script_auth_allows_book_owner_uuid_id_without_project_lookup():
    user_id = uuid.uuid4()
    book = SimpleNamespace(id=uuid.uuid4(), user_id=user_id, project_id=None)
    chapter = SimpleNamespace(book=book)
    current_user = SimpleNamespace(id=user_id)
    session = _Session()

    assert (
        await routes._user_can_modify_chapter_script(session, chapter, current_user)
        is True
    )
    assert session.exec_count == 0


@pytest.mark.asyncio
async def test_save_script_auth_allows_linked_project_owner_when_book_owner_differs():
    owner_id = uuid.uuid4()
    project_id = uuid.uuid4()
    book = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        project_id=project_id,
    )
    chapter = SimpleNamespace(book=book)
    current_user = SimpleNamespace(id=owner_id)
    session = _Session(all_items=[SimpleNamespace(id=project_id, user_id=owner_id)])

    assert (
        await routes._user_can_modify_chapter_script(session, chapter, current_user)
        is True
    )
    assert session.exec_count == 1


@pytest.mark.asyncio
async def test_save_script_auth_rejects_unrelated_user():
    book = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), project_id=None)
    chapter = SimpleNamespace(book=book)
    current_user = SimpleNamespace(id=uuid.uuid4())
    session = _Session(all_items=[])

    assert (
        await routes._user_can_modify_chapter_script(session, chapter, current_user)
        is False
    )


@pytest.mark.asyncio
async def test_save_script_and_scenes_preserves_not_found_http_exception():
    session = _Session(first=None)
    current_user = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await routes.save_script_and_scenes(
            chapter_id=str(uuid.uuid4()),
            script="INT. TEST - DAY",
            scene_descriptions=["A test scene"],
            characters=[],
            character_details="",
            script_style="cinematic_movie",
            session=session,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Chapter not found"
