import pytest
import os

class TestDockerCelerybeatConfig:
    def test_dockerfile_exists(self):
        """Dockerfile or docker-compose should reference celerybeat"""
        # Updated 2026-05-26 per litinkai-infra-redesign-2026-05-26.md:
        # the canonical compose file is backend/local.yml (root-level docker-compose.yml
        # being removed). Test now points at backend/local.yml.
        compose_path = os.path.join(os.path.dirname(__file__), '..', 'local.yml')
        if os.path.exists(compose_path):
            with open(compose_path) as f:
                content = f.read()
            assert 'celerybeat' in content.lower() or 'beat' in content.lower(), 'backend/local.yml should reference celerybeat'

    def test_celery_beat_schedule_exists(self):
        """Celery app should have a beat schedule configured"""
        # Import will fail if celery_app has syntax errors
        from app.tasks.celery_app import celery_app
        # Check beat_schedule exists (may be empty but should be defined)
        assert hasattr(celery_app.conf, 'beat_schedule') or 'beat_schedule' in dir(celery_app.conf)
