import uuid
from types import SimpleNamespace

from app.api.routes.ai.routes import _extract_script_characters_with_ids


def test_kan443_rejects_markdown_headings_and_generic_roles():
    canonical_id = uuid.uuid4()
    script_lines = [
        "# THE REALM OF ANGELS",
        "BOY",
        "ELDER",
        "CITY MAN",
        "MARCUS",
        "ENMEDURANKI",
        "# ACT I - THE ANCIENT CALLING",
    ]
    canonical = {
        "enmeduranki": SimpleNamespace(id=canonical_id, name="Enmeduranki"),
    }

    characters, character_ids = _extract_script_characters_with_ids(
        script_lines, canonical
    )

    # KAN-331: MARCUS is a valid script-only speaker → kept as a warning-state
    # pill (empty id) instead of dropped when a canonical map exists.
    assert characters == ["Marcus", "Enmeduranki"]
    assert character_ids == ["", str(canonical_id)]


def test_kan443_filters_generic_roles_without_plot_overview():
    script_lines = [
        "BOY",
        "ELDER",
        "CITY MAN",
        "MARCUS",
        "ELENA (V.O.)",
        "-----",
        "# ACT I - THE ANCIENT CALLING",
    ]

    characters, character_ids = _extract_script_characters_with_ids(script_lines, {})

    assert characters == ["Marcus", "Elena"]
    assert character_ids == ["", ""]
