"""KAN-438 regression fix verification: video_segments.sequence_index.

These are offline/structural checks (no DB connection required) that verify:
  1. The migration file exists and adds ``sequence_index int NOT NULL``.
  2. The ``VideoSegment`` SQLModel declares ``sequence_index: int`` as required.
  3. The two cinematic-gates service queries against ``video_segments`` now
     resolve — i.e., the column referenced in ``ORDER BY sequence_index``
     exists on the table definition.
  4. Every ``INSERT INTO video_segments`` path (``video_tasks.py`` x3,
     ``lipsync_tasks.py`` x2) provides a value for ``sequence_index``.

The runtime pass/fail verification will be redone by PSQ against
``backend-dev`` after this branch is merged to dev_branch.
"""
from pathlib import Path
import re

BACKEND = Path(__file__).parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text()


def test_migration_adds_sequence_index_not_null():
    """Migration must add ``sequence_index INTEGER NOT NULL`` to video_segments."""
    migration = _read(
        "migrations/versions/kan_438_video_segments_sequence_index.py"
    )
    assert "op.add_column" in migration
    # Locate the add_column('video_segments', ...) call.
    m = re.search(
        r"op\.add_column\(\s*'video_segments'\s*,\s*sa\.Column\(\s*'sequence_index'",
        migration,
    )
    assert m is not None, (
        "migration must op.add_column('video_segments', sa.Column('sequence_index'...))"
    )
    # NOT NULL is enforced in a second op.alter_column call.
    assert (
        "'sequence_index'" in migration
        and "nullable=False" in migration
    ), "migration must end with NOT NULL on sequence_index"


def test_migration_is_chained_after_merge_kan438_439():
    """The migration must depend on ``merge_kan438_439`` (no head fork)."""
    migration = _read(
        "migrations/versions/kan_438_video_segments_sequence_index.py"
    )
    assert "down_revision = 'merge_kan438_439'" in migration
    assert "revision = 'kan438_seg_seq_idx'" in migration


def test_video_segment_sqlmodel_declares_sequence_index():
    """VideoSegment ORM must declare ``sequence_index`` as ``int`` + ``nullable=False``."""
    models = _read("app/videos/models.py")
    # Locate the VideoSegment class definition and the next 35 lines for inspection.
    m = re.search(r"class VideoSegment\(SQLModel, table=True\):.*?(?=\nclass )", models, re.DOTALL)
    assert m is not None, "VideoSegment class must exist in app/videos/models.py"
    body = m.group(0)
    assert "sequence_index: int" in body, (
        "VideoSegment must declare `sequence_index: int`"
    )
    # Field line must include nullable=False
    assert re.search(
        r"sequence_index:\s*int\s*=\s*Field\([^)]*nullable=False",
        body,
    ), "VideoSegment.sequence_index must be Field(nullable=False)"


def test_shot_diversity_query_orders_by_sequence_index():
    """shot_diversity_service.analyze_shots must ORDER BY sequence_index."""
    src = _read("app/core/services/shot_diversity_service.py")
    m = re.search(
        r"SELECT \* FROM video_segments.*?ORDER BY sequence_index",
        src,
        re.DOTALL,
    )
    assert m is not None, (
        "shot_diversity_service.analyze_shots must ORDER BY sequence_index"
    )


def test_continuity_query_orders_by_sequence_index():
    """continuity_service.run_adjacent_shot_qa must ORDER BY sequence_index."""
    src = _read("app/core/services/continuity_service.py")
    m = re.search(
        r"SELECT \* FROM video_segments.*?ORDER BY sequence_index",
        src,
        re.DOTALL,
    )
    assert m is not None, (
        "continuity_service.run_adjacent_shot_qa must ORDER BY sequence_index"
    )


def test_video_tasks_inserts_provide_sequence_index():
    """All 3 video_tasks INSERTs must bind :sequence_index."""
    src = _read("app/tasks/video_tasks.py")
    # We expect both the column list and the bind dict to mention sequence_index.
    assert src.count("INSERT INTO video_segments") == 3, (
        f"expected 3 INSERT INTO video_segments in video_tasks.py, found "
        f"{src.count('INSERT INTO video_segments')}"
    )
    assert src.count(":sequence_index") == 3, (
        "every video_tasks INSERT must bind :sequence_index"
    )
    assert src.count('"sequence_index":') == 3, (
        "every video_tasks INSERT bind dict must include sequence_index value"
    )


def test_lipsync_tasks_inserts_provide_sequence_index():
    """Both lipsync_tasks INSERTs must bind :sequence_index."""
    src = _read("app/tasks/lipsync_tasks.py")
    assert src.count("INSERT INTO video_segments") == 2, (
        f"expected 2 INSERT INTO video_segments in lipsync_tasks.py, found "
        f"{src.count('INSERT INTO video_segments')}"
    )
    assert src.count(":sequence_index") == 2, (
        "every lipsync_tasks INSERT must bind :sequence_index"
    )
    assert src.count('"sequence_index":') == 2, (
        "every lipsync_tasks INSERT bind dict must include sequence_index value"
    )
