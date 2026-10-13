"""KAN-467 response-surface: accent/voice_gender/voice_characteristics in HTTP JSON.

The service layer persists and echoes the three voice fields (covered by
test_kan467_character_voice_persistence.py). These tests drive the real FastAPI
app over ASGI so the assertion target is the HTTP response body the client
actually receives, i.e. after response_model serialization:

- POST /api/v1/characters/plot/{plot_overview_id}  (create)
- PUT  /api/v1/characters/{character_id}           (update)

Acceptance (LC gate ruling, ratified 2026-09-18): non-null accent,
voice_gender and voice_characteristics in create AND update response JSON.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import HTTPException

from app.main import app
from app.core.database import get_session
from app.core.auth import get_current_active_user
from app.plots.models import Character

pytestmark = pytest.mark.asyncio


class _StubResult:
    """Mimics a SQL result whose first() returns a queued value."""

    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class _StubSession:
    """Session stub that pops queued results in call order (select/update agnostic).

    When an UPDATE statement is executed, its compiled params are applied to
    ``updatable`` (the ORM object the follow-up SELECT returns), mirroring the
    real DB round-trip: update -> commit -> refetch sees persisted values.
    """

    def __init__(self, results, updatable=None):
        self._results = list(results)
        self._updatable = updatable
        self.exec_calls = []
        self.update_params = []
        self.commits = 0

    async def exec(self, statement):
        self.exec_calls.append(statement)
        if getattr(statement, "is_update", False):
            params = statement.compile().params
            self.update_params.append(params)
            if self._updatable is not None:
                for key, value in params.items():
                    if hasattr(self._updatable, key):
                        setattr(self._updatable, key, value)
        return self._results.pop(0)

    def add(self, item):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        return None


def _voice_character(**overrides) -> Character:
    """ORM Character carrying non-default persisted voice values."""
    kwargs = dict(
        id=uuid.uuid4(),
        plot_overview_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Amara",
        accent="british",
        voice_gender="female",
        voice_characteristics="warm and friendly",
    )
    kwargs.update(overrides)
    return Character(**kwargs)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _install_overrides(session: _StubSession, user_id: uuid.UUID):
    async def _fake_session():
        return session

    def _fake_user():
        return SimpleNamespace(id=user_id, is_active=True)

    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_current_active_user] = _fake_user


def _clear_overrides():
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_active_user, None)


class TestCharacterCreateResponseSurface:
    async def test_create_response_json_carries_voice_fields(self, client):
        owner = uuid.uuid4()
        plot_id = uuid.uuid4()
        session = _StubSession(
            results=[_StubResult(SimpleNamespace(book_id=uuid.uuid4()))]
        )
        _install_overrides(session, owner)
        try:
            resp = await client.post(
                f"/api/v1/characters/plot/{plot_id}",
                json={
                    "name": "Amara",
                    "role": "Protagonist",
                    "accent": "british",
                    "voice_gender": "female",
                    "voice_characteristics": "warm and friendly",
                    "plot_overview_id": str(plot_id),
                    "book_id": "",
                    "user_id": "",
                },
            )
        finally:
            _clear_overrides()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["accent"] == "british", f"accent dropped from create response: {body}"
        assert body["voice_gender"] == "female", f"voice_gender dropped from create response: {body}"
        assert body["voice_characteristics"] == "warm and friendly", (
            f"voice_characteristics dropped from create response: {body}"
        )

    async def test_create_response_json_canonical_defaults_when_voice_fields_absent(
        self, client
    ):
        owner = uuid.uuid4()
        plot_id = uuid.uuid4()
        session = _StubSession(
            results=[_StubResult(SimpleNamespace(book_id=uuid.uuid4()))]
        )
        _install_overrides(session, owner)
        try:
            resp = await client.post(
                f"/api/v1/characters/plot/{plot_id}",
                json={
                    "name": "Bode",
                    "plot_overview_id": str(plot_id),
                    "book_id": "",
                    "user_id": "",
                },
            )
        finally:
            _clear_overrides()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["accent"] == "neutral"
        assert body["voice_gender"] == "auto"


class TestCharacterUpdateResponseSurface:
    async def test_update_response_json_carries_voice_fields(self, client):
        character = _voice_character()
        session = _StubSession(
            results=[
                _StubResult(character.user_id),  # permission check
                _StubResult(None),               # update statement execution
                _StubResult(character),          # refetch after commit
            ],
            updatable=character,
        )
        _install_overrides(session, character.user_id)
        try:
            resp = await client.put(
                f"/api/v1/characters/{character.id}",
                json={
                    "accent": "jamaican",
                    "voice_gender": "male",
                    "voice_characteristics": "deep and authoritative",
                },
            )
        finally:
            _clear_overrides()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["accent"] == "jamaican", f"accent dropped from update response: {body}"
        assert body["voice_gender"] == "male", f"voice_gender dropped from update response: {body}"
        assert body["voice_characteristics"] == "deep and authoritative", (
            f"voice_characteristics dropped from update response: {body}"
        )

    async def test_update_empty_strings_collapse_to_canonical_defaults(self, client):
        """LC gate ruling: empty-string voice fields must collapse to canonical
        defaults, not persist as '' (which the UI renders as unset/default)."""
        character = _voice_character(
            accent="british", voice_gender="female",
            voice_characteristics="warm and friendly",
        )
        session = _StubSession(
            results=[
                _StubResult(character.user_id),  # permission check
                _StubResult(None),               # update statement execution
                _StubResult(character),          # refetch after commit
            ],
            updatable=character,
        )
        _install_overrides(session, character.user_id)
        try:
            resp = await client.put(
                f"/api/v1/characters/{character.id}",
                json={
                    "accent": "",
                    "voice_gender": "",
                    "voice_characteristics": "",
                },
            )
        finally:
            _clear_overrides()

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["accent"] == "neutral", f"empty accent not canonicalized: {body}"
        assert body["voice_gender"] == "auto", f"empty voice_gender not canonicalized: {body}"
        assert body["voice_characteristics"] is None, (
            f"empty voice_characteristics not canonicalized to unset: {body}"
        )
        # And the persisted statement must carry the canonical values too
        assert session.update_params, "update statement was never executed"
        persisted = session.update_params[0]
        assert persisted["accent"] == "neutral"
        assert persisted["voice_gender"] == "auto"
        assert persisted["voice_characteristics"] is None
