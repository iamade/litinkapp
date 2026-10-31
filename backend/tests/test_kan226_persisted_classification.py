"""
KAN-226 regression — persistence-boundary classification and numbering.

LC 2026-10-31 06:54Z: "Add a regression test that OMITS content_type and
asserts the persisted classification." The client (BookUpload.tsx) is frozen
under KAN-332, so it never sends content_type; the server must re-derive the
classification at the persistence boundary and persist the heading-derived
chapter number, not the positional index.

The payload below deliberately OMITS content_type everywhere. The assertion
is on the Chapter objects the save path actually adds to the session.
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
for _k in [
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "REDIS_URL", "CELERY_BROKER_URL",
]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import uuid

import pytest


class _FakeResult:
    def first(self):
        return None

    def one(self):
        return None

    def all(self):
        return []


class _RecordingSession:
    """Minimal session that records what the save path persists."""

    def __init__(self):
        self.added = []

    async def exec(self, *args, **kwargs):
        return _FakeResult()

    async def flush(self):
        return None

    async def refresh(self, obj):
        # assign the DB-generated id the save path reads back
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None

    def add(self, obj):
        self.added.append(obj)


@pytest.fixture
def stub_embeddings(monkeypatch):
    """Key-free: no provider call, no network, no abort."""
    from app.core.services.embeddings import EmbeddingsService

    calls = []

    async def _stub(self, chapter_id, content):
        calls.append(str(chapter_id))
        return None

    monkeypatch.setattr(
        EmbeddingsService, "create_chapter_embeddings", _stub, raising=True
    )
    return calls


async def _run_save(payload):
    from app.api.services.character import CharacterService  # noqa: F401  (import sanity)
    from app.core.services.file import FileService

    session = _RecordingSession()
    service = FileService()
    async for _ in service.confirm_book_structure(
        str(uuid.uuid4()), payload, str(uuid.uuid4()), session
    ):
        pass
    from app.books.models import Chapter

    return [obj for obj in session.added if isinstance(obj, Chapter)]


class TestKan226PersistedClassification:
    """content_type omitted by the client must be re-derived at the boundary."""

    @pytest.mark.asyncio
    async def test_omitted_content_type_is_re_derived_and_persisted(self, stub_embeddings):
        payload = [
            {"title": "Preface", "content": "front matter body"},
            {"title": "Chapter 1", "content": "first real chapter body"},
            {"title": "Chapter 2", "content": "second real chapter body"},
            {"title": "Index", "content": "back matter body"},
        ]
        chapters = await _run_save(payload)
        by_title = {c.title: c for c in chapters}
        assert set(by_title) == {"Preface", "Chapter 1", "Chapter 2", "Index"}
        assert by_title["Preface"].content_type == "front_matter"
        assert by_title["Chapter 1"].content_type == "chapter"
        assert by_title["Chapter 2"].content_type == "chapter"
        assert by_title["Index"].content_type == "back_matter"

    @pytest.mark.asyncio
    async def test_non_chapter_rows_keep_null_chapter_number(self, stub_embeddings):
        payload = [
            {"title": "Preface", "content": "front matter body"},
            {"title": "Chapter 1", "content": "first real chapter body"},
            {"title": "Index", "content": "back matter body"},
        ]
        chapters = await _run_save(payload)
        by_title = {c.title: c for c in chapters}
        assert by_title["Preface"].chapter_number is None
        assert by_title["Index"].chapter_number is None
        assert by_title["Chapter 1"].chapter_number == 1

    @pytest.mark.asyncio
    async def test_heading_derived_number_beats_positional_index(self, stub_embeddings):
        """'CHAPTER LI' is chapter 51, not the 2nd row."""
        payload = [
            {"title": "Chapter 1", "content": "first real chapter body"},
            {"title": "CHAPTER LI", "content": "fifty first real chapter body"},
        ]
        chapters = await _run_save(payload)
        by_title = {c.title: c for c in chapters}
        assert by_title["CHAPTER LI"].chapter_number == 51
        assert by_title["Chapter 1"].chapter_number == 1

    @pytest.mark.asyncio
    async def test_every_persisted_row_carries_a_classification(self, stub_embeddings):
        payload = [
            {"title": "Preface", "content": "front matter body"},
            {"title": "Chapter 1", "content": "first real chapter body"},
        ]
        chapters = await _run_save(payload)
        assert chapters
        for chapter in chapters:
            assert chapter.content_type in {
                "chapter",
                "front_matter",
                "back_matter",
                "metadata",
            }
