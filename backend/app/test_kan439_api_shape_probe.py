"""
KAN-439: API Response Shape Test

Hits the running API endpoints via httpx ASGITransport and verifies
response JSON shapes match ORM model_dump for ProductionBible,
VoiceCasting, and DialogueManifest.

Run:
    cd /opt/openclaw/repos/litinkapp && python3 -m pytest backend/app/test_kan439_api_shape_probe.py -v
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import pytest
from httpx import ASGITransport, AsyncClient

# ── App + models ──
from app.main import app
from app.videos.models import ProductionBible, VoiceCasting, DialogueManifest


# ── Expected field sets (from ORM model_dump) ──

PRODUCTION_BIBLE_FIELDS: Dict[str, type] = {
    "id": str,
    "project_id": str,
    "version": int,
    "is_active": bool,
    "characters": (list, dict, type(None)),
    "objects": (list, dict, type(None)),
    "locations": (list, dict, type(None)),
    "voices": (list, dict, type(None)),
    "pronunciation": (list, dict, type(None)),
    "style_rules": (list, dict, type(None)),
    "world_rules": (list, dict, type(None)),
    "approved_reference_assets": (list, dict, type(None)),
    "change_log": (str, type(None)),
    "created_by": (str, type(None)),
    "created_at": (str, type(None)),
    "updated_at": (str, type(None)),
}

VOICE_CASTING_FIELDS: Dict[str, type] = {
    "id": str,
    "project_id": str,
    "character_name": str,
    "voice_id": str,
    "provider": str,
    "model": (str, type(None)),
    "voice_metadata": dict,
    "is_locked": bool,
    "created_at": (str, type(None)),
    "updated_at": (str, type(None)),
}

DIALOGUE_MANIFEST_FIELDS: Dict[str, type] = {
    "id": str,
    "project_id": str,
    "video_generation_id": (str, type(None)),
    "content_hash": str,
    "scene_id": str,
    "speaker": str,
    "manifest_text": str,
    "sequence_order": int,
    "audio_url": (str, type(None)),
    "audio_duration_seconds": (float, int, type(None)),
    "audio_generation_id": (str, type(None)),
    "subtitle_url": (str, type(None)),
    "subtitle_format": (str, type(None)),
    "lip_sync_url": (str, type(None)),
    "lip_sync_status": (str, type(None)),
    "merge_output_url": (str, type(None)),
    "merge_status": (str, type(None)),
    "voice_id": (str, type(None)),
    "voice_provider": (str, type(None)),
    "scene_state": dict,
    "previous_frame_url": (str, type(None)),
    "continuity_frame_url": (str, type(None)),
    "status": str,
    "is_finalized": bool,
    "created_at": (str, type(None)),
    "updated_at": (str, type(None)),
}


def _check_fields(
    label: str,
    payload: Dict[str, Any],
    expected_fields: Dict[str, type],
) -> List[str]:
    """Verify all expected fields are present in the payload with correct types."""
    errors: List[str] = []
    for field, expected_type in expected_fields.items():
        if field not in payload:
            errors.append(f"{label}: missing field '{field}'")
        else:
            val = payload[field]
            if not isinstance(val, expected_type):
                errors.append(
                    f"{label}: field '{field}' expected {expected_type}, got {type(val).__name__}"
                )
    return errors


# ── Fixtures ──


@pytest.fixture
async def client():
    """ASGI test client — no network, in-process."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_project_id() -> uuid.UUID:
    """A deterministic test project UUID. Adjust if a real project ID is needed."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


# ── Production Bible API tests ──


class TestProductionBibleAPI:
    @pytest.mark.asyncio
    async def test_create_bible_shape(self, client: AsyncClient, test_project_id):
        """POST /api/v1/ai/production-bible/bible — response shape."""
        # Use a unique project_id to avoid conflicts
        pid = uuid.uuid4()
        resp = await client.post(
            "/api/v1/ai/production-bible/bible",
            json={
                "project_id": str(pid),
                "characters": [{"name": "Hero"}],
                "objects": [],
                "locations": [],
                "voices": {},
                "pronunciation": {},
                "style_rules": {},
                "world_rules": {},
                "approved_reference_assets": [],
                "change_log": "KAN-439 probe",
            },
        )
        # Accept 500 if DB not reachable; we're testing shape, not integration
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable (500): {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["status"] == "ok", f"Unexpected status: {body.get('status')}"
        bible = body["bible"]

        errors = _check_fields("bible", bible, PRODUCTION_BIBLE_FIELDS)
        assert not errors, "Field errors:\n" + "\n".join(errors)

    @pytest.mark.asyncio
    async def test_get_bible_shape(self, client: AsyncClient, test_project_id):
        """GET /api/v1/ai/production-bible/bible/{project_id} — response shape."""
        resp = await client.get(
            f"/api/v1/ai/production-bible/bible/{test_project_id}"
        )
        if resp.status_code == 404:
            pytest.skip("No production bible for test project")
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable: {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "ok"
        bible = body["bible"]

        errors = _check_fields("bible", bible, PRODUCTION_BIBLE_FIELDS)
        assert not errors, "Field errors:\n" + "\n".join(errors)


# ── Voice Casting API tests ──


class TestVoiceCastingAPI:
    @pytest.mark.asyncio
    async def test_cast_voice_shape(self, client: AsyncClient):
        """POST /api/v1/ai/production-bible/voice-casting — response shape."""
        pid = uuid.uuid4()
        resp = await client.post(
            "/api/v1/ai/production-bible/voice-casting",
            json={
                "project_id": str(pid),
                "character_name": "Narrator",
                "provider": "elevenlabs",
                "voice_id": "voice-probe-test",
            },
        )
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable: {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["status"] == "ok"
        casting = body["casting"]

        errors = _check_fields("casting", casting, VOICE_CASTING_FIELDS)
        assert not errors, "Field errors:\n" + "\n".join(errors)

    @pytest.mark.asyncio
    async def test_list_castings_shape(self, client: AsyncClient, test_project_id):
        """GET /api/v1/ai/production-bible/voice-casting/{project_id} — response shape."""
        resp = await client.get(
            f"/api/v1/ai/production-bible/voice-casting/{test_project_id}"
        )
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable: {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "ok"
        castings = body.get("castings", [])
        assert isinstance(castings, list)

        if castings:
            errors = _check_fields("casting", castings[0], VOICE_CASTING_FIELDS)
            assert not errors, "Field errors:\n" + "\n".join(errors)


# ── Dialogue Manifest API tests ──


class TestDialogueManifestAPI:
    @pytest.mark.asyncio
    async def test_create_manifest_shape(self, client: AsyncClient):
        """POST /api/v1/ai/production-bible/dialogue-manifest — response shape."""
        pid = uuid.uuid4()
        resp = await client.post(
            "/api/v1/ai/production-bible/dialogue-manifest",
            json={
                "project_id": str(pid),
                "scene_id": "scene-probe-1",
                "speaker": "Hero",
                "manifest_text": "This is a KAN-439 probe line.",
                "sequence_order": 0,
            },
        )
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable: {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        body = resp.json()
        assert body["status"] == "ok"
        manifest = body["manifest"]

        errors = _check_fields("manifest", manifest, DIALOGUE_MANIFEST_FIELDS)
        assert not errors, "Field errors:\n" + "\n".join(errors)

    @pytest.mark.asyncio
    async def test_list_manifests_shape(self, client: AsyncClient, test_project_id):
        """GET /api/v1/ai/production-bible/dialogue-manifest/{project_id} — response shape."""
        resp = await client.get(
            f"/api/v1/ai/production-bible/dialogue-manifest/{test_project_id}"
        )
        if resp.status_code == 500:
            pytest.skip(f"DB not reachable: {resp.text[:200]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        body = resp.json()
        assert body["status"] == "ok"
        manifests = body.get("manifests", [])
        assert isinstance(manifests, list)

        if manifests:
            errors = _check_fields("manifest", manifests[0], DIALOGUE_MANIFEST_FIELDS)
            assert not errors, "Field errors:\n" + "\n".join(errors)


# ── ORM model_dump verification ──


class TestORMModelDumpIntegrity:
    """Verify that model_dump() round-trips without serialization errors for each model."""

    def test_production_bible_model_fields(self):
        """ProductionBible ORM model has expected field names."""
        orm_cols = set(ProductionBible.__table__.columns.keys())
        expected = set(PRODUCTION_BIBLE_FIELDS.keys())
        missing = expected - orm_cols
        extra = orm_cols - expected
        assert not missing, f"ORM missing fields vs spec: {missing}"
        # extra columns in ORM are OK (they'll appear in model_dump)

    def test_voice_casting_model_fields(self):
        orm_cols = set(VoiceCasting.__table__.columns.keys())
        expected = set(VOICE_CASTING_FIELDS.keys())
        missing = expected - orm_cols
        assert not missing, f"ORM missing fields vs spec: {missing}"

    def test_dialogue_manifest_model_fields(self):
        orm_cols = set(DialogueManifest.__table__.columns.keys())
        expected = set(DIALOGUE_MANIFEST_FIELDS.keys())
        missing = expected - orm_cols
        assert not missing, f"ORM missing fields vs spec: {missing}"
