"""Focused runtime contracts for KAN-438/KAN-439.

These checks prevent the ORM-class contamination and doubled API-prefix defects
that reached staging in f8e7f4b.
"""

import uuid
from pathlib import Path

from app.videos.models import (
    DialogueManifest,
    LineTracking,
    ProductionBible,
    VoiceCasting,
)


def _columns(model):
    return set(model.__table__.columns.keys())


def test_kan438_cinematic_routes_match_the_frontend_contract():
    route_source = (Path(__file__).parents[1] / "app/api/routes/ai/cinematic_gates.py").read_text()
    mount_source = (Path(__file__).parents[1] / "app/api/routes/ai/__init__.py").read_text()

    assert 'prefix="/cinematic-gates"' in mount_source
    assert '"/{vg_id}/sequence-units"' in route_source
    assert '@router.patch("/line-tracking/{line_id}")' in route_source
    assert '"/{vg_id}/continuity-references"' in route_source
    assert '"/{vg_id}/gate-status"' in route_source
    assert "/api/v1" not in mount_source


def test_kan438_line_tracking_contains_only_migrated_columns():
    assert _columns(LineTracking) == {
        "id", "sequence_unit_id", "video_generation_id", "line_text",
        "character_name", "voice_id", "scene_id", "shot_id",
        "source_audio_url", "lipsync_task_id", "resolved_provider",
        "resolved_model", "timeline_position_ms", "status", "metadata",
        "created_at", "updated_at",
    }


def test_kan439_orm_models_match_migrated_schema():
    assert "video_generation_id" not in _columns(ProductionBible)
    assert "unit_type" not in _columns(ProductionBible)
    assert "video_generation_id" not in _columns(VoiceCasting)
    assert "total_shots" not in _columns(VoiceCasting)
    assert "reference_type" not in _columns(DialogueManifest)
    assert "project_id" in _columns(DialogueManifest)
    # ORM attribute is manifest_text but DB column is mapped to "text"
    assert "text" in _columns(DialogueManifest)
    assert "manifest_text" not in _columns(DialogueManifest)


def test_kan439_multi_shot_dialogue_and_continuity_payload_survives_orm_construction():
    project_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    manifest = DialogueManifest(
        project_id=project_id,
        video_generation_id=generation_id,
        content_hash="multi-shot-dialogue-hash",
        scene_id="scene-7",
        speaker="Ada",
        manifest_text="We keep the same coat across both shots.",
        sequence_order=2,
        scene_state={"wardrobe": "blue coat", "shot_ids": ["shot-1", "shot-2"]},
        previous_frame_url="s3://frames/shot-1.png",
        continuity_frame_url="s3://frames/shot-2.png",
    )

    assert manifest.video_generation_id == generation_id
    assert manifest.scene_state["shot_ids"] == ["shot-1", "shot-2"]
    assert manifest.previous_frame_url.endswith("shot-1.png")
    assert manifest.continuity_frame_url.endswith("shot-2.png")
