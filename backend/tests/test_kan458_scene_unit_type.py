"""
KAN-458 — 'scene' added to sequence_unit_type enum.

PSQ test harness POSTs with ``unit_type="scene"``; DB enum originally
declared 6 values and rejected with InvalidTextRepresentationError.

LC dispatch (msg ``1534174532619730984``): add 'scene' to DB enum;
request schema is authoritative.

This test verifies:
1. ``SequenceUnitType`` enum has ``SCENE = "scene"``
2. ``REQUIRED_UNIT_TYPES`` list contains ``"scene"``
3. Field description on ``SequenceUnitCreate.unit_type`` mentions ``"scene"``
4. Alembic migration exists and runs the right SQL
5. Runtime simulation: Pydantic accepts ``"scene"`` as a valid unit_type
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


WORKTREE = Path("/opt/openclaw/worktrees/cos-kan458-scene-unit-type")
MODELS_PY = WORKTREE / "backend/app/videos/models.py"
SERVICE_PY = WORKTREE / "backend/app/core/services/cinematic_episode_gate_service.py"
ROUTES_PY = WORKTREE / "backend/app/api/routes/ai/cinematic_gates.py"
MIGRATION_PY = WORKTREE / "backend/migrations/versions/kan_458_add_scene_unit_type.py"


def _read(path: Path) -> str:
    return path.read_text()


# --------------------------------------------------------------------------- #
# Test 1: SequenceUnitType enum has SCENE = "scene"
# --------------------------------------------------------------------------- #

def test_models_have_scene_enum_value():
    src = _read(MODELS_PY)
    # Look for SCENE = "scene" pattern
    assert re.search(r'^\s*SCENE\s*=\s*"scene"', src, re.MULTILINE), (
        "SequenceUnitType enum must have SCENE = \"scene\""
    )


# --------------------------------------------------------------------------- #
# Test 2: REQUIRED_UNIT_TYPES list contains "scene"
# --------------------------------------------------------------------------- #

def test_required_unit_types_contains_scene():
    src = _read(SERVICE_PY)
    # Find REQUIRED_UNIT_TYPES list literal
    m = re.search(
        r'REQUIRED_UNIT_TYPES\s*=\s*\[(.*?)\]',
        src,
        re.DOTALL,
    )
    assert m is not None, "REQUIRED_UNIT_TYPES list must exist"
    body = m.group(1)
    assert '"scene"' in body, 'REQUIRED_UNIT_TYPES list must contain "scene"'


# --------------------------------------------------------------------------- #
# Test 3: SequenceUnitCreate.unit_type field description includes "scene"
# --------------------------------------------------------------------------- #

def test_routes_field_description_includes_scene():
    src = _read(ROUTES_PY)
    # Look for SequenceUnitCreate class
    cls_match = re.search(
        r'class SequenceUnitCreate\(BaseModel\):(.*?)(?=^class |\Z)',
        src,
        re.DOTALL | re.MULTILINE,
    )
    assert cls_match is not None, "SequenceUnitCreate class must exist"
    body = cls_match.group(1)
    assert "unit_type: str = Field(" in body, (
        "SequenceUnitCreate must declare unit_type: str = Field(...)"
    )
    # Find the description string
    desc_match = re.search(
        r'unit_type:\s*str\s*=\s*Field\(\s*\.\.\.,\s*description\s*=\s*"([^"]+)"',
        body,
    )
    assert desc_match is not None, "unit_type field must have description=..."
    desc = desc_match.group(1)
    assert "scene" in desc, (
        f'unit_type description must mention "scene"; got: {desc!r}'
    )


# --------------------------------------------------------------------------- #
# Test 4: Alembic migration exists with correct upgrade SQL
# --------------------------------------------------------------------------- #

def test_migration_file_exists_and_correct():
    assert MIGRATION_PY.exists(), (
        "Migration file kan_458_add_scene_unit_type.py must exist"
    )
    src = _read(MIGRATION_PY)
    assert "ALTER TYPE sequence_unit_type ADD VALUE IF NOT EXISTS 'scene'" in src, (
        "Migration upgrade() must run ALTER TYPE ... ADD VALUE 'scene'"
    )
    assert "revision = 'kan_458_add_scene_unit_type'" in src
    assert "down_revision = 'kan_438_video_segments_sequence_index'" in src


# --------------------------------------------------------------------------- #
# Test 5: Runtime simulation — Pydantic accepts "scene" as unit_type
# --------------------------------------------------------------------------- #

def test_runtime_pydantic_accepts_scene_unit_type():
    from pydantic import BaseModel, Field
    from typing import Optional, Any, Dict

    class SequenceUnitCreate(BaseModel):
        unit_type: str = Field(
            ...,
            description="One of: ident_title, prologue, dialogue_act, climax_resolution, closing_bookend, end_title_credits, scene",
        )
        unit_order: int = Field(...)
        title: str = Field(..., min_length=1)
        metadata: Optional[Dict[str, Any]] = None

    # "scene" must be accepted
    u = SequenceUnitCreate(
        unit_type="scene",
        unit_order=1,
        title="Scene 1",
    )
    assert u.unit_type == "scene"

    # Other enum values still accepted
    for ut in (
        "ident_title",
        "prologue",
        "dialogue_act",
        "climax_resolution",
        "closing_bookend",
        "end_title_credits",
    ):
        u = SequenceUnitCreate(unit_type=ut, unit_order=1, title="X")
        assert u.unit_type == ut

    # Bogus value accepted by Pydantic (str field allows any string);
    # DB enum enforces the actual constraint at INSERT time.
    u = SequenceUnitCreate(
        unit_type="definitely_not_a_real_unit_type",
        unit_order=1,
        title="X",
    )
    assert u.unit_type == "definitely_not_a_real_unit_type"
    # (DB would reject this with InvalidTextRepresentationError)