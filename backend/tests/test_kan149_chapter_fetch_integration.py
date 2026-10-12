"""KAN-149 (c17813 still-owed): real-Book-row chapter-fetch integration test.

Suite-gap context: the 5-test adapter suite (test_kan149_highlight_scene_selection.py)
bypasses the real chapter-fetch path. This test locks the behavioral surface the
2026-10-12 re-drive proved live: TrailerSceneService._get_project_chapters must fetch
ALL chapters of EVERY book in a project, ordered by chapter_number, from REAL
database rows.

Real-row discipline (c17813) + NO-live-DB-write constraint (LC 2026-10-12):
rows live in a REAL Postgres engine, but ONLY in an explicitly-provided
DISPOSABLE database (TEST_DATABASE_URL) - never a live/staging DB. The test
SKIPS with instructions when TEST_DATABASE_URL is absent:

    docker run --rm -d --name kan149-test-pg \
        -e POSTGRES_PASSWORD=test -p 55432:5432 pgvector/pgvector:pg16
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:test@localhost:55432/postgres \
        python -m pytest tests/test_kan149_chapter_fetch_integration.py -q
"""
import os
import uuid

# Test-safe env BEFORE app imports (KAN-470/471/477 pattern per test_plot_fallback.py).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"):
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="real-row test requires a disposable postgres via TEST_DATABASE_URL (see module docstring); live DBs are never written",
)
async def test_get_project_chapters_real_rows_complete_and_ordered():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlmodel import SQLModel
    from sqlmodel.ext.asyncio.session import AsyncSession

    import app.auth.models  # noqa: F401 - register User table for FK resolution
    import app.projects.models  # noqa: F401 - register Project table for FK resolution
    from app.books.models import Book, Chapter
    from app.trailers.service import TrailerSceneService

    engine = create_async_engine(TEST_DATABASE_URL)

    # create_type=False PG enums are owned by app migrations; pre-create them
    # in the disposable DB so SQLModel.metadata.create_all can resolve them.
    from sqlalchemy import text

    from app.projects.models import ArtifactType
    from app.trailers.models import TrailerStatus, SelectionMethod

    async def _ensure_enum(conn, name, pyenum):
        q = chr(39)
        vals = ', '.join(q + v.value + q for v in pyenum)
        d = chr(36)  # dollar sign for DO $$ ... $$ block
        ddl = 'DO ' + d*2 + ' BEGIN CREATE TYPE ' + name + ' AS ENUM (' + vals + '); '
        ddl += 'EXCEPTION WHEN duplicate_object THEN NULL; END ' + d*2 + ';'
        await conn.execute(text(ddl))

    async with engine.begin() as conn:
        # pgvector owns the VECTOR type (book-content chunk embeddings use
        # VECTOR(1536)); the pgvector image ships the extension but never
        # installs it into a new database. Without this line, create_all
        # fails with UndefinedObjectError: type "vector" does not exist
        # (KAN-149 c17890/c17905 runnability defect).
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await _ensure_enum(conn, 'artifact_type', ArtifactType)
        await _ensure_enum(conn, 'trailer_status', TrailerStatus)
        await _ensure_enum(conn, 'selection_method', SelectionMethod)



    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        async with AsyncSession(engine) as session:
            book1 = Book(
                id=uuid.uuid4(), user_id=user_id, title="KAN-149 IT B1",
                book_type="fiction", project_id=project_id, total_chapters=5,
            )
            book2 = Book(
                id=uuid.uuid4(), user_id=user_id, title="KAN-149 IT B2",
                book_type="fiction", project_id=project_id, total_chapters=3,
            )
            session.add(book1)
            session.add(book2)
            # Insert chapters OUT of order to prove order_by(chapter_number).
            for n in (5, 3, 1, 4, 2):
                session.add(Chapter(
                    id=uuid.uuid4(), book_id=book1.id, chapter_number=n,
                    title=f"B1 Ch {n}", content=f"chapter body {n}",
                ))
            for n in (3, 1, 2):
                session.add(Chapter(
                    id=uuid.uuid4(), book_id=book2.id, chapter_number=n,
                    title=f"B2 Ch {n}", content=f"chapter body b2 {n}",
                ))
            await session.commit()

            service = TrailerSceneService(session)
            fetched = await service._get_project_chapters(project_id)

            assert len(fetched) == 8, (
                f"expected all 8 chapters across both project books, got {len(fetched)}"
            )
            per_book = {}
            for ch in fetched:
                per_book.setdefault(str(ch.book_id), []).append(ch.chapter_number)
            assert set(per_book) == {str(book1.id), str(book2.id)}
            assert per_book[str(book1.id)] == [1, 2, 3, 4, 5]
            assert per_book[str(book2.id)] == [1, 2, 3]
    finally:
        await engine.dispose()
