import json
import uuid
from datetime import datetime, timezone, timedelta
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
    ProviderMediaUrlConfigurationError,
    _json_dumps_safe,
    generate_scene_videos,
    normalize_media_url_for_internal_access,
    normalize_media_url_for_provider,
    rehydrate_media_provider_metadata,
    select_provider_media_source,
)


def test_kan86_provider_media_url_rejects_localhost_without_external_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    monkeypatch.delenv("PUBLIC_MINIO_URL", raising=False)
    monkeypatch.delenv("MINIO_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("MEDIA_PUBLIC_URL", raising=False)
    monkeypatch.delenv("PUBLIC_MEDIA_URL", raising=False)
    monkeypatch.delenv("S3_PUBLIC_URL", raising=False)
    monkeypatch.delenv("CDN_BASE_URL", raising=False)

    stored_url = "http://localhost:9000/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"

    with pytest.raises(ProviderMediaUrlConfigurationError):
        normalize_media_url_for_provider(stored_url)
    assert (
        normalize_media_url_for_internal_access(stored_url)
        == "http://minio:9000/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"
    )


def test_kan86_provider_media_url_rewrites_localhost_minio_to_explicit_provider_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", "https://minio-public.example.com")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)

    stored_url = "http://localhost:9000/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"

    assert (
        normalize_media_url_for_provider(stored_url)
        == "https://minio-public.example.com/litink-books/users/u1/images/scene.png?X-Amz-Signature=secret"
    )


def test_kan86_provider_media_url_rejects_raw_http_ip_minio_without_https_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://72.62.97.111:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    stored_url = "http://72.62.97.111:9000/litink-books/users/u1/images/scene.png"

    with pytest.raises(ProviderMediaUrlConfigurationError) as excinfo:
        normalize_media_url_for_provider(stored_url)
    assert "HTTPS public/CDN/R2/S3 base" in str(excinfo.value)
    assert "72.62.97.111" in str(excinfo.value)


def test_kan86_provider_media_url_rewrites_raw_http_ip_minio_to_https_provider_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://72.62.97.111:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", "https://media.litinkai.example")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)

    stored_url = "http://72.62.97.111:9000/litink-books/users/u1/images/scene.png"

    assert (
        normalize_media_url_for_provider(stored_url)
        == "https://media.litinkai.example/litink-books/users/u1/images/scene.png"
    )


def test_kan86_provider_media_url_ignores_http_ip_provider_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://72.62.97.111:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", "http://72.62.97.111:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    with pytest.raises(ProviderMediaUrlConfigurationError):
        normalize_media_url_for_provider("http://72.62.97.111:9000/litink-books/users/u1/images/scene.png")


def test_kan86_provider_media_url_leaves_external_urls_unchanged(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "https://minio-public.example.com")
    external_url = "https://cdn.example.com/litink-books/users/u1/images/scene.png"

    assert normalize_media_url_for_provider(external_url) == external_url


def test_kan86_provider_media_source_prefers_preserved_provider_cdn_url():
    canonical_url = "http://localhost:9000/litink-books/users/u1/images/scene.png"
    scene_image = {
        "image_url": canonical_url,
        "metadata": {
            "provider_cdn_url": "https://modelslab-cdn.example.com/scene.png?fresh=1",
            "provider_url_created_at": "2999-01-01T00:00:00+00:00",
        },
    }

    assert (
        select_provider_media_source(canonical_url, scene_image)
        == "https://modelslab-cdn.example.com/scene.png?fresh=1"
    )


def test_kan86_provider_media_source_skips_unsafe_metadata_url():
    canonical_url = "https://storage.example.com/litink-books/users/u1/images/scene.png"
    scene_image = {
        "image_url": canonical_url,
        "meta": {
            "provider_cdn_url": "http://72.62.97.111:9000/litink-books/users/u1/images/scene.png",
            "provider_url_created_at": "2999-01-01T00:00:00+00:00",
        },
    }

    assert select_provider_media_source(canonical_url, scene_image) == canonical_url


def test_kan86_provider_media_source_prefers_audio_provider_url_metadata():
    canonical_url = "http://localhost:9000/litink-books/users/u1/audio/scene-1.mp3"
    provider_audio_url = "https://pub-3626123a908346a7a8be8d9295f44e26.r2.dev/generations/4b402da1-f8af-4ee8-97cd-7baca0ad5c05.mp3"
    selected_audio = {
        "id": "ff624d48-0000-4000-8000-000000000000",
        "audio_url": canonical_url,
        "audio_metadata": {
            "provider_audio_url": provider_audio_url,
            "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    assert select_provider_media_source(canonical_url, selected_audio) == provider_audio_url


class _HydrateResult:
    def __init__(self, rows, scalar_value="segment-id"):
        self._rows = rows
        self._scalar_value = scalar_value

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar_value


class _HydrateSession:
    def __init__(self, *, audio_rows=None, image_rows=None):
        self.audio_rows = audio_rows or []
        self.image_rows = image_rows or []
        self.executed = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement, params=None):
        statement_text = str(statement)
        self.executed.append((statement_text, params or {}))
        if "audio_generations" in statement_text:
            return _HydrateResult(self.audio_rows)
        if "image_generations" in statement_text:
            return _HydrateResult(self.image_rows)
        return _HydrateResult([])

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_kan86_rehydrates_selected_audio_snapshot_from_audio_metadata():
    provider_audio_url = "https://pub-3626123a908346a7a8be8d9295f44e26.r2.dev/generations/4b402da1-f8af-4ee8-97cd-7baca0ad5c05.mp3"
    audio_files = {
        "characters": [
            {
                "id": "ff624d48-0000-4000-8000-000000000000",
                "scene": 1,
                "scene_number": 1,
                "audio_url": "http://localhost:9000/litink-books/users/u1/audio/scene-1.mp3",
                "duration": 3.0,
            }
        ],
        "narrator": [],
        "sound_effects": [],
        "background_music": [],
    }
    session = _HydrateSession(
        audio_rows=[
            {
                "id": "ff624d48-0000-4000-8000-000000000000",
                "audio_metadata": {
                    "provider_audio_url": provider_audio_url,
                    "provider_cdn_url": provider_audio_url,
                    "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        ]
    )

    await rehydrate_media_provider_metadata(
        session,
        audio_files=audio_files,
        image_data={"scene_images": []},
        selected_audio_ids=["ff624d48-0000-4000-8000-000000000000"],
    )

    selected_audio = audio_files["characters"][0]
    assert selected_audio["audio_url"].startswith("http://localhost:9000/")
    assert selected_audio["audio_metadata"]["provider_audio_url"] == provider_audio_url
    assert select_provider_media_source(selected_audio["audio_url"], selected_audio) == provider_audio_url


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
async def test_kan86_scene_video_uses_preserved_provider_cdn_image_without_minio_public_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    service = _RecordingModelsLabService()
    session = AsyncMock()
    local_image_url = "http://localhost:9000/litink-books/users/u1/images/scene-1.png"
    provider_cdn_url = "https://modelslab-cdn.example.com/scene-1.png?fresh=1"

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="video-gen-1",
        scene_descriptions=["Scene one only"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={
            "scene_images": [
                {
                    "id": "img-1",
                    "scene_number": 1,
                    "shot_index": 0,
                    "image_url": local_image_url,
                    "metadata": {
                        "provider_cdn_url": provider_cdn_url,
                        "provider_url_created_at": "2999-01-01T00:00:00+00:00",
                    },
                }
            ]
        },
        video_style="realistic",
        script_data={"script": "", "characters": []},
        user_id="u1",
        session=session,
        scene_numbers=[1],
    )

    assert result == [None]
    assert len(service.calls) == 1
    assert service.calls[0]["image_url"] == provider_cdn_url


@pytest.mark.asyncio
async def test_kan86_selected_scene_audio_rehydrates_provider_cdn_and_records_attempt(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    provider_audio_url = "https://pub-3626123a908346a7a8be8d9295f44e26.r2.dev/generations/4b402da1-f8af-4ee8-97cd-7baca0ad5c05.mp3"
    provider_image_url = "https://modelslab-cdn.example.com/scene-1.png"
    service = _RecordingModelsLabService()
    session = _HydrateSession(
        audio_rows=[
            {
                "id": "ff624d48-0000-4000-8000-000000000000",
                "audio_metadata": {
                    "provider_audio_url": provider_audio_url,
                    "provider_cdn_url": provider_audio_url,
                    "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        ]
    )

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one only"],
        audio_files={
            "characters": [
                {
                    "id": "ff624d48-0000-4000-8000-000000000000",
                    "scene": 1,
                    "scene_number": 1,
                    "audio_url": "http://localhost:9000/litink-books/users/u1/audio/scene-1.mp3",
                    "duration": 3.0,
                }
            ],
            "narrator": [],
            "sound_effects": [],
            "background_music": [],
        },
        image_data={
            "scene_images": [
                {
                    "id": "img-1",
                    "scene_number": 1,
                    "shot_index": 0,
                    "image_url": "http://localhost:9000/litink-books/users/u1/images/scene-1.png",
                    "metadata": {
                        "provider_image_url": provider_image_url,
                        "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
                    },
                }
            ]
        },
        video_style="realistic",
        script_data={"script": "", "characters": []},
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1],
        selected_audio_ids=["ff624d48-0000-4000-8000-000000000000"],
    )

    assert result == [None]
    assert service.calls[0]["image_url"] == provider_image_url
    assert service.calls[0]["init_audio"] == provider_audio_url
    diagnostic_calls = [params for stmt, params in session.executed if "provider_attempts" in stmt]
    assert diagnostic_calls
    assert provider_audio_url in diagnostic_calls[0]["diagnostic"]
    assert provider_image_url in diagnostic_calls[0]["diagnostic"]
    assert '"provider_audio_url": null' not in diagnostic_calls[0]["diagnostic"]
    assert '"provider_image_url": null' not in diagnostic_calls[0]["diagnostic"]


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
async def test_kan86_localhost_media_config_error_is_persisted_before_provider_call(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)
    session = _RecordingSession()
    service = _ProviderFailureService()

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={"scene_images": [{"image_url": "http://localhost:9000/litink-dev/scene.png?secret=1"}]},
        video_style="realistic",
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1],
    )

    assert result == [None]
    assert service.calls == []
    diagnostic_calls = [params for stmt, params in session.executed if "provider_attempts" in stmt]
    assert diagnostic_calls, "configuration errors should be persisted to task_meta"
    assert "configuration_error" in diagnostic_calls[0]["diagnostic"]
    assert "Provider media URL is not externally reachable" in diagnostic_calls[0]["diagnostic"]
    assert "secret=1" not in diagnostic_calls[0]["diagnostic"]


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


def test_kan86_finalization_metadata_serializes_uuid_and_duration():
    segment_id = uuid.uuid4()
    payload = {
        "scene_videos": [
            {
                "id": segment_id,
                "scene_id": "scene_1",
                "scene_number": 1,
                "video_url": "https://storage.example.com/video.mp4",
                "duration": 5.05,
            }
        ],
        "statistics": {
            "total_scenes": 1,
            "videos_generated": 1,
            "total_duration": 5.05,
            "success_rate": 100.0,
        },
    }

    serialized = _json_dumps_safe(payload)
    decoded = json.loads(serialized)

    assert decoded["scene_videos"][0]["id"] == str(segment_id)
    assert decoded["scene_videos"][0]["video_url"] == "https://storage.example.com/video.mp4"
    assert decoded["statistics"]["total_duration"] == 5.05


def test_kan86_provider_cdn_url_preferred_over_localhost_minio_without_provider_base(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    canonical = "http://localhost:9000/litink-books/users/u1/images/scene.png"
    provider = "https://modelslab-cdn.example.com/scene.png"
    selected = select_provider_media_source(
        canonical,
        {
            "image_url": canonical,
            "meta": {
                "provider_image_url": provider,
                "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    assert selected == provider
    assert normalize_media_url_for_provider(selected) == provider


def test_kan86_stale_provider_cdn_url_falls_back_to_local_minio_config_error(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    canonical = "http://localhost:9000/litink-books/users/u1/images/scene.png"
    selected = select_provider_media_source(
        canonical,
        {
            "image_url": canonical,
            "metadata": {
                "original_cdn_url": "https://modelslab-cdn.example.com/stale.png",
                "provider_url_created_at": (
                    datetime.now(timezone.utc) - timedelta(days=14)
                ).isoformat(),
            },
        },
    )

    assert selected == canonical
    with pytest.raises(ProviderMediaUrlConfigurationError):
        normalize_media_url_for_provider(selected)


def test_kan86_raw_ip_provider_cdn_candidate_still_rejected_or_falls_back(monkeypatch):
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PUBLIC_URL", "http://72.62.97.111:9000")
    monkeypatch.setattr("app.tasks.video_tasks.settings.MODELSLAB_MEDIA_PUBLIC_URL", None)
    monkeypatch.setattr("app.tasks.video_tasks.settings.MINIO_PROVIDER_PUBLIC_URL", None)
    for env_name in (
        "MODELSLAB_MEDIA_PUBLIC_URL",
        "MINIO_PROVIDER_PUBLIC_URL",
        "PUBLIC_MINIO_URL",
        "MINIO_EXTERNAL_URL",
        "MEDIA_PUBLIC_URL",
        "PUBLIC_MEDIA_URL",
        "S3_PUBLIC_URL",
        "CDN_BASE_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)

    canonical = "http://72.62.97.111:9000/litink-books/users/u1/images/scene.png"
    selected = select_provider_media_source(
        canonical,
        {
            "image_url": canonical,
            "image_metadata": {
                "provider_image_url": "http://72.62.97.111:9000/provider/scene.png",
                "provider_url_created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    assert selected == canonical
    with pytest.raises(ProviderMediaUrlConfigurationError):
        normalize_media_url_for_provider(selected)


def test_kan87_generate_all_expands_scene_then_shot_order():
    pre_gen_scene_images = [
        {"id": "scene-1-shot-1", "scene_number": 1, "shot_index": 1, "image_url": "https://cdn/s1-1.png"},
        {"id": "scene-1-key", "scene_number": 1, "shot_index": 0, "image_url": "https://cdn/s1-0.png"},
        {"id": "scene-2-key", "scene_number": 2, "shot_index": 0, "image_url": "https://cdn/s2-0.png"},
    ]
    scene_image_map = {}
    for img in pre_gen_scene_images:
        scene_image_map.setdefault(int(img["scene_number"]), {})[int(img["shot_index"])] = img

    descriptions, scene_numbers, images = select_scene_assets_for_targets(
        target_scene_numbers=[1, 2],
        original_scene_descriptions=["Scene one", "Scene two"],
        scene_image_map=scene_image_map,
        pre_gen_scene_images=pre_gen_scene_images,
        pre_gen_character_images=[],
        selected_shots=[],
    )

    assert descriptions == ["Scene one", "Scene one", "Scene two"]
    assert scene_numbers == [1, 1, 2]
    assert [img["id"] for img in images] == ["scene-1-key", "scene-1-shot-1", "scene-2-key"]


@pytest.mark.asyncio
async def test_kan87_suggested_shot_uses_previous_upscaled_frame_and_scene_key_resets(monkeypatch):
    monkeypatch.setattr("app.core.services.storage.get_storage_service", lambda: _NoopStorage())
    frames = ["https://storage.example.com/frame-key.jpg", "https://storage.example.com/frame-suggested.jpg", "https://storage.example.com/frame-scene2.jpg"]
    monkeypatch.setattr("app.tasks.video_tasks.extract_last_frame", AsyncMock(side_effect=frames))
    monkeypatch.setattr("app.tasks.video_tasks.upscale_frame", AsyncMock(side_effect=lambda url, **kwargs: url.replace("frame", "upscaled")))
    session = _RecordingSession()
    service = _ProviderSuccessService()

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one", "Scene one suggested", "Scene two"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={"scene_images": [
            {"image_url": "https://cdn.example.com/scene1-key.png", "scene_number": 1, "shot_index": 0},
            {"image_url": "https://cdn.example.com/scene1-shot1.png", "scene_number": 1, "shot_index": 1},
            {"image_url": "https://cdn.example.com/scene2-key.png", "scene_number": 2, "shot_index": 0},
        ]},
        video_style="realistic",
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1, 1, 2],
    )

    assert [r["shot_index"] for r in result] == [0, 1, 0]
    assert service.calls[0]["image_url"] == "https://cdn.example.com/scene1-key.png"
    assert service.calls[1]["image_url"] == "https://storage.example.com/upscaled-key.jpg"
    assert service.calls[2]["image_url"] == "https://cdn.example.com/scene2-key.png"
    assert result[1]["frame_dependency"]["extracted_frame_url"] == "https://storage.example.com/frame-key.jpg"


@pytest.mark.asyncio
async def test_kan87_suggested_shot_fails_without_previous_frame_dependency(monkeypatch):
    monkeypatch.setattr("app.core.services.storage.get_storage_service", lambda: _NoopStorage())
    monkeypatch.setattr("app.tasks.video_tasks.extract_last_frame", AsyncMock(return_value=None))
    session = _RecordingSession()
    service = _ProviderSuccessService()

    result = await generate_scene_videos(
        modelslab_service=service,
        video_gen_id="11111111-1111-1111-1111-111111111111",
        scene_descriptions=["Scene one", "Scene one suggested"],
        audio_files={"characters": [], "narrator": [], "sound_effects": [], "background_music": []},
        image_data={"scene_images": [
            {"image_url": "https://cdn.example.com/scene1-key.png", "scene_number": 1, "shot_index": 0},
            {"image_url": "https://cdn.example.com/scene1-shot1.png", "scene_number": 1, "shot_index": 1},
        ]},
        video_style="realistic",
        user_id="22222222-2222-2222-2222-222222222222",
        session=session,
        scene_numbers=[1, 1],
    )

    assert result[0] is not None
    assert result[1] is None
    assert len(service.calls) == 1
