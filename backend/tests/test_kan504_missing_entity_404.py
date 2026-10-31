"""KAN-504: nonexistent plot/book ids must surface as 404, not leak the
access-denied path as 500.

Defect (LC ruling c18876, verified at dev cba36243): both ownership checks
conflate a MISSING entity with a WRONG OWNER:

  character.py ~:657 (get_characters_by_plot)
      if not plot_user_id or str(plot_user_id) != str(user_id):
          raise PermissionDeniedError("Access denied to plot overview")
  character.py ~:831 (get_all_characters_for_book)
      if not book_user_id or str(book_user_id) != str(user_id):
          raise PermissionDeniedError("Access denied to book")

result.first() is None for a nonexistent id, so the missing-entity case takes
the denial branch; the route then maps the exception to HTTP 500. The split:
missing -> CharacterNotFoundError -> 404; wrong owner -> PermissionDeniedError
-> 403 (the 500 handler is part of the leak, per LC's ruling).
"""
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("STRIPE_SECRET_KEY", "dummy")
os.environ.setdefault("OPENAI_API_KEY", "dummy-openai-key")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy-modelslab-key")
os.environ.setdefault("MAIL_FROM", "test@litinkai.dev")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")

from types import SimpleNamespace  # noqa: E402

from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from app.api.services.character import (  # noqa: E402
    CharacterNotFoundError,
    CharacterService,
    PermissionDeniedError,
)
from app.plots.schemas import CharacterResponse  # noqa: E402

pytestmark = pytest.mark.asyncio


class _Result:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value

    def all(self):
        if isinstance(self._value, (list, tuple)):
            return list(self._value)
        return [self._value] if self._value is not None else []


class _DispatchingSession:
    """Dispatch exec() on SQL text: plot_overviews, books, characters, images."""

    def __init__(self, owner_value=None, owner_user_id=None, characters=None):
        self.owner_value = owner_value  # what the ownership select returns
        self.owner_user_id = owner_user_id
        self.characters = characters or []
        self.added = []

    async def exec(self, statement):
        text = str(statement).lower()
        if "plot_overview" in text and "select" in text and "character" not in text:
            return _Result(self.owner_value)
        if '"book"' in text or " from book " in text or "from book" in text:
            if "character" not in text:
                return _Result(self.owner_value)
        if "imagegeneration" in text:
            return _Result([])
        return _Result(self.characters)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        pass

    async def rollback(self):
        pass


OWNER = uuid.uuid4()
OTHER = uuid.uuid4()


def _service(owner_value, characters=None):
    return CharacterService(_DispatchingSession(owner_value=owner_value, characters=characters or [])), OWNER


class TestPlotSite:
    async def test_nonexistent_plot_404(self):
        svc, uid = _service(None)
        with pytest.raises(CharacterNotFoundError):
            await svc.get_characters_by_plot(str(uuid.uuid4()), str(uid))

    async def test_other_owner_403(self):
        svc, uid = _service(OTHER)
        with pytest.raises(PermissionDeniedError):
            await svc.get_characters_by_plot(str(uuid.uuid4()), str(uid))

    async def test_owner_200(self):
        chars = [MagicMock()]
        svc, uid = _service(OWNER, characters=chars)
        with patch.object(
            CharacterResponse, "model_validate", classmethod(lambda cls, v: v)
        ):
            out = await svc.get_characters_by_plot(str(uuid.uuid4()), str(uid))
        assert out == chars


class TestBookSite:
    async def test_nonexistent_book_404(self):
        svc, uid = _service(None)
        with pytest.raises(CharacterNotFoundError):
            await svc.get_all_characters_for_book(str(uuid.uuid4()), str(uid))

    async def test_other_owner_403(self):
        svc, uid = _service(OTHER)
        with pytest.raises(PermissionDeniedError):
            await svc.get_all_characters_for_book(str(uuid.uuid4()), str(uid))

    async def test_owner_200(self):
        chars = [MagicMock()]
        svc, uid = _service(OWNER, characters=chars)
        with patch.object(
            CharacterResponse, "model_validate", classmethod(lambda cls, v: v)
        ):
            out = await svc.get_all_characters_for_book(str(uuid.uuid4()), str(uid))
        assert out == chars


class TestRouteMapping:
    """The route must map CharacterNotFoundError -> 404 and
    PermissionDeniedError -> 403 instead of the generic 500."""

    async def test_plot_route_maps_not_found_to_404(self):
        from fastapi import HTTPException
        from app.api.routes.characters import routes as char_routes

        async def _raise(*args, **kwargs):
            raise CharacterNotFoundError("Plot overview not found")

        fake_service = MagicMock()
        fake_service.get_characters_by_plot = _raise
        with _patched_service(char_routes, fake_service):
            with pytest.raises(HTTPException) as exc:
                await char_routes.get_characters_by_plot(
                    str(uuid.uuid4()),
                    session=MagicMock(),
                    current_user=SimpleNamespace(id=OWNER),
                )
        assert exc.value.status_code == 404, "missing entity must be 404, not 500"

    async def test_plot_route_maps_denial_to_403(self):
        from fastapi import HTTPException
        from app.api.routes.characters import routes as char_routes

        async def _raise(*args, **kwargs):
            raise PermissionDeniedError("Access denied to plot overview")

        fake_service = MagicMock()
        fake_service.get_characters_by_plot = _raise
        with _patched_service(char_routes, fake_service):
            with pytest.raises(HTTPException) as exc:
                await char_routes.get_characters_by_plot(
                    str(uuid.uuid4()),
                    session=MagicMock(),
                    current_user=SimpleNamespace(id=OWNER),
                )
        assert exc.value.status_code == 403, "wrong owner must be 403, not 500"


class _patched_service:
    def __init__(self, module, fake):
        self._module = module
        self._fake = fake

    def __enter__(self):
        import contextlib

        self._cm = contextlib.ExitStack()
        mod = self._module

        class _Factory:
            def __init__(self, fake):
                self.fake = fake

            def __call__(self, session):
                return self.fake

        self._orig = getattr(mod, "CharacterService", None)
        mod.CharacterService = _Factory(self._fake)
        return self

    def __exit__(self, *exc):
        mod = self._module
        if self._orig is not None:
            mod.CharacterService = self._orig
        return False
