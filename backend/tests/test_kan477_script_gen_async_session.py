"""KAN-477: script generation 500 regression tests.

Defect (Akande-verified 2026-09-29): backend/app/api/routes/ai/routes.py
registered POST /generate-script-and-scenes TWICE — the serving
ScriptModelRouter handler (~:3588) and a dead RAGService-block handler
(generate_script_and_scenes_with_gpt, ~:4234). The duplicate registration
was removed; these tests pin the fix:

1. exactly one POST route for the path is registered;
2. the endpoint returns HTTP 200 on a happy-path request (mocked services).
"""

import os
import uuid

# Test-safe env BEFORE app imports (KAN-470/471 pattern).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.ai import routes as ai_routes
from app.auth.models import User
from app.books.models import Book, Chapter
from app.core.database import get_session
from app.main import app

pytestmark = pytest.mark.asyncio

ROUTE_PATH = "/generate-script-and-scenes"
API_URL = "/api/v1/ai/generate-script-and-scenes"


def test_single_registration():
    """KAN-477 regression: the route must be registered exactly once."""
    matches = [
        r
        for r in ai_routes.router.routes
        if getattr(r, "path", "") == ROUTE_PATH
        and "POST" in (getattr(r, "methods", None) or set())
    ]
    assert len(matches) == 1, (
        f"expected exactly 1 POST {ROUTE_PATH}, found {len(matches)}"
    )


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
        self.incidental = []
        self.added = []
        self.commits = 0
        self.refreshes = 0

    async def exec(self, statement):
        # First (chapter lookup) comes from the strict queue; later
        # incidental selects (plot_overviews lookup, etc.) fall through to
        # a permissive empty result so the real handler code path runs.
        if self._results:
            return self._results.pop(0)
        self.incidental.append(str(statement))
        return _Result(first=None)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        self.refreshes += 1


class _Tier:
    value = "free"


class _FakeSubscriptionManager:
    def __init__(self, session):
        pass

    async def get_user_tier(self, user_id):
        return _Tier()

    async def record_usage(self, *args, **kwargs):
        return None


class _FakeCreditService:
    def __init__(self, session):
        pass

    def credit_transaction(self, reservation_id, amount):
        class _Ctx:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *exc):
                return False

        return _Ctx()


class _FakeScriptModelRouter:
    async def generate_script(self, **kwargs):
        return {
            "status": "success",
            "content": (
                "Scene 1: INT. STUDY - NIGHT\n\n"
                "ISHMAEL reads by candlelight. A quiet scene for testing.\n\n"
                "Scene 2: EXT. DOCKS - DAWN\n\n"
                "The ship waits in the fog."
            ),
            "model_used": "kan477-test-model",
            "usage": {"total_tokens": 10, "estimated_cost": 0.0},
            "scene_descriptions": [
                "A quiet study at night",
                "Candlelight fades",
            ],
        }

    async def analyze_content(self, **kwargs):
        return {
            "scenes": [
                {"description": "A quiet study at night", "sub_scenes": []},
                {"description": "Candlelight fades", "sub_scenes": []},
            ],
            "sub_scenes_metadata": {},
            "dialogue_moments": {},
        }


class _FakeRAGService:
    def __init__(self, session):
        pass

    async def get_chapter_with_context(self, chapter_id, include_adjacent=True):
        return {
            "total_context": "The old man read by candlelight. Ishmael waited.",
            "chapter": {
                "title": "Chapter 1",
                "content": "The old man read by candlelight.",
            },
        }


def _user():
    return User(
        id=uuid.uuid4(),
        email="kan477@example.test",
        is_active=True,
        full_name="KAN 477 User",
    )


def _book(user):
    return Book(
        id=uuid.uuid4(),
        user_id=user.id,
        title="KAN 477 Book",
        book_type="epub",
        status="completed",
    )


def _chapter(book):
    chapter = Chapter(
        id=uuid.uuid4(),
        book_id=book.id,
        title="Chapter 1",
        content="The old man read by candlelight.",
        chapter_number=1,
    )
    chapter.book = book
    return chapter


def _override_credits_dependency():
    """require_credits(...) built a unique dependency callable at import;
    locate it on the live route and override it by object identity."""
    target = None
    for r in ai_routes.router.routes:
        if getattr(r, "path", "") == ROUTE_PATH:
            for d in r.dependant.dependencies:
                if d.name == "reservation_id":
                    target = d.call
    assert target is not None, "reservation_id dependency not found on route"
    app.dependency_overrides[target] = lambda: uuid.uuid4()


async def test_generate_script_and_scenes_returns_200(monkeypatch):
    """KAN-477 regression: happy-path POST must return 200 (was 500)."""
    monkeypatch.setattr(ai_routes, "SubscriptionManager", _FakeSubscriptionManager)
    monkeypatch.setattr(ai_routes, "CreditService", _FakeCreditService)
    monkeypatch.setattr(ai_routes, "ScriptModelRouter", _FakeScriptModelRouter)
    monkeypatch.setattr(ai_routes, "RAGService", _FakeRAGService)

    user = _user()
    book = _book(user)
    chapter = _chapter(book)
    fake_session = _FakeSession([_Result(first=chapter)])

    app.dependency_overrides[get_session] = lambda: fake_session
    app.dependency_overrides[ai_routes.get_current_active_user] = lambda: user
    _override_credits_dependency()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                API_URL,
                json={
                    "chapter_id": str(chapter.id),
                    "script_style": "cinematic",
                    "script_name": "KAN-477 Test 001",
                },
            )
        assert resp.status_code == 200, f"body: {resp.text[:800]}"
        assert resp.headers.get("X-Resolved-Model") == "kan477-test-model"
    finally:
        app.dependency_overrides.clear()
