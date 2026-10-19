"""KAN-453: retry-state columns must agree between model and migration.

PSQ failed 8035705b code-only because the model declared
server_default="0" for retry-count columns while the migration never
altered pipeline_steps, leaving the database column with no default.
These assertions lock the model side; the migration is asserted
separately by test_kan453_migration_reconciles_pipeline_steps.
"""
import pathlib
import re

from app.videos.models import PipelineStepModel, VideoGeneration


def test_video_generation_retry_state_has_database_defaults():
    table = VideoGeneration.__table__
    assert str(table.c.can_resume.server_default.arg) == "false"
    assert str(table.c.retry_count.server_default.arg) == "0"
    assert table.c.can_resume.nullable is False
    assert table.c.retry_count.nullable is False


def test_pipeline_step_retry_count_has_database_default():
    """The column PSQ's FAIL was actually about: pipeline_steps.retry_count."""
    assert PipelineStepModel.__tablename__ == "pipeline_steps"
    col = PipelineStepModel.__table__.c.retry_count
    assert str(col.server_default.arg) == "0"
    assert col.nullable is False


def _kan453_migration_source() -> str:
    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "kan453_video_generation_defaults.py"
    )
    return path.read_text()


def test_kan453_migration_reconciles_pipeline_steps():
    """The migration must alter pipeline_steps, not just video_generations.

    Without this, the model advertises a default the database does not
    have - the exact mismatch that made 8035705b a code-only FAIL.
    """
    src = _kan453_migration_source()
    upgrade = src.split("def downgrade")[0]
    assert "pipeline_steps" in upgrade, (
        "upgrade() must alter pipeline_steps.retry_count; the model sets "
        "server_default='0' and the DB column had none"
    )
    assert re.search(
        r'alter_column\(\s*["\']pipeline_steps["\'],\s*["\']retry_count["\']',
        upgrade,
    ), "upgrade() must alter_column('pipeline_steps', 'retry_count', ...)"

    downgrade = src.split("def downgrade")[1]
    assert "pipeline_steps" in downgrade, "downgrade() must reverse it"
