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
