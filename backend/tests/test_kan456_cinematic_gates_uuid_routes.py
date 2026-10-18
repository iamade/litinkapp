"""Route-level regression coverage for KAN-456 UUID response serialization."""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.api.routes.ai import cinematic_gates
from app.core.auth import get_current_active_user
from app.core.database import get_session

VG_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
UNIT_ID = uuid.UUID("10000000-0000-0000-0000-000000000002")
LINE_ID = uuid.UUID("10000000-0000-0000-0000-000000000003")
REFERENCE_ID = uuid.UUID("10000000-0000-0000-0000-000000000004")


def sequence_unit_row():
    return {"id": UNIT_ID, "video_generation_id": VG_ID, "unit_type": "scene", "unit_order": 1, "title": "Opening", "metadata": {"source": "asyncpg"}}


def line_tracking_row():
    return {"id": LINE_ID, "sequence_unit_id": UNIT_ID, "video_generation_id": VG_ID, "line_text": "Hello", "status": "placed", "metadata": {"source": "asyncpg"}, "unit_type": "scene", "unit_order": 1}


def continuity_reference_row():
    return {"id": REFERENCE_ID, "video_generation_id": VG_ID, "reference_type": "character", "reference_id": "character-42", "reference_data": {"name": "Ari"}, "shot_ids": ["shot-1"], "adjacent_shot_qa": {}}


class GateServiceStub:
    async def get_sequence_units(self, vg_id, session):
        return [sequence_unit_row()]

    async def get_full_line_tracking(self, vg_id, session):
        return [line_tracking_row()]

    async def create_sequence_units(self, vg_id, units_data, session):
        return [sequence_unit_row()]


class ContinuityServiceStub:
    async def get_references(self, vg_id, reference_type, session):
        return [continuity_reference_row()]

    async def create_reference(self, vg_id, ref_type, ref_id, ref_data, session, shot_ids):
        return continuity_reference_row()


def app_with_stubs(monkeypatch):
    app = FastAPI()
    # Production nesting: API_V1_STR + /ai + /cinematic-gates.
    app.include_router(cinematic_gates.router, prefix="/api/v1/ai/cinematic-gates")

    async def session_override():
        yield object()

    async def user_override():
        return object()

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_active_user] = user_override
    monkeypatch.setattr(cinematic_gates, "_gate_service", GateServiceStub())
    monkeypatch.setattr(cinematic_gates, "_continuity_service", ContinuityServiceStub())
    return app


def assert_uuid_json(payload, **expected):
    for key, value in expected.items():
        assert isinstance(payload[key], str)
        assert payload[key] == str(value)


def test_sequence_unit_routes_serialize_asyncpg_uuids(monkeypatch):
    client = TestClient(app_with_stubs(monkeypatch))
    base = f"/api/v1/ai/cinematic-gates/{VG_ID}"
    listed = client.get(f"{base}/sequence-units")
    created = client.post(f"{base}/sequence-units", json={"units": [{"unit_type": "scene", "unit_order": 1, "title": "Opening"}]})
    assert listed.status_code == 200
    assert created.status_code == 200
    for response in (listed, created):
        assert_uuid_json(response.json()[0], id=UNIT_ID, video_generation_id=VG_ID)


def test_line_tracking_route_serializes_asyncpg_uuids(monkeypatch):
    response = TestClient(app_with_stubs(monkeypatch)).get(f"/api/v1/ai/cinematic-gates/{VG_ID}/line-tracking")
    assert response.status_code == 200
    assert_uuid_json(response.json()[0], id=LINE_ID, sequence_unit_id=UNIT_ID, video_generation_id=VG_ID)


def test_continuity_reference_routes_serialize_asyncpg_uuids(monkeypatch):
    client = TestClient(app_with_stubs(monkeypatch))
    base = f"/api/v1/ai/cinematic-gates/{VG_ID}/continuity-references"
    listed = client.get(base)
    created = client.post(base, json={"reference_type": "character", "reference_id": "character-42", "reference_data": {"name": "Ari"}, "shot_ids": ["shot-1"]})
    assert listed.status_code == 200
    assert created.status_code == 200
    assert_uuid_json(listed.json()[0], id=REFERENCE_ID, video_generation_id=VG_ID)
    assert_uuid_json(created.json(), id=REFERENCE_ID, video_generation_id=VG_ID)
    assert listed.json()[0]["reference_id"] == "character-42"
    assert created.json()["reference_id"] == "character-42"


def test_harness_detects_a_strict_string_schema_without_uuid_coercion():
    """Negative control: this route rejects a UUID for a strict str id."""
    class BrokenResponse(BaseModel):
        model_config = ConfigDict(strict=True)
        id: str

    app = FastAPI()

    @app.get("/broken", response_model=BrokenResponse)
    async def broken():
        return {"id": UNIT_ID}

    response = TestClient(app, raise_server_exceptions=False).get("/broken")
    assert response.status_code == 500
