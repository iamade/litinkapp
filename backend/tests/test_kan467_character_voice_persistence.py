"""KAN-467: accent/voice_gender/voice_characteristics persistence on character create/update.

Root cause: CharacterService.create_character built the Character model and the manual
CharacterResponse with an explicit field list that omitted the three voice fields, so the
SQLModel Python-side defaults (accent='neutral', voice_gender='auto',
voice_characteristics=None) always won. update_character's whitelist had the same omission.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.api.services.character import CharacterService
from app.plots.models import Character
from app.plots.schemas import CharacterCreate, CharacterUpdate


def _make_service():
    """CharacterService with a mocked session, bypassing heavy __init__ dependencies."""
    session = MagicMock()
    service = CharacterService.__new__(CharacterService)
    service.session = session
    return service, session


def _first_result(value):
    result = MagicMock()
    result.first.return_value = value
    return result


@pytest.mark.asyncio
async def test_create_character_persists_voice_fields():
    service, session = _make_service()
    session.exec = AsyncMock(
        return_value=_first_result(SimpleNamespace(book_id=uuid.uuid4()))
    )
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    payload = CharacterCreate(
        name="Amara",
        role="Protagonist",
        accent="british",
        voice_gender="female",
        voice_characteristics="warm and friendly",
        plot_overview_id=str(uuid.uuid4()),
        book_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )

    response = await service.create_character(
        plot_overview_id=payload.plot_overview_id,
        user_id=payload.user_id,
        character_data=payload,
    )

    added = session.add.call_args.args[0]
    assert isinstance(added, Character)
    assert added.accent == "british"
    assert added.voice_gender == "female"
    assert added.voice_characteristics == "warm and friendly"

    # API response echoes persisted values, not CharacterBase defaults
    assert response.accent == "british"
    assert response.voice_gender == "female"
    assert response.voice_characteristics == "warm and friendly"


@pytest.mark.asyncio
async def test_create_character_keeps_existing_defaults_when_voice_fields_absent():
    service, session = _make_service()
    session.exec = AsyncMock(
        return_value=_first_result(SimpleNamespace(book_id=uuid.uuid4()))
    )
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    payload = CharacterCreate(
        name="Bode",
        plot_overview_id=str(uuid.uuid4()),
        book_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
    )

    response = await service.create_character(
        plot_overview_id=payload.plot_overview_id,
        user_id=payload.user_id,
        character_data=payload,
    )

    added = session.add.call_args.args[0]
    assert added.accent == "neutral"
    assert added.voice_gender == "auto"
    assert added.voice_characteristics is None
    assert response.accent == "neutral"
    assert response.voice_gender == "auto"


@pytest.mark.asyncio
async def test_update_character_includes_voice_fields_in_update_statement():
    service, session = _make_service()
    char_user_id = uuid.uuid4()
    character = Character(
        id=uuid.uuid4(),
        plot_overview_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        user_id=char_user_id,
        name="Amara",
        accent="jamaican",
        voice_gender="male",
        voice_characteristics="deep and authoritative",
    )
    session.exec = AsyncMock(
        side_effect=[
            _first_result(char_user_id),  # permission check
            MagicMock(),                  # update execution (result unused)
            _first_result(character),     # refetch after commit
        ]
    )
    session.commit = AsyncMock()

    response = await service.update_character(
        character_id=str(character.id),
        user_id=str(char_user_id),
        updates=CharacterUpdate(
            accent="jamaican",
            voice_gender="male",
            voice_characteristics="deep and authoritative",
        ),
    )

    update_stmt = session.exec.call_args_list[1].args[0]
    compiled = update_stmt.compile(dialect=postgresql.dialect())
    assert compiled.params["accent"] == "jamaican"
    assert compiled.params["voice_gender"] == "male"
    assert compiled.params["voice_characteristics"] == "deep and authoritative"

    assert response.accent == "jamaican"
    assert response.voice_gender == "male"
    assert response.voice_characteristics == "deep and authoritative"
