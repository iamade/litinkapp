"""
Continuity Service

Manages continuity references (characters, world elements, props, locations)
and performs QA checks for adjacent shots and track consistency across sequence units.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import uuid


# Valid continuity reference types
VALID_REF_TYPES = {"character", "world_element", "prop", "location"}


class ContinuityService:
    """Service for continuity reference management and QA checks."""

    async def create_reference(
        self,
        video_generation_id: str,
        ref_type: str,
        ref_id: str,
        ref_data: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Create a continuity reference for a character, world element, prop, or location.

        Args:
            video_generation_id: The video generation this reference belongs to.
            ref_type: One of 'character', 'world_element', 'prop', 'location'.
            ref_id: The ID of the referenced entity (e.g. character ID).
            ref_data: Dictionary with reference details (name, description, visual attributes, etc.)
        """
        if ref_type not in VALID_REF_TYPES:
            raise ValueError(
                f"Invalid ref_type '{ref_type}'. Must be one of: {VALID_REF_TYPES}"
            )

        reference_id = str(uuid.uuid4())
        insert_query = text(
            """
            INSERT INTO continuity_references (
                id, video_generation_id, ref_type, ref_id, ref_data,
                adjacent_shot_qa, created_at, updated_at
            ) VALUES (
                :id, :vg_id, :ref_type, :ref_id, :ref_data,
                NULL, :created_at, :updated_at
            )
            RETURNING *
            """
        )
        result = await session.execute(
            insert_query,
            {
                "id": reference_id,
                "vg_id": video_generation_id,
                "ref_type": ref_type,
                "ref_id": ref_id,
                "ref_data": json.dumps(ref_data),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )
        row = dict(result.mappings().first())
        if row.get("ref_data") and isinstance(row["ref_data"], str):
            row["ref_data"] = json.loads(row["ref_data"])
        await session.commit()
        return row

    async def get_references(
        self,
        video_generation_id: str,
        ref_type: Optional[str] = None,
        session: AsyncSession = None,
    ) -> List[Dict[str, Any]]:
        """Get continuity references, optionally filtered by type."""
        if ref_type:
            query = text(
                """
                SELECT * FROM continuity_references
                WHERE video_generation_id = :vg_id AND ref_type = :ref_type
                ORDER BY created_at
                """
            )
            result = await session.execute(
                query, {"vg_id": video_generation_id, "ref_type": ref_type}
            )
        else:
            query = text(
                """
                SELECT * FROM continuity_references
                WHERE video_generation_id = :vg_id
                ORDER BY ref_type, created_at
                """
            )
            result = await session.execute(query, {"vg_id": video_generation_id})

        rows = []
        for row in result.mappings():
            d = dict(row)
            if d.get("ref_data") and isinstance(d["ref_data"], str):
                d["ref_data"] = json.loads(d["ref_data"])
            if d.get("adjacent_shot_qa") and isinstance(d["adjacent_shot_qa"], str):
                d["adjacent_shot_qa"] = json.loads(d["adjacent_shot_qa"])
            rows.append(d)
        return rows

    async def update_reference(
        self, reference_id: str, update_data: Dict[str, Any], session: AsyncSession
    ) -> Dict[str, Any]:
        """Update a continuity reference."""
        allowed_fields = {"ref_type", "ref_id", "ref_data", "adjacent_shot_qa"}
        sets = []
        params: Dict[str, Any] = {"reference_id": reference_id, "updated_at": datetime.utcnow()}

        for field, value in update_data.items():
            if field not in allowed_fields:
                continue
            if field in ("ref_data", "adjacent_shot_qa") and isinstance(value, (dict, list)):
                value = json.dumps(value)
            sets.append(f"{field} = :{field}")
            params[field] = value

        if not sets:
            raise ValueError("No valid fields to update")

        sets.append("updated_at = :updated_at")

        update_query = text(
            f"""
            UPDATE continuity_references
            SET {', '.join(sets)}
            WHERE id = :reference_id
            RETURNING *
            """
        )
        result = await session.execute(update_query, params)
        row = dict(result.mappings().first())
        if not row:
            raise ValueError(f"Continuity reference {reference_id} not found")
        for field in ("ref_data", "adjacent_shot_qa"):
            if row.get(field) and isinstance(row[field], str):
                row[field] = json.loads(row[field])
        await session.commit()
        return row

    async def run_adjacent_shot_qa(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Check continuity between adjacent shots.

        For each pair of adjacent video_segments, check:
          - Character appearance consistency
          - Location/setting consistency
          - Prop consistency
          - Lighting/mood consistency (from metadata)

        Store results in continuity_references.adjacent_shot_qa JSONB.
        Return {pairs_checked, inconsistencies_found, details}
        """
        # Fetch all video segments ordered by sequence
        seg_query = text(
            """
            SELECT * FROM video_segments
            WHERE video_generation_id = :vg_id
            ORDER BY sequence_index
            """
        )
        result = await session.execute(seg_query, {"vg_id": video_generation_id})
        segments = [dict(row) for row in result.mappings()]

        if len(segments) < 2:
            return {
                "pairs_checked": 0,
                "inconsistencies_found": 0,
                "details": [],
                "message": "Not enough segments for adjacent-shot QA.",
            }

        # Fetch continuity references for context
        ref_query = text(
            """
            SELECT * FROM continuity_references
            WHERE video_generation_id = :vg_id
            """
        )
        ref_result = await session.execute(ref_query, {"vg_id": video_generation_id})
        references = [dict(row) for row in ref_result.mappings()]

        # Build reference lookup maps
        char_refs = {}
        location_refs = {}
        prop_refs = {}
        for ref in references:
            ref_data = ref.get("ref_data")
            if isinstance(ref_data, str):
                try:
                    ref_data = json.loads(ref_data)
                except (json.JSONDecodeError, TypeError):
                    ref_data = {}
            if ref["ref_type"] == "character":
                char_refs[ref["ref_id"]] = ref_data or {}
            elif ref["ref_type"] == "location":
                location_refs[ref["ref_id"]] = ref_data or {}
            elif ref["ref_type"] == "prop":
                prop_refs[ref["ref_id"]] = ref_data or {}

        pairs_checked = 0
        inconsistencies_found = 0
        details = []

        for i in range(len(segments) - 1):
            seg_a = segments[i]
            seg_b = segments[i + 1]
            pairs_checked += 1

            pair_issues = []

            # Parse metadata
            meta_a = seg_a.get("metadata")
            meta_b = seg_b.get("metadata")
            if isinstance(meta_a, str):
                try:
                    meta_a = json.loads(meta_a)
                except (json.JSONDecodeError, TypeError):
                    meta_a = {}
            if isinstance(meta_b, str):
                try:
                    meta_b = json.loads(meta_b)
                except (json.JSONDecodeError, TypeError):
                    meta_b = {}

            # Check character consistency
            chars_a = set(meta_a.get("characters", []))
            chars_b = set(meta_b.get("characters", []))
            if chars_a and chars_b:
                added = chars_b - chars_a
                removed = chars_a - chars_b
                if added or removed:
                    # Only flag as inconsistency if there's no scene transition marker
                    if not meta_b.get("scene_transition", False):
                        pair_issues.append(
                            {
                                "type": "character",
                                "message": "Character set changed between adjacent shots",
                                "added": list(added),
                                "removed": list(removed),
                            }
                        )

            # Check location/setting consistency
            loc_a = meta_a.get("location") or meta_a.get("setting")
            loc_b = meta_b.get("location") or meta_b.get("setting")
            if loc_a and loc_b and loc_a != loc_b:
                if not meta_b.get("scene_transition", False):
                    pair_issues.append(
                        {
                            "type": "location",
                            "message": "Location/setting changed between adjacent shots",
                            "from": loc_a,
                            "to": loc_b,
                        }
                    )

            # Check prop consistency
            props_a = set(meta_a.get("props", []))
            props_b = set(meta_b.get("props", []))
            if props_a and props_b:
                added_props = props_b - props_a
                removed_props = props_a - props_b
                if (added_props or removed_props) and not meta_b.get("scene_transition", False):
                    pair_issues.append(
                        {
                            "type": "prop",
                            "message": "Prop set changed between adjacent shots",
                            "added": list(added_props),
                            "removed": list(removed_props),
                        }
                    )

            # Check lighting/mood consistency
            mood_a = meta_a.get("lighting") or meta_a.get("mood")
            mood_b = meta_b.get("lighting") or meta_b.get("mood")
            if mood_a and mood_b and mood_a != mood_b:
                # Lighting changes are more common, only flag if dramatic
                if not meta_b.get("scene_transition", False):
                    pair_issues.append(
                        {
                            "type": "lighting_mood",
                            "message": "Lighting/mood changed between adjacent shots",
                            "from": mood_a,
                            "to": mood_b,
                        }
                    )

            if pair_issues:
                inconsistencies_found += 1
                details.append(
                    {
                        "pair_index": i,
                        "segment_a_id": str(seg_a["id"]),
                        "segment_b_id": str(seg_b["id"]),
                        "sequence_index_a": seg_a.get("sequence_index"),
                        "sequence_index_b": seg_b.get("sequence_index"),
                        "issues": pair_issues,
                    }
                )

        # Store results in continuity_references adjacent_shot_qa JSONB
        qa_result = {
            "pairs_checked": pairs_checked,
            "inconsistencies_found": inconsistencies_found,
            "details": details,
            "checked_at": datetime.utcnow().isoformat(),
        }

        # Update all continuity references for this video generation with the QA result
        if references:
            update_query = text(
                """
                UPDATE continuity_references
                SET adjacent_shot_qa = :qa_result,
                    updated_at = :updated_at
                WHERE video_generation_id = :vg_id
                """
            )
            await session.execute(
                update_query,
                {
                    "qa_result": json.dumps(qa_result),
                    "updated_at": datetime.utcnow(),
                    "vg_id": video_generation_id,
                },
            )

        await session.commit()
        return qa_result

    async def validate_track_consistency(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Validate that narrator, dialogue, music, and ambience tracks are consistent across sequence units.

        - Check voice_id consistency for narrator across all units
        - Check character voice consistency across units
        - Check music style/track consistency
        - Check ambience consistency
        - Return {consistent: bool, inconsistencies: []}
        """
        # Fetch all sequence units with their metadata
        unit_query = text(
            """
            SELECT * FROM sequence_units
            WHERE video_generation_id = :vg_id
            ORDER BY unit_order
            """
        )
        result = await session.execute(unit_query, {"vg_id": video_generation_id})
        units = [dict(row) for row in result.mappings()]

        if not units:
            return {
                "consistent": True,
                "inconsistencies": [],
                "message": "No sequence units found for this video generation.",
            }

        inconsistencies = []

        # Track expected values for each track type
        narrator_voice_id: Optional[str] = None
        character_voice_map: Dict[str, str] = {}  # character_name → voice_id
        music_style: Optional[str] = None
        ambience: Optional[str] = None

        for unit in units:
            metadata = unit.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            if not metadata:
                metadata = {}

            unit_label = f"unit_{unit.get('unit_order')} ({unit.get('unit_type', 'unknown')})"

            # Check narrator voice_id consistency
            tracks = metadata.get("tracks", {})
            narrator_track = tracks.get("narrator", {})
            narrator_vid = narrator_track.get("voice_id")
            if narrator_vid:
                if narrator_voice_id is None:
                    narrator_voice_id = narrator_vid
                elif narrator_vid != narrator_voice_id:
                    inconsistencies.append(
                        {
                            "type": "narrator_voice",
                            "unit": unit_label,
                            "expected": narrator_voice_id,
                            "found": narrator_vid,
                            "message": "Narrator voice_id differs across sequence units",
                        }
                    )

            # Check character voice consistency
            dialogue_track = tracks.get("dialogue", {})
            character_voices = dialogue_track.get("character_voices", {})
            if isinstance(character_voices, dict):
                for char_name, voice_id in character_voices.items():
                    if char_name in character_voice_map:
                        if voice_id != character_voice_map[char_name]:
                            inconsistencies.append(
                                {
                                    "type": "character_voice",
                                    "unit": unit_label,
                                    "character": char_name,
                                    "expected": character_voice_map[char_name],
                                    "found": voice_id,
                                    "message": f"Character '{char_name}' voice_id differs across sequence units",
                                }
                            )
                    else:
                        character_voice_map[char_name] = voice_id

            # Check music style/track consistency
            music_track = tracks.get("music", {})
            unit_music = music_track.get("style") or music_track.get("track_id")
            if unit_music:
                if music_style is None:
                    music_style = unit_music
                elif unit_music != music_style:
                    inconsistencies.append(
                        {
                            "type": "music",
                            "unit": unit_label,
                            "expected": music_style,
                            "found": unit_music,
                            "message": "Music style/track differs across sequence units",
                        }
                    )

            # Check ambience consistency
            ambience_track = tracks.get("ambience", {})
            unit_ambience = ambience_track.get("type") or ambience_track.get("track_id")
            if unit_ambience:
                if ambience is None:
                    ambience = unit_ambience
                elif unit_ambience != ambience:
                    inconsistencies.append(
                        {
                            "type": "ambience",
                            "unit": unit_label,
                            "expected": ambience,
                            "found": unit_ambience,
                            "message": "Ambience differs across sequence units",
                        }
                    )

        return {
            "consistent": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies,
            "units_checked": len(units),
        }