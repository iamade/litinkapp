"""KAN-331: script character pill auto-linking to Plot Overview characters.

Regression tests for `_extract_script_characters_with_ids` resolution
semantics on the generate-script-and-scenes path:

- exact (case-insensitive, whitespace-normalized) name matches resolve to
  canonical Plot Overview character ids and use the canonical spelling
- unmatched script-only speakers are KEPT with an empty id so the frontend
  renders them as warning-state pills (previously they were dropped whenever
  a canonical map existed)
- an empty canonical map keeps every valid speaker unlinked
"""

import uuid
from types import SimpleNamespace

from app.api.routes.ai.routes import _extract_script_characters_with_ids


def _canonical(*pairs):
    return {name.casefold(): SimpleNamespace(id=cid, name=name) for name, cid in pairs}


def test_kan331_exact_name_matches_autolink_to_canonical_ids():
    ishmael_id, ahab_id, queequeg_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    canonical = _canonical(
        ("Ishmael", ishmael_id),
        ("Captain Ahab", ahab_id),
        ("Queequeg", queequeg_id),
    )
    script_lines = [
        "# MOBY DICK - CHAPTER ONE",
        "ISHMAEL",
        "Call me Ishmael.",
        "CAPTAIN AHAB",
        "Have you seen the white whale?",
        "QUEEQUEG (V.O.)",
        "Aye.",
    ]

    characters, character_ids = _extract_script_characters_with_ids(
        script_lines, canonical
    )

    assert characters == ["Ishmael", "Captain Ahab", "Queequeg"]
    assert character_ids == [str(ishmael_id), str(ahab_id), str(queequeg_id)]


def test_kan331_unmatched_script_only_speakers_kept_as_warning_pills():
    """Script-only speakers must survive with empty ids (KAN-331 warning pills)."""
    ahab_id = uuid.uuid4()
    canonical = _canonical(("Captain Ahab", ahab_id))
    script_lines = [
        "ELIJAH",
        "CAPTAIN AHAB",
        "PELEG",
    ]

    characters, character_ids = _extract_script_characters_with_ids(
        script_lines, canonical
    )

    assert characters == ["Elijah", "Captain Ahab", "Peleg"]
    assert character_ids == ["", str(ahab_id), ""]


def test_kan331_empty_plot_map_keeps_all_speakers_unlinked():
    """No Plot Overview rows at all: every valid speaker still becomes a pill."""
    script_lines = [
        "ISHMAEL",
        "CAPTAIN AHAB",
    ]

    characters, character_ids = _extract_script_characters_with_ids(script_lines, {})

    assert characters == ["Ishmael", "Captain Ahab"]
    assert character_ids == ["", ""]


def test_kan331_matching_is_case_and_whitespace_insensitive():
    stubb_id = uuid.uuid4()
    canonical = _canonical(("Stubb", stubb_id))
    script_lines = [
        "  STUBB  ",
        "stubb (laughing)",
    ]

    characters, character_ids = _extract_script_characters_with_ids(
        script_lines, canonical
    )

    # Second occurrence dedupes against the canonical display name
    assert characters == ["Stubb"]
    assert character_ids == [str(stubb_id)]


def test_kan331_generic_roles_still_filtered_with_populated_map():
    ahab_id = uuid.uuid4()
    canonical = _canonical(("Captain Ahab", ahab_id))
    script_lines = [
        "NARRATOR",
        "BOY",
        "CAPTAIN AHAB",
    ]

    characters, character_ids = _extract_script_characters_with_ids(
        script_lines, canonical
    )

    assert characters == ["Captain Ahab"]
    assert character_ids == [str(ahab_id)]
