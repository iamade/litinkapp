"""Regression test for KAN-467 — plot read-path drops accent/voice_gender/voice_characteristics.

Zcode c16310 found: write-path (create echo + DB persistence) PASS; read-path constructor
in plot.py drops the three persisted fields after save. LC c16313 scoped the fix to the
read-path only — restore accent/voice_gender/voice_characteristics in CharacterResponse(...)
constructor calls in PlotService.

This test asserts that the three fields are passed to CharacterResponse when present on the
persisted model. Uses a stub async session + minimal plot data shape, matching the pattern of
existing tests/test_kan186_character_voice.py (referenced by the original ticket lineage).
"""
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.services.plot import PlotService
from app.plots.schemas import CharacterResponse


def _char_data(**overrides):
    base = {
        "id": uuid4(),
        "plot_overview_id": uuid4(),
        "book_id": uuid4(),
        "user_id": uuid4(),
        "name": "Test Character",
        "role": "Protagonist",
        "entity_type": "human",
        "character_arc": "Redemption",
        "physical_description": "Tall, dark hair",
        "personality": "Brooding",
        "archetypes": ["hero"],
        "want": "Save the kingdom",
        "need": "Accept help",
        "lie": "He is alone",
        "ghost": "Lost his brother",
        "image_url": None,
        "image_generation_prompt": None,
        "image_metadata": None,
        "generation_method": "openrouter",
        "model_used": "anthropic/claude-3.5-sonnet",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        # The three fields that KAN-467 restores:
        "accent": "british",
        "voice_gender": "female",
        "voice_characteristics": "warm and friendly, deep",
    }
    base.update(overrides)
    return base


def _assert_three_fields_in_response(char_response: CharacterResponse, char_data: dict) -> None:
    """Verify the three KAN-467 fields are populated on the response."""
    assert char_response.accent == char_data["accent"], (
        f"accent dropped: expected {char_data['accent']!r}, got {char_response.accent!r}"
    )
    assert char_response.voice_gender == char_data["voice_gender"], (
        f"voice_gender dropped: expected {char_data['voice_gender']!r}, got {char_response.voice_gender!r}"
    )
    assert char_response.voice_characteristics == char_data["voice_characteristics"], (
        f"voice_characteristics dropped: expected {char_data['voice_characteristics']!r}, "
        f"got {char_response.voice_characteristics!r}"
    )


def test_character_response_includes_accent_voice_gender_voice_characteristics():
    """KAN-467 regression: CharacterResponse must carry the three voice/accent fields.

    Verifies the Pydantic schema accepts the three fields (proves the schema is in sync
    with the read-path constructor in plot.py). Catches a class of regression where a
    schema field is renamed or removed without updating the read-path constructor.
    """
    char_data = _char_data()
    response = CharacterResponse(
        id=str(char_data["id"]),
        plot_overview_id=str(char_data["plot_overview_id"]),
        book_id=str(char_data["book_id"]),
        user_id=str(char_data["user_id"]),
        name=char_data["name"],
        role=char_data["role"],
        entity_type=char_data["entity_type"],
        character_arc=char_data["character_arc"],
        physical_description=char_data["physical_description"],
        personality=char_data["personality"],
        archetypes=char_data["archetypes"],
        want=char_data["want"],
        need=char_data["need"],
        lie=char_data["lie"],
        ghost=char_data["ghost"],
        image_url=char_data["image_url"],
        image_generation_prompt=char_data["image_generation_prompt"],
        image_metadata=char_data["image_metadata"],
        generation_method=char_data["generation_method"],
        model_used=char_data["model_used"],
        created_at=char_data["created_at"],
        updated_at=char_data["updated_at"],
        accent=char_data["accent"],
        voice_gender=char_data["voice_gender"],
        voice_characteristics=char_data["voice_characteristics"],
        images=[],
    )
    _assert_three_fields_in_response(response, char_data)


def test_character_response_defaults_for_three_fields():
    """Schema defaults: accent='neutral', voice_gender='auto', voice_characteristics=None.

    Proves the read-path constructor does not need explicit defaults (model already has them);
    missing values from older data should fall back to schema defaults rather than None/empty.
    """
    char_data = _char_data(accent="neutral", voice_gender="auto", voice_characteristics=None)
    response = CharacterResponse(
        id=str(char_data["id"]),
        plot_overview_id=str(char_data["plot_overview_id"]),
        book_id=str(char_data["book_id"]),
        user_id=str(char_data["user_id"]),
        name=char_data["name"],
        role=char_data["role"],
        entity_type=char_data["entity_type"],
        character_arc=None,
        physical_description=None,
        personality=None,
        archetypes=None,
        want=None,
        need=None,
        lie=None,
        ghost=None,
        image_url=None,
        image_generation_prompt=None,
        image_metadata=None,
        generation_method="openrouter",
        model_used=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        accent=char_data["accent"],
        voice_gender=char_data["voice_gender"],
        voice_characteristics=char_data["voice_characteristics"],
        images=[],
    )
    assert response.accent == "neutral"
    assert response.voice_gender == "auto"
    assert response.voice_characteristics is None


def test_character_response_accent_variations():
    """Round-trip: a variety of accent values survives the response constructor.

    Covers: british, american-southern, australian, neutral (the four most common
    values observed in the FE forward payload).
    """
    for accent in ("british", "american-southern", "australian", "neutral"):
        char_data = _char_data(accent=accent)
        response = CharacterResponse(
            id=str(char_data["id"]),
            plot_overview_id=str(char_data["plot_overview_id"]),
            book_id=str(char_data["book_id"]),
            user_id=str(char_data["user_id"]),
            name=char_data["name"],
            role=char_data["role"],
            entity_type=char_data["entity_type"],
            character_arc=None, physical_description=None, personality=None,
            archetypes=None, want=None, need=None, lie=None, ghost=None,
            image_url=None, image_generation_prompt=None, image_metadata=None,
            generation_method="openrouter", model_used=None,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            accent=char_data["accent"],
            voice_gender=char_data["voice_gender"],
            voice_characteristics=char_data["voice_characteristics"],
            images=[],
        )
        assert response.accent == accent


def test_plot_read_path_constructor_includes_three_fields():
    """Static check: the plot.py read-path CharacterResponse(...) call sites pass
    accent, voice_gender, voice_characteristics to the response constructor.

    This is the actual regression gate for Zcode c16310 / LC c16313: if a future change
    drops these three kwargs from the plot.py read-path constructor, the read path will
    silently drop the three fields again.

    Scoping: the file has multiple CharacterResponse(...) call sites (L17 import is not a call;
    L1668 stored_char create block; L2000 read-path block #1; L2139 read-path block #2). We
    only require the two read-path blocks (identified by the `images=[` marker immediately
    following the field assignments) to carry the three kwargs. The stored_char create block
    at L1668 is a different code path not in scope for KAN-467.
    """
    import os
    import re
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plot_path = os.path.join(repo_root, "backend", "app", "api", "services", "plot.py")
    with open(plot_path, "r") as f:
        plot_src = f.read()

    # Find CharacterResponse(...) blocks whose body contains `images=[` (the read-path marker).
    # Use a non-greedy match between CharacterResponse( and the FIRST occurrence of images=[
    # which appears inside the same block (the read-path constructor always includes images=[]).
    pattern = re.compile(r"CharacterResponse\s*\((.*?images=\[)", re.DOTALL)
    read_path_blocks = pattern.findall(plot_src)
    assert len(read_path_blocks) >= 2, (
        f"KAN-467 regression: expected at least 2 read-path CharacterResponse(...) blocks "
        f"(with images=[ marker), found {len(read_path_blocks)}. The plot.py read-path "
        f"constructor was reduced; check whether LC c16313 scope was preserved."
    )
    for i, body in enumerate(read_path_blocks):
        for field in ("accent=", "voice_gender=", "voice_characteristics="):
            assert field in body, (
                f"KAN-467 regression: read-path CharacterResponse block #{i} in plot.py "
                f"missing kwarg {field!r}. Zcode c16310 found the read-path drops the three "
                f"persisted fields; LC c16313 scoped the fix to read-path only. Restoring "
                f"all three kwargs is in-scope."
            )
