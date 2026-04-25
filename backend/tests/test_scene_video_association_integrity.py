import uuid
from types import SimpleNamespace

from app.videos.association_integrity import (
    dedupe_scene_videos,
    extract_shot_selections,
    is_audio_record_in_context,
    resolve_scene_identity,
    resolve_target_scene_numbers,
)


def test_scene_context_filters_out_other_script_assets():
    script_a = str(uuid.uuid4())
    script_b = str(uuid.uuid4())

    selected = extract_shot_selections(
        [f"scene-1741461012-0-0-{script_a}", f"scene-1741461012-0-0-{script_b}"],
        expected_script_id=script_a,
    )
    assert [(s.scene_index, s.shot_index) for s in selected] == [(0, 0)]

    wrong_script_audio = SimpleNamespace(script_id=script_b, sequence_order=1, scene_id="scene_1")
    assert is_audio_record_in_context(wrong_script_audio, script_a, [1]) is False


def test_kan86_audio_context_uses_metadata_scene_number_when_scene_fields_missing():
    script_id = str(uuid.uuid4())
    audio = SimpleNamespace(
        script_id=script_id,
        scene_id=None,
        sequence_order=None,
        audio_metadata={"scene_number": 1},
    )

    assert is_audio_record_in_context(audio, script_id, [1]) is True


def test_kan86_audio_context_rejects_mismatched_metadata_scene_number():
    script_id = str(uuid.uuid4())
    audio = SimpleNamespace(
        script_id=script_id,
        scene_id=None,
        sequence_order=None,
        audio_metadata={"scene_number": 2},
    )

    assert is_audio_record_in_context(audio, script_id, [1]) is False


def test_kan86_audio_context_ignores_non_dict_metadata_before_sequence_fallback():
    script_id = str(uuid.uuid4())
    audio = SimpleNamespace(
        script_id=script_id,
        scene_id=None,
        sequence_order=None,
        audio_metadata='{"scene_number": 1}',
    )

    assert is_audio_record_in_context(audio, script_id, [1]) is False


def test_deduplicate_scene_videos_by_deterministic_key():
    scene_videos = [
        {
            "scene_id": "scene_1",
            "scene_sequence": 1,
            "source_image": "img-a",
            "video_url": "https://video/1.mp4",
            "method": "veo2_image_to_video_sequential",
        },
        {
            "scene_id": "scene_1",
            "scene_sequence": 1,
            "source_image": "img-a",
            "video_url": "https://video/1.mp4",
            "method": "veo2_image_to_video_sequential",
        },
        {
            "scene_id": "scene_1",
            "scene_sequence": 1,
            "source_image": "img-b",
            "video_url": "https://video/2.mp4",
            "method": "veo2_image_to_video_sequential",
        },
    ]

    deduped = dedupe_scene_videos(scene_videos)
    assert len(deduped) == 2


def test_single_shot_keeps_true_scene_sequence():
    scene_num, scene_id = resolve_scene_identity(loop_index=0, scene_numbers=[4])
    assert scene_num == 4
    assert scene_id == "scene_4"


def test_extract_shot_selections_handles_numeric_prefix_script_id():
    script_id = "12345678-aaaa-bbbb-cccc-1234567890ab"
    selected = extract_shot_selections(
        [f"scene-1741461012-0-{script_id}"], expected_script_id=script_id
    )
    assert len(selected) == 1
    assert selected[0].scene_index == 0
    assert selected[0].shot_index == 0
    assert selected[0].script_id == script_id


def test_kan86_extract_shot_selection_handles_scene_number_before_uuid():
    script_id = "c5942431-1552-4f50-a23e-73d8d1d6fb3a"
    selected = extract_shot_selections(
        [f"scene-1777133288345-0-1-0-{script_id}"], expected_script_id=script_id
    )
    assert len(selected) == 1
    assert selected[0].scene_index == 0
    assert selected[0].shot_index == 0
    assert selected[0].script_id == script_id


def test_kan86_target_scene_numbers_support_string_scene_descriptions():
    assert resolve_target_scene_numbers(
        selected_shot_ids=None,
        expected_script_id="script-a",
        scene_descriptions=["Opening shot", "Closing shot"],
    ) == [1, 2]


def test_kan86_target_scene_numbers_support_mixed_scene_description_shapes():
    scene_obj = SimpleNamespace(scene_number="4", description="object scene")
    scenes = [
        {"scene_number": "2", "description": "dict scene"},
        "string scene",
        scene_obj,
        {"description": "missing explicit scene number"},
        SimpleNamespace(description="object missing scene_number"),
    ]
    assert resolve_target_scene_numbers(None, "script-a", scenes) == [2, 4, 5]


def test_kan86_target_scene_numbers_prefers_selected_shot_ids():
    script_id = "c5942431-1552-4f50-a23e-73d8d1d6fb3a"
    selected_shot_ids = [f"scene-1777133288345-2-3-0-{script_id}"]
    assert resolve_target_scene_numbers(
        selected_shot_ids,
        script_id,
        ["Scene 1", "Scene 2", "Scene 3"],
    ) == [3]

from app.tasks.video_tasks import find_scene_audio


def test_kan86_find_scene_audio_refuses_unrelated_url_fallback():
    audio_files = {
        "characters": [],
        "narrator": [
            {"id": "audio-scene-2", "scene": 2, "scene_number": 2, "audio_url": "https://cdn/audio-2.mp3"}
        ],
        "sound_effects": [],
        "background_music": [],
    }

    assert find_scene_audio("scene_1", audio_files) is None


def test_kan86_find_scene_audio_requires_selected_audio_scene_match():
    audio_files = {
        "characters": [
            {"id": "wrong-scene", "scene": 2, "scene_number": 2, "audio_url": "https://cdn/audio-2.mp3"},
            {"id": "right-scene", "scene": 1, "scene_number": 1, "audio_url": "https://cdn/audio-1.mp3"},
        ],
        "narrator": [],
        "sound_effects": [],
        "background_music": [],
    }

    selected = find_scene_audio("scene_1", audio_files, selected_audio_ids=["wrong-scene"])
    assert selected is None

    selected = find_scene_audio("scene_1", audio_files, selected_audio_ids=["right-scene"])
    assert selected["id"] == "right-scene"

from app.tasks.video_tasks import normalize_target_scene_numbers, select_scene_assets_for_targets


def test_kan86_persisted_target_scene_filters_and_reorders_scene_images():
    target_scene_numbers = normalize_target_scene_numbers(["1"])
    pre_gen_scene_images = [
        {"id": "scene-2-image", "scene_number": 2, "shot_index": 0, "image_url": "https://cdn/scene2.png"},
        {"id": "scene-1-image", "scene_number": 1, "shot_index": 0, "image_url": "https://cdn/scene1.png"},
    ]
    scene_image_map = {
        int(img["scene_number"]): {int(img["shot_index"]): img}
        for img in pre_gen_scene_images
    }

    descriptions, scene_numbers, images = select_scene_assets_for_targets(
        target_scene_numbers=target_scene_numbers,
        original_scene_descriptions=["Scene one", "Scene two"],
        scene_image_map=scene_image_map,
        pre_gen_scene_images=pre_gen_scene_images,
        pre_gen_character_images=[],
        selected_shots=[],
    )

    assert descriptions == ["Scene one"]
    assert scene_numbers == [1]
    assert [img["id"] for img in images] == ["scene-1-image"]


def test_kan86_find_scene_audio_normalizes_legacy_zero_based_scene_one_payload():
    audio_files = {
        "characters": [
            {"id": "selected-scene-1", "scene": 0, "scene_number": 0, "audio_url": "https://cdn/audio-1.mp3"},
        ],
        "narrator": [],
        "sound_effects": [],
        "background_music": [],
    }

    selected = find_scene_audio(
        "scene_1", audio_files, selected_audio_ids=["selected-scene-1"]
    )
    assert selected["id"] == "selected-scene-1"

from unittest.mock import AsyncMock
import pytest

from app.tasks.video_tasks import (
    generate_scene_videos,
    normalize_media_url_for_internal_access,
    normalize_media_url_for_provider,
)


def test_kan86_provider_media_url_rewrites_localhost_minio_to_public_url(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "https://minio-public.example.com")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")

    stored_url = "http://localhost:9000/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"

    assert (
        normalize_media_url_for_provider(stored_url)
        == "https://minio-public.example.com/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"
    )
    assert (
        normalize_media_url_for_internal_access(stored_url)
        == "http://minio:9000/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"
    )


def test_kan86_provider_media_url_leaves_external_urls_unchanged(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "https://minio-public.example.com")
    external_url = "https://cdn.example.com/litink-books/users/u1/images/scene.png"

    assert normalize_media_url_for_provider(external_url) == external_url


class _RecordingModelsLabService:
    def __init__(self):
        self.calls = []

    def get_min_audio_duration(self, model_id):
        return 1.0

    def get_max_audio_duration(self, model_id):
        return 15.0

    async def generate_image_to_video(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "error", "error": "test stops before provider generation result handling"}


@pytest.mark.asyncio
async def test_kan86_selected_scene_audio_flow_passes_public_media_urls_to_provider(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "https://minio-public.example.com")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")

    service = _RecordingModelsLabService()
    session = AsyncMock()
    image_url = "http://localhost:9000/litink-books/users/u1/images/scene-1.png"
    audio_url = "http://localhost:9000/litink-books/users/u1/audio/scene-1.mp3"

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="video-gen-1",
        scene_descriptions=["Scene one only"],
        audio_files={
            "characters": [
                {"id": "audio-1", "scene": 1, "scene_number": 1, "audio_url": audio_url, "duration": 3.0},
                {"id": "audio-2", "scene": 2, "scene_number": 2, "audio_url": "http://localhost:9000/litink-books/users/u1/audio/scene-2.mp3", "duration": 3.0},
            ],
            "narrator": [],
            "sound_effects": [],
            "background_music": [],
        },
        image_data={"scene_images": [{"id": "img-1", "scene_number": 1, "shot_index": 0, "image_url": image_url}]},
        video_style="realistic",
        script_data={"script": "", "characters": []},
        user_id="u1",
        session=session,
        scene_numbers=[1],
        selected_audio_ids=["audio-1"],
    )

    assert result == [None]
    assert len(service.calls) == 1
    assert service.calls[0]["image_url"] == "https://minio-public.example.com/litink-books/users/u1/images/scene-1.png"
    assert service.calls[0]["init_audio"] == "https://minio-public.example.com/litink-books/users/u1/audio/scene-1.mp3"


class _RecordingSession:
    def __init__(self):
        self.executed = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))
        return SimpleNamespace(scalar=lambda: "segment-id")

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class _ProviderFailureService(_RecordingModelsLabService):
    async def generate_image_to_video(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "error", "error": "provider refused media"}


@pytest.mark.asyncio
async def test_kan86_failed_segment_insert_has_required_counts_and_provider_diagnostics(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "https://minio-public.example.com")
    session = _RecordingSession()
    service = _ProviderFailureService()

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={"scene_images": [{"image_url": "http://localhost:9000/bucket/scene.png?secret=1"}]},
        video_style="realistic",
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1],
    )

    assert result == [None]
    diagnostic_calls = [params for stmt, params in session.executed if "provider_attempts" in stmt]
    assert diagnostic_calls, "provider diagnostics should be persisted to task_meta"
    assert "provider refused media" in diagnostic_calls[0]["diagnostic"]
    assert "secret=1" not in diagnostic_calls[0]["diagnostic"]

    failed_inserts = [params for stmt, params in session.executed if "INSERT INTO video_segments" in stmt]
    assert failed_inserts
    assert failed_inserts[-1]["user_id"] == "22222222-2222-2222-2222-222222222222"
    assert failed_inserts[-1]["character_count"] == 0
    assert failed_inserts[-1]["dialogue_count"] == 0
    assert failed_inserts[-1]["action_count"] == 0
    assert failed_inserts[-1]["status"] == "failed"


class _ProviderSuccessService(_RecordingModelsLabService):
    async def generate_image_to_video(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "success", "video_url": "https://cdn.example.com/video.mp4"}


class _NoopStorage:
    async def persist_from_url(self, url, *args, **kwargs):
        return "https://storage.example.com/video.mp4"


@pytest.mark.asyncio
async def test_kan86_success_segment_insert_has_required_counts(monkeypatch):
    monkeypatch.setattr("app.core.services.storage.get_storage_service", lambda: _NoopStorage())
    monkeypatch.setattr("app.tasks.video_tasks.extract_last_frame", AsyncMock(return_value="https://storage.example.com/frame.jpg"))
    session = _RecordingSession()

    result = await generate_scene_videos(
        modelslab_service=_ProviderSuccessService(),
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={"scene_images": [{"image_url": "https://cdn.example.com/scene.png"}]},
        video_style="realistic",
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1],
    )

    assert result[0]["video_url"] == "https://storage.example.com/video.mp4"
    completed_inserts = [params for stmt, params in session.executed if "INSERT INTO video_segments" in stmt]
    assert completed_inserts
    assert completed_inserts[-1]["status"] == "completed"
    assert completed_inserts[-1]["user_id"] == "22222222-2222-2222-2222-222222222222"
    assert completed_inserts[-1]["character_count"] == 0
    assert completed_inserts[-1]["dialogue_count"] == 0
    assert completed_inserts[-1]["action_count"] == 0
