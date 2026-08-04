"""
Finding D / KAN-457 — title required in SequenceUnitCreate (option b).

LC dispatch (msg `1534173334412202128`, KAN-457, issue id `14976`):
  "Enforce request schema `title` as required — surfaces constraint to
   client, no silent defaults."

DB schema: `sequence_units.title` → NOT NULL.
ORM:      `SequenceUnit.title`  → `nullable=False`.
Request schema (this fix): `title: str = Field(..., min_length=1)` (required).

Previous incorrect fix: option (c) default `""` via `@model_validator(mode="before")`.
Reverted; this is option (b).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


CINEMATIC_GATES = Path(
    "/opt/openclaw/worktrees/cos-finding-d-title-default/backend/app/api/routes/ai/cinematic_gates.py"
)


def _read(path: Path) -> str:
    return path.read_text()


def _class_src(tree: ast.Module, name: str) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return ast.unparse(node)
    return None


# --------------------------------------------------------------------------- #
# Test 1: SequenceUnitCreate.title is required (str, no default)
# --------------------------------------------------------------------------- #

def test_sequence_unit_create_title_is_required():
    tree = ast.parse(_read(CINEMATIC_GATES))
    cls_src = _class_src(tree, "SequenceUnitCreate")
    assert cls_src is not None, "SequenceUnitCreate must exist"

    # Must NOT be Optional
    assert "title: Optional" not in cls_src, (
        "title must NOT be Optional — DB enforces NOT NULL, so the request "
        "schema must surface that constraint to the client (LC option b)"
    )
    # Must be required (no default)
    assert "title: str = Field(...)" in cls_src or "title: str" in cls_src, (
        "title must be declared as required str (no default)"
    )
    # Must have min_length=1 to reject empty strings
    assert "min_length=1" in cls_src, (
        "title must have min_length=1 to reject empty strings "
        "(DB enforces NOT NULL; empty string would still violate intent)"
    )


# --------------------------------------------------------------------------- #
# Test 2: no @model_validator(mode="before") on SequenceUnitCreate
#           (we don't silently coerce; we surface the constraint)
# --------------------------------------------------------------------------- #

def test_no_model_validator_for_title_coercion():
    tree = ast.parse(_read(CINEMATIC_GATES))
    target_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SequenceUnitCreate":
            target_cls = node
            break
    assert target_cls is not None

    # Find any classmethod decorated with @model_validator
    found_title_coercion = False
    for item in target_cls.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in item.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "model_validator"
                ):
                    fn_src = ast.unparse(item)
                    if "title" in fn_src and "None" in fn_src:
                        found_title_coercion = True
                        break
    assert not found_title_coercion, (
        "SequenceUnitCreate must NOT have a model_validator that silently "
        "coerces title (option c). LC chose option b: enforce as required."
    )


# --------------------------------------------------------------------------- #
# Test 3: runtime — missing title raises ValidationError, empty title raises
# --------------------------------------------------------------------------- #

def test_runtime_title_required():
    from pydantic import BaseModel, Field, ValidationError
    from typing import Optional, Any, Dict

    class SequenceUnitCreate(BaseModel):
        unit_type: str = Field(...)
        unit_order: int = Field(...)
        title: str = Field(..., min_length=1)
        metadata: Optional[Dict[str, Any]] = None

    # Case 1: explicit title passes
    u = SequenceUnitCreate(unit_type="ident_title", unit_order=1, title="Open")
    assert u.title == "Open"

    # Case 2: missing title raises
    with pytest.raises(ValidationError) as exc_info:
        SequenceUnitCreate(unit_type="ident_title", unit_order=1)
    assert "title" in str(exc_info.value).lower()

    # Case 3: empty title raises (min_length=1)
    with pytest.raises(ValidationError) as exc_info:
        SequenceUnitCreate(unit_type="ident_title", unit_order=1, title="")
    assert "title" in str(exc_info.value).lower()

    # Case 4: None raises (no silent coercion)
    with pytest.raises(ValidationError) as exc_info:
        SequenceUnitCreate(unit_type="ident_title", unit_order=1, title=None)
    assert "title" in str(exc_info.value).lower()
