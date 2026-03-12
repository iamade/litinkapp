import uuid
from types import SimpleNamespace

from app.videos.association_integrity import (
    dedupe_scene_videos,
    extract_shot_selections,
    is_audio_record_in_context,
    resolve_scene_identity,
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
