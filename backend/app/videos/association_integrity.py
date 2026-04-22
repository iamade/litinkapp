from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCENE_SHOT_ID_PATTERN = re.compile(
    r"^scene-(?P<timestamp>\d+)-(?P<scene_index>\d+)(?:-(?P<shot_index>\d+))?(?:-(?P<script_id>.+))?$"
)


@dataclass(frozen=True)
class ShotSelection:
    scene_index: int
    shot_index: int
    script_id: Optional[str]

    @property
    def scene_number(self) -> int:
        return self.scene_index + 1


def parse_selected_shot_id(shot_id: Any) -> Optional[ShotSelection]:
    if not isinstance(shot_id, str):
        return None

    match = SCENE_SHOT_ID_PATTERN.match(shot_id.strip())
    if not match:
        return None

    try:
        scene_index = int(match.group("scene_index"))
        shot_index_raw = match.group("shot_index")
        shot_index = int(shot_index_raw) if shot_index_raw is not None else 0
    except (TypeError, ValueError):
        return None

    script_id = match.group("script_id")
    return ShotSelection(scene_index=scene_index, shot_index=shot_index, script_id=script_id)


def extract_shot_selections(
    selected_shot_ids: Optional[Sequence[Any]], expected_script_id: Optional[str] = None
) -> List[ShotSelection]:
    def _parse_with_expected_script(raw_id: str) -> Optional[ShotSelection]:
        if not expected_script_id:
            return None
        marker = f"-{expected_script_id}"
        if not raw_id.endswith(marker):
            return None

        prefix = raw_id[: -len(marker)]
        match = re.match(
            r"^scene-(?P<timestamp>\d+)-(?P<scene_index>\d+)(?:-(?P<shot_index>\d+))?$",
            prefix,
        )
        if not match:
            return None

        try:
            scene_index = int(match.group("scene_index"))
            shot_index_raw = match.group("shot_index")
            shot_index = int(shot_index_raw) if shot_index_raw is not None else 0
        except (TypeError, ValueError):
            return None

        return ShotSelection(
            scene_index=scene_index, shot_index=shot_index, script_id=expected_script_id
        )

    selections: List[ShotSelection] = []
    seen: set[Tuple[int, int]] = set()

    for raw_id in selected_shot_ids or []:
        parsed = None
        if isinstance(raw_id, str):
            parsed = _parse_with_expected_script(raw_id)
        if not parsed:
            parsed = parse_selected_shot_id(raw_id)
        if not parsed:
            continue
        if expected_script_id and parsed.script_id and parsed.script_id != expected_script_id:
            continue

        dedupe_key = (parsed.scene_index, parsed.shot_index)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        selections.append(parsed)

    return sorted(selections, key=lambda s: (s.scene_index, s.shot_index))


def extract_selected_scene_numbers(
    selected_shot_ids: Optional[Sequence[Any]], expected_script_id: Optional[str] = None
) -> List[int]:
    scene_numbers: List[int] = []
    seen: set[int] = set()

    for selection in extract_shot_selections(selected_shot_ids, expected_script_id):
        scene_number = selection.scene_number
        if scene_number not in seen:
            scene_numbers.append(scene_number)
            seen.add(scene_number)
    return scene_numbers


def parse_scene_id(scene_id: Any) -> Optional[int]:
    if isinstance(scene_id, str):
        match = re.match(r"^scene_(\d+)$", scene_id.strip())
        if match:
            return int(match.group(1))
    return None


def is_generation_excluded(task_meta: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(task_meta, dict):
        return False
    integrity = task_meta.get("association_integrity")
    return bool(isinstance(integrity, dict) and integrity.get("excluded") is True)


def is_audio_record_in_context(
    audio_record: Any, expected_script_id: Optional[str], allowed_scene_numbers: Optional[Iterable[int]] = None
) -> bool:
    if expected_script_id is not None:
        record_script_id = getattr(audio_record, "script_id", None)
        if record_script_id is None or str(record_script_id) != str(expected_script_id):
            return False

    if allowed_scene_numbers is None:
        return True

    allowed_set = {int(n) for n in allowed_scene_numbers}
    if not allowed_set:
        return True

    # KAN-165 integration fix: Try scene_id first (e.g. "scene_2" → 2),
    # since sequence_order is just a sequential index within audio type, NOT the scene number.
    scene_number = parse_scene_id(getattr(audio_record, "scene_id", None))
    if scene_number is None:
        scene_number = getattr(audio_record, "sequence_order", None)

    try:
        if scene_number is None:
            return False
        return int(scene_number) in allowed_set
    except (TypeError, ValueError):
        return False


def dedupe_scene_videos(scene_videos: Sequence[Optional[Dict[str, Any]]]) -> List[Optional[Dict[str, Any]]]:
    deduped: List[Optional[Dict[str, Any]]] = []
    seen: set[Tuple[Any, Any, Any, Any, Any]] = set()

    for video in scene_videos:
        if video is None:
            deduped.append(video)
            continue

        scene_id = video.get("scene_id")
        scene_sequence = video.get("scene_sequence")
        source_image = video.get("source_image")
        video_url = video.get("video_url")
        method = video.get("method")

        key = (scene_id, scene_sequence, source_image, video_url, method)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(video)

    return deduped


def resolve_scene_identity(loop_index: int, scene_numbers: Optional[Sequence[int]] = None) -> Tuple[int, str]:
    if scene_numbers and loop_index < len(scene_numbers):
        scene_num = int(scene_numbers[loop_index])
    else:
        scene_num = loop_index + 1
    return scene_num, f"scene_{scene_num}"
