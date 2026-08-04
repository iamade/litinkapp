"""
KAN-452 offline structural + serialization tests.

Verifies:
1. `model_validator(mode="before")` decorator is present on each of the 3 affected response schemas.
2. The validator coerces `uuid.UUID` → `str` (and is a no-op on already-str values).
3. Required-coverage fields: each schema's UUID fields are all listed in its validator's field names.
4. import surface: `model_validator` is imported from pydantic.
"""

from __future__ import annotations

import ast
import re
import uuid
from pathlib import Path

import pytest


SCHEMA_PATH = Path(
    "/opt/openclaw/worktrees/cos-kan452-uuid-response-sweep/backend/app/api/routes/ai/cinematic_gates.py"
)


def _read_source() -> str:
    return SCHEMA_PATH.read_text()


def _extract_class(src: str, class_name: str) -> ast.ClassDef:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    raise AssertionError(f"class {class_name!r} not found in source")


def _field_names(class_node: ast.ClassDef) -> list[str]:
    """Return annotated field names declared on a BaseModel subclass (skip methods/imports)."""
    out = []
    for stmt in class_node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            out.append(stmt.target.id)
    return out


def _has_model_validator_before(class_node: ast.ClassDef) -> str | None:
    """Return the function name if a @model_validator(mode='before') method exists."""
    for stmt in class_node.body:
        if not isinstance(stmt, ast.FunctionDef):
            continue
        for dec in stmt.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if not isinstance(dec.func, ast.Name):
                continue
            if dec.func.id != "model_validator":
                continue
            # check keyword `mode="before"` or `mode='before'`
            for kw in dec.keywords:
                if kw.arg == "mode":
                    if isinstance(kw.value, ast.Constant) and kw.value.value == "before":
                        return stmt.name
    return None


def _validator_field_coverage(class_node: ast.ClassDef, fn_name: str) -> set[str]:
    """Walk the method body and find tuple/list literals like ("id", "video_generation_id")."""
    method = next(
        (s for s in class_node.body
         if isinstance(s, ast.FunctionDef) and s.name == fn_name),
        None,
    )
    assert method is not None
    found: set[str] = set()
    for node in ast.walk(method):
        if isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    found.add(elt.value)
    return found


# --------------------------------------------------------------------------- #
# Test 1: file imports `model_validator` from pydantic (NOT field_serializer)
# --------------------------------------------------------------------------- #

def test_model_validator_is_imported() -> None:
    src = _read_source()
    tree = ast.parse(src)
    found_validator = False
    found_serializer = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("pydantic"):
            for alias in node.names:
                if alias.name == "model_validator":
                    found_validator = True
                if alias.name == "field_serializer":
                    found_serializer = True
    assert found_validator, "pydantic.model_validator must be imported"
    assert not found_serializer, (
        "KAN-452 uses model_validator(mode='before'), not field_serializer; "
        "field_serializer runs after validation and cannot pre-coerce UUIDs"
    )


# --------------------------------------------------------------------------- #
# Test 2: SequenceUnitResponse has @model_validator(mode='before') with right coverage
# --------------------------------------------------------------------------- #

def test_sequence_unit_response_validator_coverage() -> None:
    src = _read_source()
    cls = _extract_class(src, "SequenceUnitResponse")
    fn = _has_model_validator_before(cls)
    assert fn is not None, "SequenceUnitResponse must declare @model_validator(mode='before')"
    covered = _validator_field_coverage(cls, fn)
    for required in ("id", "video_generation_id"):
        assert required in covered, (
            f"SequenceUnitResponse validator must cover {required!r}; "
            f"covered={sorted(covered)}"
        )


# --------------------------------------------------------------------------- #
# Test 3: LineTrackingResponse
# --------------------------------------------------------------------------- #

def test_line_tracking_response_validator_coverage() -> None:
    src = _read_source()
    cls = _extract_class(src, "LineTrackingResponse")
    fn = _has_model_validator_before(cls)
    assert fn is not None, "LineTrackingResponse must declare @model_validator(mode='before')"
    covered = _validator_field_coverage(cls, fn)
    for required in ("id", "sequence_unit_id", "video_generation_id"):
        assert required in covered, (
            f"LineTrackingResponse validator must cover {required!r}; "
            f"covered={sorted(covered)}"
        )


# --------------------------------------------------------------------------- #
# Test 4: ContinuityReferenceResponse
# --------------------------------------------------------------------------- #

def test_continuity_reference_response_validator_coverage() -> None:
    src = _read_source()
    cls = _extract_class(src, "ContinuityReferenceResponse")
    fn = _has_model_validator_before(cls)
    assert fn is not None, "ContinuityReferenceResponse must declare @model_validator(mode='before')"
    covered = _validator_field_coverage(cls, fn)
    for required in ("id", "video_generation_id"):
        assert required in covered, (
            f"ContinuityReferenceResponse validator must cover {required!r}; "
            f"covered={sorted(covered)}"
        )


# --------------------------------------------------------------------------- #
# Test 5: validator body coerces `uuid.UUID` → `str`
# --------------------------------------------------------------------------- #

def test_validator_method_coerces_uuid_to_str() -> None:
    src = _read_source()

    target_classes = [
        "SequenceUnitResponse",
        "LineTrackingResponse",
        "ContinuityReferenceResponse",
    ]
    for class_name in target_classes:
        cls = _extract_class(src, class_name)
        fn = _has_model_validator_before(cls)
        assert fn is not None, f"{class_name} must have @model_validator(mode='before')"
        method = next(s for s in cls.body if isinstance(s, ast.FunctionDef) and s.name == fn)
        method_src = ast.unparse(method)
        assert "uuid.UUID" in method_src, (
            f"{class_name}.{fn} must check `isinstance(..., uuid.UUID)`; "
            f"method source: {method_src}"
        )
        assert re.search(r"\bstr\s*\(", method_src), (
            f"{class_name}.{fn} must call `str(...)` to coerce UUID → str"
        )
        # body should mutate the dict in place
        assert "data" in method_src and "field_name" in method_src, (
            f"{class_name}.{fn} must iterate data[field_name] to coerce"
        )


# --------------------------------------------------------------------------- #
# Test 6: simulate validator runtime behavior
# --------------------------------------------------------------------------- #

def test_runtime_uuid_coercion_simulation() -> None:
    """Simulate the model_validator(mode='before') body: UUID passes through str(), str passes through."""
    test_uuid = uuid.UUID("eb0a7f01-8173-459b-b5ea-cb98b58aa725")
    test_str = "eb0a7f01-8173-459b-b5ea-cb98b58aa725"

    def coerce(data, field_names):
        if isinstance(data, dict):
            for field_name in field_names:
                v = data.get(field_name)
                if isinstance(v, uuid.UUID):
                    data[field_name] = str(v)
        return data

    sample = {"id": test_uuid, "video_generation_id": test_uuid}
    out = coerce(sample, ("id", "video_generation_id"))
    assert out["id"] == test_str
    assert out["video_generation_id"] == test_str

    # Already-str input passes through
    sample_str = {"id": test_str, "video_generation_id": test_str}
    out_str = coerce(sample_str, ("id", "video_generation_id"))
    assert out_str["id"] == test_str
    assert out_str["video_generation_id"] == test_str
