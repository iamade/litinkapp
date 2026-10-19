"""KAN-483: GET /books/{id}/chapters 500 at response serialization.

Root cause: route returns Chapter ORM model_dump() whose id/book_id are uuid.UUID,
while response_model ChapterSchema declares them str; pydantic v2 does not coerce
UUID->str, so FastAPI response validation raises -> HTTP 500.
"""
import os

# KAN-488 bare-env guard: run without an external DATABASE_URL etc.
# Use the asyncpg driver: a sync postgresql:// URL makes engine construction fail
# with AsyncAdaptedQueuePool before any assertion runs.
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
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
from typing import List

from fastapi.encoders import jsonable_encoder
from pydantic import TypeAdapter

from app.books.models import Chapter as ChapterModel
from app.books.schemas import Chapter as ChapterSchema


def _orm_chapter(book_id):
    return ChapterModel(
        id=uuid.uuid4(), book_id=book_id, title="Chapter 1: The Graveyard",
        content="text", chapter_number=1, order_index=0,
    )


def test_chapter_schema_accepts_orm_uuid_fields():
    c = _orm_chapter(uuid.uuid4())
    out = TypeAdapter(List[ChapterSchema]).validate_python([c.model_dump()])
    assert out[0].id == str(c.id) and out[0].book_id == str(c.book_id)
    jsonable_encoder(out)


def test_get_chapters_route_output_passes_response_model():
    from app.api.routes.books import routes

    book_id = uuid.uuid4()
    user_id = uuid.uuid4()
    book = SimpleNamespace(id=book_id, user_id=user_id, status="READY")
    rows = [_orm_chapter(book_id), _orm_chapter(book_id)]

    class _Res:
        def __init__(self, v): self.v = v
        def first(self): return self.v
        def all(self): return self.v

    class _Sess:
        def __init__(self): self.n = 0
        async def exec(self, stmt):
            self.n += 1
            return _Res(book) if self.n == 1 else _Res(rows)

    payload = asyncio.run(routes.get_chapters(str(book_id), session=_Sess(),
                                               current_user=SimpleNamespace(id=user_id)))
    validated = TypeAdapter(List[ChapterSchema]).validate_python(payload)
    assert [v.id for v in validated] == [str(r.id) for r in rows]
