"""KAN-331: create_character_placeholder must pass book_id/user_id into Character.

Root cause: the placeholder endpoint built Character(...) with only
plot_overview_id/name/entity_type/role, but Character.book_id and
Character.user_id are nullable=False (backend/app/plots/models.py), so the
insert raised NotNullViolation -> HTTP 500 whenever a new placeholder was
created (used by script-character linking when the character is missing from
the Plot Overview).

Both values are in scope at the call site (book_id path param + current_user),
so the fix is to thread them into the constructor.
"""
import os
import sys
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

# KAN-488: module-scope SQLAlchemy engine setup in app.core.database runs at
# collection time; a bare environment (unset DATABASE_URL) crashes collection.
# Established repo guard pattern (test_kan445/470/477/kan226).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_kan488_guard")
os.environ.setdefault("MAIL_FROM", "qa@example.com")

import pytest
from fastapi import HTTPException

# KAN-488: if app modules were already imported by an earlier test module in
# a whole-directory run with a bare environment (settings cached with empty
# MAIL_URL/MAIL_FROM), collection here would ERROR. Skip collection instead.
try:
    from app.api.routes.plots.routes import create_character_placeholder
    from app.plots.models import Character
except Exception as _exc:  # bare/poisoned environment guard (KAN-488)
    pytest.skip(
        f"app imports unavailable in this collection environment: {_exc}",
        allow_module_level=True,
    )


def _session_exec_results(*values):
    """Each exec() call returns a result whose .first() yields the next value."""
    results = []
    for value in values:
        result = MagicMock()
        result.first.return_value = value
        results.append(result)
    return AsyncMock(side_effect=results)


def _make_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_placeholder_character_gets_scope_book_and_user_ids():
    """New placeholder Character must carry book_id + user_id from request scope."""
    user_id = uuid.uuid4()
    book_id = uuid.uuid4()
    plot_overview_id = uuid.uuid4()

    book = SimpleNamespace(id=book_id, user_id=user_id)
    plot_overview = SimpleNamespace(id=plot_overview_id, user_id=user_id)

    session = _make_session()
    session.exec = _session_exec_results(book, plot_overview, None)

    response = await create_character_placeholder(
        book_id=book_id,
        character_name="Amara",
        entity_type="character",
        session=session,
        current_user=SimpleNamespace(id=user_id),
    )

    added = session.add.call_args.args[0]
    assert isinstance(added, Character)
    # KAN-331: both FK columns are nullable=False; without these the INSERT
    # fails with NotNullViolation (500).
    assert added.book_id == book_id
    assert added.user_id == user_id
    assert added.plot_overview_id == plot_overview_id
    assert added.name == "Amara"

    assert response["id"] == str(added.id)
    assert response["message"] == "Character placeholder created successfully"


@pytest.mark.asyncio
async def test_placeholder_returns_existing_character_without_new_insert():
    """Idempotent path: matching name on the plot overview returns the row as-is."""
    user_id = uuid.uuid4()
    book_id = uuid.uuid4()
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        name="Amara",
        role="supporting",
        physical_description="",
        personality="",
        entity_type="character",
        image_url=None,
        accent=None,
        voice_gender=None,
        voice_characteristics=None,
    )

    session = _make_session()
    session.exec = _session_exec_results(
        SimpleNamespace(id=book_id, user_id=user_id),
        SimpleNamespace(id=uuid.uuid4(), user_id=user_id),
        existing,
    )

    response = await create_character_placeholder(
        book_id=book_id,
        character_name="Amara",
        entity_type="character",
        session=session,
        current_user=SimpleNamespace(id=user_id),
    )

    session.add.assert_not_called()
    assert response["id"] == str(existing.id)
    assert response["message"] == "Character already exists"


@pytest.mark.asyncio
async def test_placeholder_rejects_foreign_book():
    """Ownership check stays enforced: another user's book -> 403, no insert."""
    session = _make_session()
    session.exec = _session_exec_results(
        SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4())
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_character_placeholder(
            book_id=uuid.uuid4(),
            character_name="Amara",
            entity_type="character",
            session=session,
            current_user=SimpleNamespace(id=uuid.uuid4()),
        )

    assert exc_info.value.status_code == 403
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_placeholder_requires_plot_overview():
    """No plot overview for the book -> 404, no insert."""
    user_id = uuid.uuid4()
    book_id = uuid.uuid4()

    session = _make_session()
    session.exec = _session_exec_results(SimpleNamespace(id=book_id, user_id=user_id), None)

    with pytest.raises(HTTPException) as exc_info:
        await create_character_placeholder(
            book_id=book_id,
            character_name="Amara",
            entity_type="character",
            session=session,
            current_user=SimpleNamespace(id=user_id),
        )

    assert exc_info.value.status_code == 404
    session.add.assert_not_called()
