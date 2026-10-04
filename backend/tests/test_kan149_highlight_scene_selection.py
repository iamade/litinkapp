"""KAN-149 AC1 highlight scene selection adapter contract tests."""

import os
import uuid

# Test-safe env BEFORE app imports (same pattern as test_kan470_471_auth_error_hardening).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in [
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "REDIS_URL", "CELERY_BROKER_URL",
]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import pytest

from app.trailers import models as trailer_models
from app.trailers.models import TrailerScene
from app.trailers.service import select_highlight_scenes


def _candidate(index: int, score: float | None = None) -> dict:
    return {
        "id": uuid.uuid4(),
        "chapter_id": uuid.uuid4(),
        "source_index": index,
        "scene_title": f"Scene {index}",
        "scene_description": f"Usable trailer highlight scene {index} with clear action and stakes.",
        "action_score": 0.45 + (index % 4) * 0.08,
        "emotional_score": 0.5 + (index % 3) * 0.07,
        "visual_score": 0.55 + (index % 2) * 0.1,
        "narrative_score": 0.6 + (index % 5) * 0.05,
        "overall_score": score if score is not None else 0.4 + index * 0.03,
        "selection_reason": f"Scene {index} is cinematic and trailer-ready.",
    }


def test_select_highlight_scenes_returns_five_to_eight_ordered_with_timing_and_roles():
    candidates = [_candidate(i) for i in range(12)]
    project_id = uuid.uuid4()
    trailer_generation_id = uuid.uuid4()

    selections = select_highlight_scenes(
        candidates,
        project_id=project_id,
        trailer_generation_id=trailer_generation_id,
        target_duration_seconds=60,
        tone="epic",
    )

    assert 5 <= len(selections) <= 8
    assert len(selections) == 8
    assert all(isinstance(selection, TrailerScene) for selection in selections)
    assert [selection.scene_number for selection in selections] == list(range(1, 9))
    assert [selection.selection_order for selection in selections] == list(range(1, 9))
    assert [selection.source_index for selection in selections] == sorted(
        selection.source_index for selection in selections
    )

    cursor = 0.0
    for selection in selections:
        assert selection.is_selected is True
        assert selection.scene_description
        assert selection.trailer_role
        assert selection.project_id == project_id
        assert selection.trailer_generation_id == trailer_generation_id
        assert selection.start_time_seconds == pytest.approx(cursor)
        assert 4.0 <= selection.duration_seconds <= 12.0
        cursor += selection.duration_seconds


def test_select_highlight_scenes_clamps_requested_count_to_ac1_bounds():
    candidates = [_candidate(i) for i in range(12)]

    low = select_highlight_scenes(candidates, target_scene_count=1)
    high = select_highlight_scenes(candidates, target_scene_count=30)

    assert len(low) == 5
    assert [selection.scene_number for selection in low] == list(range(1, 6))
    assert len(high) == 8
    assert [selection.scene_number for selection in high] == list(range(1, 9))


def test_select_highlight_scenes_rejects_insufficient_usable_candidates():
    unusable = [
        {"scene_title": "No description", "overall_score": 1.0},
        {"scene_description": "Description but no title or source", "overall_score": 1.0},
    ]

    with pytest.raises(ValueError, match="at least 5 usable highlight scenes"):
        select_highlight_scenes(unusable)



def test_select_highlight_scenes_accepts_legacy_trailer_scene_candidates():
    trailer_generation_id = uuid.uuid4()
    scenes = [
        TrailerScene(
            trailer_generation_id=trailer_generation_id,
            scene_number=0,
            scene_title=f"Analyzed scene {index}",
            scene_description=f"Analyzed candidate {index} has usable cinematic stakes.",
            action_score=0.4 + index * 0.01,
            emotional_score=0.5,
            visual_score=0.6,
            narrative_score=0.7,
            overall_score=0.55 + index * 0.02,
            selection_reason="legacy analyzed candidate",
        )
        for index in range(7)
    ]

    selections = select_highlight_scenes(
        scenes,
        trailer_generation_id=trailer_generation_id,
        target_scene_count=5,
    )

    assert len(selections) == 5
    assert all(any(selection is scene for scene in scenes) for selection in selections)
    assert all(selection.trailer_generation_id == trailer_generation_id for selection in selections)
    assert {selection.source_scene_id for selection in selections}.issubset(
        {scene.id for scene in scenes}
    )
    assert [selection.scene_number for selection in selections] == [1, 2, 3, 4, 5]
    assert [selection.selection_order for selection in selections] == [1, 2, 3, 4, 5]
    assert all(selection.trailer_role for selection in selections)


def test_select_highlight_scenes_uses_existing_trailer_scene_surface_without_new_table():
    assert not hasattr(trailer_models, "TrailerSelection")
    assert TrailerScene.__tablename__ == "trailer_scenes"

    selections = select_highlight_scenes(
        [_candidate(i) for i in range(5)],
        target_scene_count=5,
    )

    assert all(isinstance(selection, TrailerScene) for selection in selections)
    assert [selection.scene_number for selection in selections] == [1, 2, 3, 4, 5]
    assert all(selection.trailer_role for selection in selections)
    assert all(selection.start_time_seconds >= 0 for selection in selections)
