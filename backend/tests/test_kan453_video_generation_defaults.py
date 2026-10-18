from app.videos.models import VideoGeneration


def test_video_generation_retry_state_has_database_defaults():
    table = VideoGeneration.__table__
    assert str(table.c.can_resume.server_default.arg) == "false"
    assert str(table.c.retry_count.server_default.arg) == "0"
    assert table.c.can_resume.nullable is False
    assert table.c.retry_count.nullable is False
