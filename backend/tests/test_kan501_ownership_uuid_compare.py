"""KAN-501: ownership comparison must compare like-with-like (UUID vs UUID).

Defect (LC first-party verification at origin/dev_branch@be636a5e):

  backend/app/api/services/character.py:657
      if not plot_user_id or str(plot_user_id) != user_id:
  backend/app/api/services/character.py:831
      if not book_user_id or str(book_user_id) != user_id:

Both are ONE-SIDED: a stringified DB value is compared against a raw
uuid.UUID. select(PlotOverview.user_id) / select(Book.user_id) read a
pg.UUID(as_uuid=True) column (backend/app/plots/models.py:23,
backend/app/books/models.py:20), so the DB side is a uuid.UUID and the caller
passes the owner current_user.id (also a uuid.UUID).
str(db_value) != uuid_value is therefore ALWAYS True and the legitimate owner
is denied.

The correct TWO-SIDED reference form already exists in the same file at
line 1225 (_validate_character_permissions):

      if str(character_user_id) != str(user_id):

HARNESS TRAP (why the stub must yield a real uuid.UUID):
if the stubbed session yielded a str owner id, the one-sided comparison
would compare str to str and GRANT access, so the test would pass on the
UNFIXED code. The negative controls below pin that difference explicitly, so
a green run can only come from the product change and never from a mistyped
stub.

Paths covered:
  1. GET /api/v1/characters/plot/{plot_overview_id}
     (backend/app/api/routes/characters/routes.py:259) -> the service raises
     PermissionDeniedError at character.py:657, which the route maps to
     HTTP 500 "Failed to retrieve characters: Access denied to plot
     overview" for the legitimate owner (the KAN-476 symptom).
  2. AI plot-context path (enhance_with_plot_context in
     backend/app/api/routes/ai/routes.py:497) -> the same service call at
     ai/routes.py:538, whose PermissionDeniedError is swallowed by the bare
     except Exception at ai/routes.py:614-616, so the caller continues with
     an EMPTY plot context (HTTP 200, plot_enhanced false).
  3. Book path (get_all_characters_for_book, character.py:819) -> the
     second one-sided site at character.py:831.
"""

import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Test-safe env BEFORE app imports (repo KAN-470/471/477 pattern): the
# CharacterService constructor builds a ModelsLab image client and an OpenAI
# embeddings client, both of which refuse an empty key. These are dummy
# literals, never real credentials, and no provider call is made.
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test-dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
for _k in ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "REDIS_URL", "CELERY_BROKER_URL"]:
    os.environ.setdefault(_k, "dummy")
os.environ.setdefault("SMTP_PORT", "0")

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.ai import routes as ai_routes
from app.api.services.character import CharacterService, PermissionDeniedError
from app.auth.models import User
from app.books.models import Book, Chapter
from app.core.auth import get_current_active_user
from app.core.database import get_session
from app.main import app
from app.plots.models import Character

pytestmark = pytest.mark.asyncio

OWNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PLOT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
BOOK_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")

AI_ROUTE_PATH = "/generate-script-and-scenes"
AI_API_URL = "/api/v1/ai/generate-script-and-scenes"


class _Result:
    """Mimics a SQLModel ScalarResult: first() / all() / one()."""

    def __init__(self, first=None, rows=None, one=None):
        self._first = first
        self._rows = rows if rows is not None else []
        self._one = one

    def first(self):
        return self._first

    def all(self):
        return self._rows

    def one(self):
        return self._one


class _DispatchingSession:
    """Session stub that answers each statement by its compiled SQL.

    Dispatching on SQL text (instead of a strict queue) keeps the stub stable
    against incidental internal queries while still returning the OWNER-SIDE
    VALUE EXACTLY AS THE DATABASE WOULD.

    The ownership value is a real uuid.UUID: PlotOverview.user_id and
    Book.user_id are pg.UUID(as_uuid=True) columns, so SQLModel exec() ->
    scalars().first() yields a uuid.UUID. A str here would invert the
    one-sided comparison and make this whole file pass against UNFIXED
    product code.
    """

    def __init__(self, *, owner_id, characters, plot_overview=None, chapter=None, book=None):
        self.owner_id = owner_id
        self.characters = characters
        self.plot_overview = plot_overview
        self.chapter = chapter
        self.book = book
        self.statements = []
        self.added = []
        self.commits = 0
        self.refreshes = 0

    async def exec(self, statement):
        self.statements.append(statement)
        sql = " ".join(str(statement).split())

        # select(PlotOverview.user_id) / select(Book.user_id) /
        # select(Character.user_id): the ownership seams.
        if sql.startswith("SELECT plot_overviews.user_id"):
            return _Result(first=self.owner_id)
        if sql.startswith("SELECT books.user_id"):
            return _Result(first=self.owner_id)
        if sql.startswith("SELECT characters.user_id"):
            return _Result(first=self.owner_id)

        # select(PlotOverview) - full entity (plot overview lookups).
        if "FROM plot_overviews" in sql:
            return _Result(first=self.plot_overview)

        # select(Character)
        if "FROM characters" in sql:
            return _Result(rows=self.characters)

        # select(ImageGeneration)
        if "FROM image_generations" in sql:
            return _Result(rows=[])

        # select(Chapter)
        if "FROM chapters" in sql:
            return _Result(first=self.chapter)

        # select(Book)
        if "FROM books" in sql:
            return _Result(first=self.book)

        # Anything else: an empty result, so incidental lookups do not fail.
        return _Result(first=None, rows=[])

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        self.refreshes += 1

    async def rollback(self):
        pass


def _owner_user(user_id=OWNER_ID):
    """Real User ORM object: current_user.id is a uuid.UUID."""
    return User(id=user_id, email=f"{user_id}@example.test", is_active=True)


def _character(user_id=OWNER_ID, plot_overview_id=PLOT_ID, book_id=BOOK_ID):
    return Character(
        id=uuid.uuid4(),
        plot_overview_id=plot_overview_id,
        book_id=book_id,
        user_id=user_id,
        name="Ada",
        role="Protagonist",
        personality="Determined",
    )


def _plot_overview_entity(user_id=OWNER_ID, book_id=BOOK_ID):
    """A PlotOverview row as the plot-overview lookups would return it."""
    from app.plots.models import PlotOverview

    return PlotOverview(
        id=PLOT_ID,
        book_id=book_id,
        user_id=user_id,
        logline="A test logline",
    )


def _duck_plot(plot_id=PLOT_ID):
    """Duck-typed plot overview for the AI plot-context path.

    PlotService.get_plot_overview returns a PlotOverviewResponse, which does
    NOT declare target_audience / conflict_type / stakes.
    enhance_with_plot_context reads those attributes at ai/routes.py:568 and
    ai/routes.py:585, and the bare except Exception at ai/routes.py:614
    swallows the resulting AttributeError. That is a SEPARATE pre-existing
    defect (reported to LC, not fixed here); using the repo established
    duck-typed plot (see backend/tests/test_plot_fallback.py) keeps this file
    focused on the OWNERSHIP seam instead of masking it behind a different
    failure.
    """
    return SimpleNamespace(
        id=plot_id,
        logline="A test logline",
        themes=["redemption"],
        story_type="Novel",
        genre="Fantasy",
        tone="Epic",
        setting="A distant land",
        target_audience="Adults",
        conflict_type="Person vs Self",
        stakes="The kingdom",
    )


def _install_overrides(session, user):
    async def _fake_session():
        return session

    def _fake_user():
        return user

    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_current_active_user] = _fake_user


def _clear_overrides():
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_active_user, None)


# ---------------------------------------------------------------------------
# 1. GET /api/v1/characters/plot/{plot_overview_id}
#    (characters/routes.py:259 -> character.py:643 -> character.py:657)
# ---------------------------------------------------------------------------


async def test_plot_route_grants_owner_uuid_owner_id():
    """The legitimate owner of the plot MUST receive the characters.

    Unfixed behaviour: HTTP 500 with detail "Access denied to plot
    overview" (the KAN-476 symptom), because str(uuid) != uuid.
    """
    session = _DispatchingSession(
        owner_id=OWNER_ID,
        characters=[_character(user_id=OWNER_ID)],
        plot_overview=_plot_overview_entity(user_id=OWNER_ID),
    )
    _install_overrides(session, _owner_user(OWNER_ID))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/characters/plot/{PLOT_ID}")
    finally:
        _clear_overrides()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1, body
    assert body[0]["name"] == "Ada", body
    assert body[0]["user_id"] == str(OWNER_ID), body


async def test_plot_route_denies_non_owner():
    """A different user MUST NOT receive the characters.

    The characters route has no 403 mapping, so a denial surfaces as a 500
    today; the security property asserted here is "denied, no character
    data". The status code accepts 403 or 500 so a future mapping cleanup
    does not break this guard.
    """
    session = _DispatchingSession(
        owner_id=OTHER_ID,
        characters=[_character(user_id=OTHER_ID)],
        plot_overview=_plot_overview_entity(user_id=OTHER_ID),
    )
    _install_overrides(session, _owner_user(OWNER_ID))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/characters/plot/{PLOT_ID}")
    finally:
        _clear_overrides()

    assert resp.status_code in (403, 500), resp.text
    assert "Access denied" in resp.text, resp.text
    assert "Ada" not in resp.text, resp.text


# ---------------------------------------------------------------------------
# 2. AI plot-context path
#    (ai/routes.py:497 -> ai/routes.py:538 -> character.py:657)
#    The denial is swallowed at ai/routes.py:614-616 -> HTTP 200 with an
#    EMPTY plot context.
# ---------------------------------------------------------------------------


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
                "ADA reads by candlelight. A quiet scene for testing."
            ),
            "model_used": "kan501-test-model",
            "usage": {"total_tokens": 10, "estimated_cost": 0.0},
        }

    async def analyze_content(self, **kwargs):
        return {"scenes": [{"description": "A quiet study at night"}]}


class _FakeRAGService:
    def __init__(self, session):
        pass

    async def get_chapter_with_context(self, chapter_id, include_adjacent=True):
        return {
            "total_context": "The old man read by candlelight.",
            "chapter": {"title": "Chapter 1", "content": "The old man read."},
        }


class _FakeAIService:
    def __init__(self, *args, **kwargs):
        pass

    async def generate_emotional_map(self, script, characters):
        return []


def _override_credits_dependency():
    """require_credits(...) built a unique dependency callable at import;
    locate it on the live route and override it by object identity."""
    target = None
    for r in ai_routes.router.routes:
        if getattr(r, "path", "") == AI_ROUTE_PATH:
            for d in r.dependant.dependencies:
                if d.name == "reservation_id":
                    target = d.call
    assert target is not None, "reservation_id dependency not found on route"
    app.dependency_overrides[target] = lambda: uuid.uuid4()


def _plot_service_stub(plot):
    plot_service = MagicMock()
    plot_service.get_plot_overview = AsyncMock(return_value=plot)
    return MagicMock(return_value=plot_service)


async def _post_ai_script(session, chapter):
    with patch.object(ai_routes, "SubscriptionManager", _FakeSubscriptionManager), \
         patch.object(ai_routes, "CreditService", _FakeCreditService), \
         patch.object(ai_routes, "ScriptModelRouter", _FakeScriptModelRouter), \
         patch.object(ai_routes, "RAGService", _FakeRAGService), \
         patch.object(ai_routes, "AIService", _FakeAIService), \
         patch.object(ai_routes, "PlotService", _plot_service_stub(_duck_plot())):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                AI_API_URL,
                json={
                    "chapter_id": str(chapter.id),
                    "script_style": "cinematic",
                    "script_name": "KAN-501 Test 001",
                    "plot_context": True,
                },
            )


def _chapter_for(book):
    chapter = Chapter(
        id=uuid.uuid4(),
        book_id=book.id,
        title="Chapter 1",
        content="The old man read by candlelight.",
        chapter_number=1,
    )
    chapter.book = book
    return chapter


async def test_ai_plot_context_grants_owner_uuid_owner_id():
    """The AI plot-context path MUST include the owner characters.

    Unfixed behaviour: the ownership denial raises inside
    get_characters_by_plot, is swallowed by the bare except Exception at
    ai/routes.py:614-616, and the route still answers HTTP 200 - but with
    plot_enhanced false and plot_info null (an EMPTY plot context).
    """
    book = Book(
        id=BOOK_ID,
        user_id=OWNER_ID,
        title="KAN 501 Book",
        book_type="epub",
        status="completed",
    )
    chapter = _chapter_for(book)
    session = _DispatchingSession(
        owner_id=OWNER_ID,
        characters=[_character(user_id=OWNER_ID)],
        plot_overview=_plot_overview_entity(user_id=OWNER_ID),
        chapter=chapter,
        book=book,
    )

    _install_overrides(session, _owner_user(OWNER_ID))
    _override_credits_dependency()
    try:
        resp = await _post_ai_script(session, chapter)
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plot_enhanced"] is True, body
    assert body["plot_info"] is not None, body
    assert body["plot_info"]["character_count"] == 1, body
    # The ownership query really ran: the seam is exercised, not bypassed.
    ownership_queries = [
        s
        for s in session.statements
        if "SELECT plot_overviews.user_id" in " ".join(str(s).split())
    ]
    assert len(ownership_queries) == 1, session.statements


async def test_ai_plot_context_denies_non_owner_with_empty_context():
    """A different user MUST get an empty plot context (swallowed denial).

    The BOOK stays owned by the requesting user so the upstream chapter
    access gate (ai/routes.py:3737) passes and the request actually reaches
    the plot-context seam under test; only the PLOT OVERVIEW belongs to
    somebody else, so the character ownership check at character.py:657 is
    the only thing that can deny it. This guard must hold in the fixed AND
    the unfixed tree (it is a guard, not a repair).
    """
    book = Book(
        id=BOOK_ID,
        user_id=OWNER_ID,
        title="KAN 501 Book",
        book_type="epub",
        status="completed",
    )
    chapter = _chapter_for(book)
    session = _DispatchingSession(
        owner_id=OTHER_ID,
        characters=[_character(user_id=OTHER_ID)],
        plot_overview=_plot_overview_entity(user_id=OTHER_ID),
        chapter=chapter,
        book=book,
    )

    _install_overrides(session, _owner_user(OWNER_ID))
    _override_credits_dependency()
    try:
        resp = await _post_ai_script(session, chapter)
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plot_enhanced"] is False, body
    assert body["plot_info"] is None, body


# ---------------------------------------------------------------------------
# 3. Book path (second one-sided site, character.py:831)
# ---------------------------------------------------------------------------


async def test_book_path_grants_owner_uuid_owner_id():
    session = _DispatchingSession(
        owner_id=OWNER_ID,
        characters=[_character(user_id=OWNER_ID)],
    )
    service = CharacterService(session)
    result = await service.get_all_characters_for_book(str(BOOK_ID), OWNER_ID)

    assert len(result) == 1, result
    assert result[0].name == "Ada", result


async def test_book_path_denies_non_owner():
    # KAN-504: the old bare `except` swallowed the denial and returned [],
    # so a wrong owner got HTTP 200 with an empty list. The split raises
    # PermissionDeniedError instead (route-mapped to 403).
    import pytest as _pytest

    from app.api.services.character import PermissionDeniedError as _PDE

    session = _DispatchingSession(
        owner_id=OTHER_ID,
        characters=[_character(user_id=OTHER_ID)],
    )
    service = CharacterService(session)
    with _pytest.raises(_PDE):
        await service.get_all_characters_for_book(str(BOOK_ID), OWNER_ID)


# ---------------------------------------------------------------------------
# 4. Negative controls and scope guards
# ---------------------------------------------------------------------------


async def test_negative_control_uuid_owner_is_denied_by_one_sided_form():
    """Negative control: the harness is sensitive to the one-sided form.

    With the REAL uuid.UUID values the comparison sees, the unfixed one-sided
    form denies the legitimate owner while the two-sided form grants it. A
    str stub would have compared str to str and granted access on the
    UNFIXED code, i.e. it would have produced a false green. This test pins
    that difference, so the passing owner tests above can only come from the
    product change.
    """
    owner = OWNER_ID

    assert (str(owner) != owner) is True, "one-sided form must deny the UUID owner"
    assert (str(owner) != str(owner)) is False, "two-sided form must grant the UUID owner"
    assert (
        str(str(owner)) != str(owner)
    ) is False, "a str stub would mask the defect on unfixed code"


async def test_negative_control_source_guards_the_two_sided_form():
    """Negative control: the source under test must use the two-sided form.

    Reads the module under test from THIS checkout
    (Path(__file__).resolve().parents[1]), never a hardcoded tree. On the
    unfixed base this test FAILS, which is what makes the FAIL-BEFORE run
    attributable to the defect rather than to a broken harness.
    """
    service_path = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "services" / "character.py"
    )
    source = service_path.read_text()

    assert "str(plot_user_id) != str(user_id)" in source, source
    assert "str(book_user_id) != str(user_id)" in source, source
    # The pre-existing two-sided reference form must remain unchanged.
    assert "str(character_user_id) != str(user_id)" in source, source
    # No one-sided ownership comparison may remain.
    assert "str(plot_user_id) != user_id" not in source, source
    assert "str(book_user_id) != user_id" not in source, source


async def test_two_sided_reference_site_still_grants_uuid_owner():
    """Guard: the already-correct site at character.py:1225 is untouched."""
    session = _DispatchingSession(owner_id=OWNER_ID, characters=[])
    service = CharacterService(session)
    assert await service._validate_character_permissions("char-1", OWNER_ID) is True


async def test_two_sided_reference_site_still_denies_non_owner():
    session = _DispatchingSession(owner_id=OTHER_ID, characters=[])
    service = CharacterService(session)
    with pytest.raises(PermissionDeniedError):
        await service._validate_character_permissions("char-1", OWNER_ID)
