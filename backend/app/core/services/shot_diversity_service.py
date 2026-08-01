"""
Shot Diversity Service

Analyzes video segments for duplicate and near-duplicate shots,
supports intentional motif overrides, and generates diversity reports.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
import hashlib
from datetime import datetime
import uuid


class ShotDiversityService:
    """Service for analyzing shot diversity and detecting duplicates."""

    def _compute_shot_hash(self, scene_description: str, image_data: Any) -> str:
        """Compute a proxy perceptual hash from scene description and image data.

        Uses a normalized scene description + image metadata as a fingerprint.
        In a production system this would use actual perceptual image hashing (pHash),
        but here we use text-based fingerprinting as a proxy.
        """
        # Normalize scene description: lowercase, strip whitespace, remove punctuation
        normalized = scene_description.lower().strip()
        # Remove common punctuation
        for ch in ".,!?;:\"'()[]{}":
            normalized = normalized.replace(ch, "")
        normalized = " ".join(normalized.split())

        # Include image data if it's a dict (metadata) — stringify and normalize
        image_str = ""
        if image_data:
            if isinstance(image_data, dict):
                image_str = json.dumps(image_data, sort_keys=True).lower()
            elif isinstance(image_data, str):
                image_str = image_data.lower()

        combined = f"{normalized}|{image_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _hamming_distance(self, hash_a: str, hash_b: str) -> int:
        """Compute Hamming distance between two hex hashes (proxy for perceptual distance)."""
        # Convert hex to binary and count differing bits
        try:
            int_a = int(hash_a, 16)
            int_b = int(hash_b, 16)
            return bin(int_a ^ int_b).count("1")
        except (ValueError, TypeError):
            return 128  # max distance

    async def analyze_shots(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Analyze all shots/segments for duplicates and near-duplicates.

        - Fetch all video_segments for the video_generation
        - For each segment, compute a perceptual hash (proxy: scene_description + image_data)
        - Compare all pairs for exact and near-duplicate detection
        - Allow intentional_motif overrides (flagged in metadata)
        - Store results in shot_diversity_reports table
        - Return summary {total, duplicates, near_duplicates, unique, motifs}
        """
        # Fetch all video segments
        query = text(
            """
            SELECT * FROM video_segments
            WHERE video_generation_id = :vg_id
            ORDER BY sequence_index
            """
        )
        result = await session.execute(query, {"vg_id": video_generation_id})
        segments = [dict(row) for row in result.mappings()]

        if not segments:
            return {
                "total": 0,
                "duplicates": 0,
                "near_duplicates": 0,
                "unique": 0,
                "motifs": 0,
                "details": [],
            }

        # Compute hashes for all segments
        shot_hashes: List[Dict[str, Any]] = []
        for seg in segments:
            scene_desc = seg.get("scene_description") or seg.get("prompt") or ""
            image_data = seg.get("image_data") or seg.get("image_metadata") or {}
            shot_hash = self._compute_shot_hash(scene_desc, image_data)
            is_motif = False
            metadata = seg.get("metadata")
            if metadata:
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                is_motif = metadata.get("intentional_motif", False)

            shot_hashes.append(
                {
                    "segment_id": str(seg["id"]),
                    "hash": shot_hash,
                    "is_motif": is_motif,
                    "scene_description": scene_desc,
                    "sequence_index": seg.get("sequence_index"),
                }
            )

        # Compare all pairs
        duplicates = []
        near_duplicates = []
        unique_shots = set()
        duplicate_ids = set()
        near_duplicate_ids = set()
        motif_ids = set()

        for i, shot_a in enumerate(shot_hashes):
            for j, shot_b in enumerate(shot_hashes):
                if i >= j:
                    continue
                distance = self._hamming_distance(shot_a["hash"], shot_b["hash"])
                if distance == 0:
                    # Exact duplicate
                    if shot_a["is_motif"] or shot_b["is_motif"]:
                        motif_ids.add(shot_a["segment_id"])
                        motif_ids.add(shot_b["segment_id"])
                    else:
                        duplicate_ids.add(shot_b["segment_id"])
                        duplicates.append(
                            {
                                "shot_a": shot_a["segment_id"],
                                "shot_b": shot_b["segment_id"],
                                "type": "exact",
                            }
                        )
                elif distance <= 4:
                    # Near duplicate (threshold for proxy hash)
                    if shot_a["is_motif"] or shot_b["is_motif"]:
                        motif_ids.add(shot_a["segment_id"])
                        motif_ids.add(shot_b["segment_id"])
                    else:
                        near_duplicate_ids.add(shot_b["segment_id"])
                        near_duplicates.append(
                            {
                                "shot_a": shot_a["segment_id"],
                                "shot_b": shot_b["segment_id"],
                                "type": "near",
                                "distance": distance,
                            }
                        )

        # Unique = total - duplicates - near_duplicates (not counting motifs)
        flagged_ids = duplicate_ids | near_duplicate_ids | motif_ids
        for shot in shot_hashes:
            if shot["segment_id"] not in flagged_ids:
                unique_shots.add(shot["segment_id"])

        summary = {
            "total": len(segments),
            "duplicates": len(duplicates),
            "near_duplicates": len(near_duplicates),
            "unique": len(unique_shots),
            "motifs": len(motif_ids),
            "duplicate_details": duplicates,
            "near_duplicate_details": near_duplicates,
            "motif_ids": list(motif_ids),
            "unique_ids": list(unique_shots),
        }

        # Store report in shot_diversity_reports table
        report_id = str(uuid.uuid4())
        insert_query = text(
            """
            INSERT INTO shot_diversity_reports (
                id, video_generation_id, total_shots, duplicate_count,
                near_duplicate_count, unique_count, intentional_motif_count,
                report_data, status, created_at, updated_at
            ) VALUES (
                :id, :vg_id, :total, :duplicates,
                :near_duplicates, :unique, :motifs,
                :report_data, 'completed', :created_at, :updated_at
            )
            RETURNING *
            """
        )
        result = await session.execute(
            insert_query,
            {
                "id": report_id,
                "vg_id": video_generation_id,
                "total": summary["total"],
                "duplicates": summary["duplicates"],
                "near_duplicates": summary["near_duplicates"],
                "unique": summary["unique"],
                "motifs": summary["motifs"],
                "report_data": json.dumps(summary),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
        )
        report_row = dict(result.mappings().first())
        await session.commit()
        return {
            "report_id": report_id,
            **summary,
        }

    async def get_report(
        self, video_generation_id: str, session: AsyncSession
    ) -> Dict[str, Any]:
        """Get the latest shot diversity report."""
        query = text(
            """
            SELECT * FROM shot_diversity_reports
            WHERE video_generation_id = :vg_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = await session.execute(query, {"vg_id": video_generation_id})
        row = result.mappings().first()
        if not row:
            return {
                "found": False,
                "message": "No shot diversity report found for this video generation.",
            }

        report = dict(row)
        data = report.get("report_data") or {}
        if isinstance(data, str):
            data = json.loads(data)
        report.update(data)
        report["found"] = True
        return report

    async def mark_intentional_motif(
        self,
        report_id: str,
        shot_id: str,
        reason: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Mark a shot as an intentional motif (overrides duplicate flag)."""
        # Fetch the existing report
        query = text(
            """
            SELECT * FROM shot_diversity_reports
            WHERE id = :report_id
            """
        )
        result = await session.execute(query, {"report_id": report_id})
        row = result.mappings().first()
        if not row:
            raise ValueError(f"Shot diversity report {report_id} not found")

        report = dict(row)
        summary = report.get("report_data") or {}
        if isinstance(summary, str):
            summary = json.loads(summary)

        # Add the shot to motif_ids
        motif_ids = set(summary.get("motif_ids", []))
        motif_ids.add(shot_id)

        # Remove from duplicate/near_duplicate ids
        dup_details = summary.get("duplicate_details", [])
        near_dup_details = summary.get("near_duplicate_details", [])

        # Filter out pairs that involve the motif shot
        dup_details = [
            d
            for d in dup_details
            if d.get("shot_a") != shot_id and d.get("shot_b") != shot_id
        ]
        near_dup_details = [
            d
            for d in near_dup_details
            if d.get("shot_a") != shot_id and d.get("shot_b") != shot_id
        ]

        # Update summary
        summary["motif_ids"] = list(motif_ids)
        summary["motifs"] = len(motif_ids)
        summary["duplicates"] = len(dup_details)
        summary["near_duplicates"] = len(near_dup_details)
        summary["duplicate_details"] = dup_details
        summary["near_duplicate_details"] = near_dup_details
        summary.setdefault("motif_reasons", {})[shot_id] = reason

        # Also update the video_segment metadata to flag it as intentional motif
        seg_update = text(
            """
            UPDATE video_segments
            SET metadata = COALESCE(metadata, '{}'::jsonb) || '{"intentional_motif": true, "motif_reason": :reason}'::jsonb
            WHERE id = :shot_id
            """
        )
        await session.execute(seg_update, {"shot_id": shot_id, "reason": reason})

        # Update the report
        update_query = text(
            """
            UPDATE shot_diversity_reports
            SET report_data = :summary,
                duplicate_count = :duplicates,
                near_duplicate_count = :near_duplicates,
                intentional_motif_count = :motifs,
                updated_at = :updated_at
            WHERE id = :report_id
            RETURNING *
            """
        )
        result = await session.execute(
            update_query,
            {
                "report_id": report_id,
                "summary": json.dumps(summary),
                "duplicates": summary["duplicates"],
                "near_duplicates": summary["near_duplicates"],
                "motifs": summary["motifs"],
                "updated_at": datetime.utcnow(),
            },
        )
        updated = dict(result.mappings().first())
        if updated.get("report_data") and isinstance(updated["report_data"], str):
            updated["report_data"] = json.loads(updated["report_data"])

        await session.commit()
        return updated
