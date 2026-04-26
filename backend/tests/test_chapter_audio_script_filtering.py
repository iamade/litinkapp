import inspect
import symtable
import uuid
from types import SimpleNamespace

import pytest

from app.api.routes.chapters import routes as chapter_routes
from app.audio.schemas import AudioRecord
from app.tasks import audio_tasks


class _EmptyResult:
    def all(self):
        return []


class _CapturingSession:
    def __init__(self):
        self.statements = []

    async def exec(self, statement):
        self.statements.append(statement)
        return _EmptyResult()


async def _allow_chapter_access(chapter_id, user_id, session):
    return {"id": chapter_id, "user_id": str(user_id)}


def test_chapter_audio_task_can_rebind_chapter_id_from_existing_record():
    """Regression: nested task rebinds chapter_id, so it must not be an unbound local."""
    source = inspect.getsource(audio_tasks.generate_chapter_audio_task.run)
    task_table = symtable.symtable(source, "audio_tasks.py", "exec").get_children()[0]
    nested_table = next(
        child
        for child in task_table.get_children()
        if child.get_name() == "async_generate_chapter_audio"
    )

    chapter_symbol = nested_table.lookup("chapter_id")
    assert chapter_symbol.is_nonlocal()
    assert not chapter_symbol.is_local()


def test_audio_record_serializes_script_id_for_script_scoped_frontend_hydration():
    """API response schema must preserve the record_dict script_id field for strict script filtering."""
    record = AudioRecord(
        id="audio-1",
        user_id="user-1",
        chapter_id="chapter-1",
        script_id="script-F",
        audio_type="narrator",
        generation_status="completed",
        metadata={"scene_number": 1},
        created_at="2026-04-25T08:00:00+00:00",
    )

    assert record.model_dump()["script_id"] == "script-F"


async def _captured_audio_statement(monkeypatch, *, chapter_id, script_id):
    monkeypatch.setattr(chapter_routes, "verify_chapter_access", _allow_chapter_access)
    session = _CapturingSession()
    user = SimpleNamespace(id=uuid.uuid4())

    response = await chapter_routes.list_chapter_audio(
        chapter_id=str(chapter_id),
        script_id=str(script_id) if script_id is not None else None,
        session=session,
        current_user=user,
    )

    assert response.total_count == 0
    assert len(session.statements) == 1
    return session.statements[0]


@pytest.mark.asyncio
async def test_script_scoped_audio_filters_same_chapter_different_scripts(monkeypatch):
    """Same chapter/different scripts must compile to different script filters, not an OR fallback."""
    chapter_id = uuid.uuid4()
    script_a = uuid.uuid4()
    script_b = uuid.uuid4()

    stmt_a = await _captured_audio_statement(
        monkeypatch, chapter_id=chapter_id, script_id=script_a
    )
    stmt_b = await _captured_audio_statement(
        monkeypatch, chapter_id=chapter_id, script_id=script_b
    )

    sql_a = str(stmt_a.whereclause)
    sql_b = str(stmt_b.whereclause)
    params_a = stmt_a.compile().params
    params_b = stmt_b.compile().params

    assert "audio_generations.chapter_id" in sql_a
    assert "audio_generations.script_id" in sql_a
    assert " OR " not in sql_a.upper()
    assert " OR " not in sql_b.upper()
    assert params_a["chapter_id_1"] == params_b["chapter_id_1"] == chapter_id
    assert params_a["script_id_1"] == script_a
    assert params_b["script_id_1"] == script_b


@pytest.mark.asyncio
async def test_script_scoped_audio_excludes_null_script_rows(monkeypatch):
    """script_id equality is required for scoped fetches, so NULL script rows do not match."""
    stmt = await _captured_audio_statement(
        monkeypatch, chapter_id=uuid.uuid4(), script_id=uuid.uuid4()
    )

    sql = str(stmt.whereclause)
    assert "audio_generations.script_id =" in sql
    assert "script_id IS NULL" not in sql.upper()
    assert " OR " not in sql.upper()


@pytest.mark.asyncio
async def test_script_scoped_audio_query_is_not_identical_to_chapter_wide_query(monkeypatch):
    """A script-scoped fetch must not accidentally return the chapter-wide result set."""
    chapter_id = uuid.uuid4()

    chapter_wide_stmt = await _captured_audio_statement(
        monkeypatch, chapter_id=chapter_id, script_id=None
    )
    script_scoped_stmt = await _captured_audio_statement(
        monkeypatch, chapter_id=chapter_id, script_id=uuid.uuid4()
    )

    chapter_wide_sql = str(chapter_wide_stmt.whereclause)
    script_scoped_sql = str(script_scoped_stmt.whereclause)

    assert chapter_wide_sql != script_scoped_sql
    assert "audio_generations.script_id" not in chapter_wide_sql
    assert "audio_generations.script_id" in script_scoped_sql
    assert " OR " not in script_scoped_sql.upper()
