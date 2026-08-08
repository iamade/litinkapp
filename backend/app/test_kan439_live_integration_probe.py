"""
KAN-439: Live Postgres Integration Probe

Verifies that ProductionBible, VoiceCasting, and DialogueManifest tables
in the actual Postgres database have column shapes matching the ORM model
definitions, and that full ORM reads (model_dump) work without errors.

Run:
    cd /opt/openclaw/repos/litinkapp && python3 -m pytest backend/app/test_kan439_live_integration_probe.py -v

Requires: DATABASE_URL pointing at the live Postgres instance.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Set, Tuple

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.videos.models import (
    ProductionBible,
    VoiceCasting,
    DialogueManifest,
)
from app.core.database import async_session


def _orm_columns(model_cls) -> Set[str]:
    return set(model_cls.__table__.columns.keys())


async def _raw_columns(session: AsyncSession, table_name: str) -> List[Tuple[str, str]]:
    result = await session.execute(
        text(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :tbl
            ORDER BY ordinal_position
            """
        ),
        {"tbl": table_name},
    )
    return [(row[0], row[1]) for row in result.fetchall()]


async def _raw_indexes(session: AsyncSession, table_name: str) -> List[str]:
    result = await session.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE tablename = :tbl ORDER BY indexname"
        ),
        {"tbl": table_name},
    )
    return [row[0] for row in result.fetchall()]


def _print_mismatch_report(
    orm_cols: Set[str],
    db_cols: Set[str],
    db_col_types: Dict[str, str],
) -> bool:
    passed = True
    phantom = orm_cols - db_cols
    orphaned = db_cols - orm_cols

    if phantom:
        passed = False
        print(f"  ❌ PHANTOM columns (ORM has, DB missing): {sorted(phantom)}")
    else:
        print("  ✅ No phantom columns")

    if orphaned:
        print(f"  ⚠️  ORPHANED columns (DB has, ORM missing): {sorted(orphaned)}")
    else:
        print("  ✅ No orphaned columns")

    return passed


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_session():
    session = async_session()
    try:
        yield session
    finally:
        await session.close()


# ── Production Bible ──


class TestProductionBibleShape:
    @pytest.mark.asyncio
    async def test_production_bibles_columns(self, db_session: AsyncSession):
        print("\n=== production_bibles: ORM vs DB column audit ===")
        orm_cols = _orm_columns(ProductionBible)
        db_raw = await _raw_columns(db_session, "production_bibles")
        db_cols = {row[0] for row in db_raw}
        db_types = {row[0]: row[1] for row in db_raw}

        print(f"  ORM columns ({len(orm_cols)}): {sorted(orm_cols)}")
        print(f"  DB columns  ({len(db_cols)}): {sorted(db_cols)}")

        passed = _print_mismatch_report(orm_cols, db_cols, db_types)
        assert passed, "Column mismatch in production_bibles"

    @pytest.mark.asyncio
    async def test_production_bibles_indexes(self, db_session: AsyncSession):
        idx = await _raw_indexes(db_session, "production_bibles")
        print(f"\n=== production_bibles indexes ===\n  {idx}")
        assert any("project_id" in i for i in idx), "Missing project_id index"

    @pytest.mark.asyncio
    async def test_production_bibles_model_dump(self, db_session: AsyncSession):
        result = await db_session.execute(
            text("SELECT * FROM production_bibles LIMIT 1")
        )
        if result.fetchone() is None:
            pytest.skip("production_bibles table is empty")

        from sqlmodel import select

        stmt = select(ProductionBible).limit(1)
        orm_result = await db_session.execute(stmt)
        bible = orm_result.scalars().first()

        dumped = bible.model_dump()
        print(f"\n=== production_bibles model_dump (1 row) ===")
        for k, v in sorted(dumped.items()):
            print(f"  {k}: {type(v).__name__} = {repr(v)[:80]}")
        assert "id" in dumped
        assert "project_id" in dumped


# ── Voice Casting ──


class TestVoiceCastingShape:
    @pytest.mark.asyncio
    async def test_voice_castings_columns(self, db_session: AsyncSession):
        print("\n=== voice_castings: ORM vs DB column audit ===")
        orm_cols = _orm_columns(VoiceCasting)
        db_raw = await _raw_columns(db_session, "voice_castings")
        db_cols = {row[0] for row in db_raw}
        db_types = {row[0]: row[1] for row in db_raw}

        print(f"  ORM columns ({len(orm_cols)}): {sorted(orm_cols)}")
        print(f"  DB columns  ({len(db_cols)}): {sorted(db_cols)}")

        passed = _print_mismatch_report(orm_cols, db_cols, db_types)
        assert passed, "Column mismatch in voice_castings"

    @pytest.mark.asyncio
    async def test_voice_castings_unique_constraint(self, db_session: AsyncSession):
        idx = await _raw_indexes(db_session, "voice_castings")
        print(f"\n=== voice_castings indexes ===\n  {idx}")
        assert any(
            "uq_voice_casting_project_character" in i for i in idx
        ), "Missing unique constraint"

    @pytest.mark.asyncio
    async def test_voice_castings_model_dump(self, db_session: AsyncSession):
        result = await db_session.execute(
            text("SELECT * FROM voice_castings LIMIT 1")
        )
        if result.fetchone() is None:
            pytest.skip("voice_castings table is empty")

        from sqlmodel import select

        stmt = select(VoiceCasting).limit(1)
        orm_result = await db_session.execute(stmt)
        casting = orm_result.scalars().first()

        dumped = casting.model_dump()
        print(f"\n=== voice_castings model_dump (1 row) ===")
        for k, v in sorted(dumped.items()):
            print(f"  {k}: {type(v).__name__} = {repr(v)[:80]}")
        assert dumped is not None


# ── Dialogue Manifest ──


class TestDialogueManifestShape:
    @pytest.mark.asyncio
    async def test_dialogue_manifests_columns(self, db_session: AsyncSession):
        print("\n=== dialogue_manifests: ORM vs DB column audit ===")
        orm_cols = _orm_columns(DialogueManifest)
        db_raw = await _raw_columns(db_session, "dialogue_manifests")
        db_cols = {row[0] for row in db_raw}
        db_types = {row[0]: row[1] for row in db_raw}

        print(f"  ORM columns ({len(orm_cols)}): {sorted(orm_cols)}")
        print(f"  DB columns  ({len(db_cols)}): {sorted(db_cols)}")

        passed = _print_mismatch_report(orm_cols, db_cols, db_types)
        assert passed, "Column mismatch in dialogue_manifests"

    @pytest.mark.asyncio
    async def test_dialogue_manifests_indexes(self, db_session: AsyncSession):
        idx = await _raw_indexes(db_session, "dialogue_manifests")
        print(f"\n=== dialogue_manifests indexes ===\n  {idx}")
        assert any("content_hash" in i for i in idx), "Missing content_hash index"
        assert any("project_id" in i for i in idx), "Missing project_id index"

    @pytest.mark.asyncio
    async def test_dialogue_manifests_model_dump(self, db_session: AsyncSession):
        result = await db_session.execute(
            text("SELECT * FROM dialogue_manifests LIMIT 1")
        )
        if result.fetchone() is None:
            pytest.skip("dialogue_manifests table is empty")

        from sqlmodel import select

        stmt = select(DialogueManifest).limit(1)
        orm_result = await db_session.execute(stmt)
        manifest = orm_result.scalars().first()

        dumped = manifest.model_dump()
        print(f"\n=== dialogue_manifests model_dump (1 row) ===")
        for k, v in sorted(dumped.items()):
            print(f"  {k}: {type(v).__name__} = {repr(v)[:80]}")
        assert dumped is not None


# ── FK Resolution ──


class TestForeignKeyResolution:
    @pytest.mark.asyncio
    async def test_line_tracking_fk(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT lt.id, lt.sequence_unit_id, su.id AS su_id "
                "FROM line_tracking lt "
                "JOIN sequence_units su ON lt.sequence_unit_id = su.id "
                "LIMIT 1"
            )
        )
        row = result.fetchone()
        if row is None:
            pytest.skip("No line_tracking rows with FK to sequence_units")
        assert row.su_id is not None
        print(f"\n✅ line_tracking → sequence_units FK resolves: {row.id} → {row.su_id}")

    @pytest.mark.asyncio
    async def test_continuity_references_fk(self, db_session: AsyncSession):
        result = await db_session.execute(
            text(
                "SELECT cr.id, cr.video_generation_id, vg.id AS vg_id "
                "FROM continuity_references cr "
                "JOIN video_generations vg ON cr.video_generation_id = vg.id "
                "LIMIT 1"
            )
        )
        row = result.fetchone()
        if row is None:
            pytest.skip("No continuity_references rows with FK to video_generations")
        assert row.vg_id is not None
        print(
            f"\n✅ continuity_references → video_generations FK resolves: {row.id} → {row.vg_id}"
        )

    @pytest.mark.asyncio
    async def test_sequence_units_queryable(self, db_session: AsyncSession):
        result = await db_session.execute(text("SELECT COUNT(*) FROM sequence_units"))
        count = result.scalar()
        print(f"\n✅ sequence_units table queryable: {count} rows")


# ── Summary ──


class TestSummaryReport:
    @pytest.mark.asyncio
    async def test_summary(self, db_session: AsyncSession):
        tables = [
            ("production_bibles", ProductionBible),
            ("voice_castings", VoiceCasting),
            ("dialogue_manifests", DialogueManifest),
        ]

        print("\n" + "=" * 60)
        print("KAN-439 Integration Probe Summary")
        print("=" * 60)

        all_passed = True
        for table_name, model_cls in tables:
            orm_cols = _orm_columns(model_cls)
            db_raw = await _raw_columns(db_session, table_name)
            db_cols = {row[0] for row in db_raw}

            phantom = orm_cols - db_cols
            orphaned = db_cols - orm_cols

            status = "❌ FAIL" if (phantom or orphaned) else "✅ PASS"
            if phantom or orphaned:
                all_passed = False

            count_result = await db_session.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            row_count = count_result.scalar()

            print(f"  {status}  {table_name}: {len(db_cols)} cols, {row_count} rows")
            if phantom:
                print(f"         Phantom (ORM-only): {sorted(phantom)}")
            if orphaned:
                print(f"         Orphaned (DB-only): {sorted(orphaned)}")

        print("=" * 60)
        if all_passed:
            print("  🟢 OVERALL: PASS — all table shapes match ORM")
        else:
            print("  🔴 OVERALL: FAIL — mismatches detected")
        print("=" * 60)

        assert all_passed, "ORM/DB schema mismatch detected"
