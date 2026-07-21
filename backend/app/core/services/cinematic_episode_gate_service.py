"""
Cinematic Episode Gate Service

Validates episode structure, tracks dialogue lines through the pipeline,
and manages sequence units for cinematic dialogue video generations.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
from datetime import datetime
import uuid


# Required sequence unit types in canonical order
REQUIRED_UNIT_TYPES = [
    "ident_title",
    "prologue",
    "dialogue_act",
    "climax_resolution",
    "closing_bookend",
    "end_title_credits",
]

# Valid line tracking stages in order
LINE_TRACKING_STAGES = [
    "character_assigned",
    "voice_assigned",
    "scene_assigned",
    "shot_assigned",
    "audio_generated",
    "lipsync_queued",
    "lipsync_complete",
    "placed",
]


class CinematicEpisodeGateService:
    """Service for cinematic episode gate validation and line tracking."""

    async def validate_episode_structure(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Validate that all required sequence unit types are present and ordered.

        Returns:
            {valid: bool, missing: [], out_of_order: [], duplicates: []}
        """
        query = text(
            """
            SELECT unit_type, unit_order
            FROM sequence_units
            WHERE video_generation_id = :vg_id
            ORDER BY unit_order
            """
        )
        result = await session.execute(query, {"vg_id": video_generation_id})
        rows = result.mappings().all()

        found_types = [row["unit_type"] for row in rows]
        found_set = set(found_types)
        required_set = set(REQUIRED_UNIT_TYPES)

        missing = list(required_set - found_set)
        extra = list(found_set - required_set)

        # Check for duplicates
        seen = set()
        duplicates = []
        for ut in found_types:
            if ut in seen:
                duplicates.append(ut)
            seen.add(ut)

        # Check ordering: for each required type that exists, verify its order
        # relative to the required order
        out_of_order = []
        type_to_order: Dict[str, int] = {}
        for row in rows:
            t = row["unit_type"]
            if t in type_to_order:
                # duplicate already tracked
                continue
            type_to_order[t] = row["unit_order"]

        for i, ut in enumerate(REQUIRED_UNIT_TYPES):
            if ut not in type_to_order:
                continue
            # Every required type before this one should have a lower unit_order
            for prev_ut in REQUIRED_UNIT_TYPES[:i]:
                if prev_ut in type_to_order and type_to_order[prev_ut] >= type_to_order[ut]:
                    if ut not in out_of_order:
                        out_of_order.append(ut)
                    break

        valid = (
            len(missing) == 0
            and len(out_of_order) == 0
            and len(duplicates) == 0
        )

        return {
            "valid": valid,
            "missing": missing,
            "out_of_order": out_of_order,
            "duplicates": duplicates,
            "extra_types": extra,
        }

    async def create_sequence_units(
        self,
        video_generation_id: str,
        units_data: List[Dict[str, Any]],
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Create sequence units for a video generation.

        Each item in units_data should have:
          - unit_type (str): one of REQUIRED_UNIT_TYPES
          - unit_order (int): ordering index
          - title (str, optional): display title
          - metadata (dict, optional): additional metadata
        """
        created = []
        for unit in units_data:
            unit_id = str(uuid.uuid4())
            insert_query = text(
                """
                INSERT INTO sequence_units (
                    id, video_generation_id, unit_type, unit_order,
                    title, metadata, created_at, updated_at
                ) VALUES (
                    :id, :vg_id, :unit_type, :unit_order,
                    :title, :metadata, :created_at, :updated_at
                )
                RETURNING *
                """
            )
            result = await session.execute(
                insert_query,
                {
                    "id": unit_id,
                    "vg_id": video_generation_id,
                    "unit_type": unit["unit_type"],
                    "unit_order": unit["unit_order"],
                    "title": unit.get("title"),
                    "metadata": json.dumps(unit.get("metadata", {})),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            )
            row = dict(result.mappings().first())
            if row.get("metadata") and isinstance(row["metadata"], str):
                row["metadata"] = json.loads(row["metadata"])
            created.append(row)

        await session.commit()
        return created

    async def get_sequence_units(
        self, video_generation_id: str, session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get all sequence units ordered by unit_order."""
        query = text(
            """
            SELECT * FROM sequence_units
            WHERE video_generation_id = :vg_id
            ORDER BY unit_order
            """
        )
        result = await session.execute(query, {"vg_id": video_generation_id})
        rows = []
        for row in result.mappings():
            d = dict(row)
            if d.get("metadata") and isinstance(d["metadata"], str):
                d["metadata"] = json.loads(d["metadata"])
            rows.append(d)
        return rows

    async def update_sequence_unit(
        self, unit_id: str, update_data: Dict[str, Any], session: AsyncSession
    ) -> Dict[str, Any]:
        """Update a sequence unit.

        Supports updating: unit_type, unit_order, title, metadata.
        """
        allowed_fields = {"unit_type", "unit_order", "title", "metadata"}
        sets = []
        params: Dict[str, Any] = {"unit_id": unit_id, "updated_at": datetime.utcnow()}

        for field, value in update_data.items():
            if field not in allowed_fields:
                continue
            if field == "metadata" and isinstance(value, (dict, list)):
                value = json.dumps(value)
            sets.append(f"{field} = :{field}")
            params[field] = value

        if not sets:
            raise ValueError("No valid fields to update")

        sets.append("updated_at = :updated_at")

        update_query = text(
            f"""
            UPDATE sequence_units
            SET {', '.join(sets)}
            WHERE id = :unit_id
            RETURNING *
            """
        )
        result = await session.execute(update_query, params)
        row = dict(result.mappings().first())
        if row.get("metadata") and isinstance(row["metadata"], str):
            row["metadata"] = json.loads(row["metadata"])
        await session.commit()
        return row

    async def track_line_through_pipeline(
        self,
        line_tracking_id: str,
        stage: str,
        data: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Update a line tracking record as it progresses through the pipeline.

        Stages: character_assigned → voice_assigned → scene_assigned → shot_assigned →
                audio_generated → lipsync_queued → lipsync_complete → placed
        """
        if stage not in LINE_TRACKING_STAGES:
            raise ValueError(
                f"Invalid stage '{stage}'. Must be one of: {LINE_TRACKING_STAGES}"
            )

        stage_index = LINE_TRACKING_STAGES.index(stage)

        update_query = text(
            """
            UPDATE line_tracking
            SET current_stage = :stage,
                stage_index = :stage_index,
                stage_data = :stage_data,
                updated_at = :updated_at
            WHERE id = :line_id
            RETURNING *
            """
        )
        result = await session.execute(
            update_query,
            {
                "line_id": line_tracking_id,
                "stage": stage,
                "stage_index": stage_index,
                "stage_data": json.dumps(data),
                "updated_at": datetime.utcnow(),
            },
        )
        row = dict(result.mappings().first())
        if not row:
            raise ValueError(f"Line tracking record {line_tracking_id} not found")
        if row.get("stage_data") and isinstance(row["stage_data"], str):
            row["stage_data"] = json.loads(row["stage_data"])
        await session.commit()
        return row

    async def get_line_tracking(
        self, sequence_unit_id: str, session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get all tracked lines for a sequence unit."""
        query = text(
            """
            SELECT * FROM line_tracking
            WHERE sequence_unit_id = :unit_id
            ORDER BY line_index
            """
        )
        result = await session.execute(query, {"unit_id": sequence_unit_id})
        rows = []
        for row in result.mappings():
            d = dict(row)
            if d.get("stage_data") and isinstance(d["stage_data"], str):
                d["stage_data"] = json.loads(d["stage_data"])
            rows.append(d)
        return rows

    async def get_full_line_tracking(
        self, video_generation_id: str, session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Get all tracked lines for a video generation, grouped by sequence unit."""
        query = text(
            """
            SELECT lt.*, su.unit_type, su.unit_order
            FROM line_tracking lt
            JOIN sequence_units su ON lt.sequence_unit_id = su.id
            WHERE su.video_generation_id = :vg_id
            ORDER BY su.unit_order, lt.line_index
            """
        )
        result = await session.execute(query, {"vg_id": video_generation_id})
        rows = []
        for row in result.mappings():
            d = dict(row)
            if d.get("stage_data") and isinstance(d["stage_data"], str):
                d["stage_data"] = json.loads(d["stage_data"])
            rows.append(d)
        return rows