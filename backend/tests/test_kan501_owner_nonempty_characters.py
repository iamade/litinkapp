"""Owner must receive rows from a consumable SQLAlchemy ScalarResult."""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.engine import IteratorResult
from sqlalchemy.engine.result import SimpleResultMetaData

from app.api.services.character import CharacterService, PermissionDeniedError
from app.plots.models import Character


def scalar_result(rows):
    return IteratorResult(SimpleResultMetaData(["value"]), iter((row,) for row in rows)).scalars()


@pytest.mark.asyncio
@pytest.mark.parametrize("owner_as_string", [False, True])
async def test_owner_receives_nonempty_character_list(owner_as_string):
    owner, plot, book = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    character = Character(id=uuid.uuid4(), user_id=owner, plot_overview_id=plot,
                          book_id=book, name="Ada", role="Protagonist", personality="Determined")
    rows = scalar_result([character])
    session = SimpleNamespace(exec=AsyncMock(side_effect=[scalar_result([owner]), rows, scalar_result([])]))
    service = object.__new__(CharacterService)
    service.session = session
    result = await service.get_characters_by_plot(str(plot), str(owner) if owner_as_string else owner)
    assert len(result) == 1
    assert str(result[0].id) == str(character.id)
    assert result[0].name == "Ada"
    assert result[0].images == []
    assert session.exec.await_count == 3


@pytest.mark.asyncio
async def test_nonowner_still_denied_before_character_query():
    session = SimpleNamespace(exec=AsyncMock(return_value=scalar_result([uuid.uuid4()])))
    service = object.__new__(CharacterService)
    service.session = session
    with pytest.raises(PermissionDeniedError):
        await service.get_characters_by_plot(str(uuid.uuid4()), uuid.uuid4())
    assert session.exec.await_count == 1
