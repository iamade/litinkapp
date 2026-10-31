import os
import re
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# KAN-505 - session-scoped provider env defaults (set ONCE, before any app import)
# ---------------------------------------------------------------------------
# app/core/config.py:456 builds the settings singleton AT IMPORT TIME, so every
# provider key is FROZEN the moment any app module is imported:
#
#   app/core/config.py:300        MODELSLAB_API_KEY = os.getenv("MODELSLAB_API_KEY", "")
#   app/core/config.py:456        settings = Settings()          # import-time singleton
#   app/core/services/modelslab_v7_image.py:16-17
#                                if not settings.MODELSLAB_API_KEY:
#                                    raise ValueError("MODELSLAB_API_KEY is required")
#   app/core/services/modelslab_v7_audio.py:17 / modelslab_v7_video.py:17 /
#   app/core/services/modelslab_upscale.py:37   same guard
#   app/core/services/stripe.py:14
#                                if not settings.STRIPE_SECRET_KEY: raise ValueError(...)
#   app/api/services/character.py:71             self.image_service = ModelsLabV7ImageService()
#
# The services read the FROZEN settings snapshot, NOT os.environ, so a key set
# AFTER the singleton exists has no effect (proven: settings.MODELSLAB_API_KEY
# stays '' after a later os.environ assignment).
#
# Previously every test file set its own env with os.environ.setdefault() at
# the TOP of the file - but that only works if that file is the FIRST to import
# an app module. When a file that imports app.core.services.file (and therefore
# app.core.config) was collected first, the singleton was created with
# MODELSLAB_API_KEY empty, and every later CharacterService() construction in
# the whole session raised ValueError. The suite result therefore depended on
# COLLECTION ORDER: collecting
#   test_kan226_content_type_persistence.py then test_kan501_ownership_uuid_compare.py
# failed 7 kan501 cases, while the swapped order passed all 22. That is a FALSE
# RED in the harness, not a product defect - modelslab_v7_image.py refusing an
# empty key is intended and fail-safe, and product code is NOT changed here.
#
# pytest imports conftest.py BEFORE any test module, so setting the defaults
# here makes the env population independent of collection order and fixes the
# CLASS of defect (the next test file added before an app import would
# otherwise inherit the same false red).
#
# Dummy literals only - no real credentials, no provider call is made.
# DATABASE_URL is deliberately NOT set here: test files disagree on purpose
# (sqlite+aiosqlite:///:memory: vs postgresql+asyncpg://...), and a
# session-wide default would silently override them. Keys that tests assert
# must be ABSENT (via monkeypatch.delenv) are likewise not set here.
_PROVIDER_ENV_DEFAULTS = {
    # provider keys frozen at import time (these raise on an empty value)
    "MODELSLAB_API_KEY": "dummy",
    "OPENAI_API_KEY": "sk-dummy",
    "STRIPE_SECRET_KEY": "sk_test-dummy",
    "STRIPE_PUBLISHABLE_KEY": "pk_test_dummy",
    "STRIPE_WEBHOOK_SECRET": "whsec_dummy",
    # app/config values other test files already provide for themselves
    "JWT_SECRET_KEY": "x" * 48,
    "MAIL_FROM": "noreply@example.com",
    "ENVIRONMENT": "staging",
    "SMTP_HOST": "localhost",
    "SMTP_USER": "dummy",
    "SMTP_PASSWORD": "dummy",
    "SMTP_PORT": "0",
    "REDIS_URL": "redis://localhost:6379/0",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
}
for _env_key, _env_value in _PROVIDER_ENV_DEFAULTS.items():
    os.environ.setdefault(_env_key, _env_value)
del _env_key, _env_value

# Ensure imports like `from app...` work when running pytest from backend/
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

# Patch loguru BEFORE app.core.logging is imported so that file-sink
# creation does not fail on root-owned log files in CI / test runners.
import loguru

loguru.logger.remove()
loguru.logger.add(sys.stderr, level="WARNING")

# Pre-populate app.core.logging with a test-safe stub so that the real
# module (which tries to open root-owned log files) is never executed.
_fake_logging = types.ModuleType("app.core.logging")


def _get_logger():
    return loguru.logger


def _redact_identity_like_output(message: object) -> str:
    return re.sub(r"\b[A-Z2-7]{58}\b", "[REDACTED_IDENTITY]", str(message))


_fake_logging.get_logger = _get_logger
_fake_logging.redact_identity_like_output = _redact_identity_like_output
sys.modules["app.core.logging"] = _fake_logging

# Lightweight stubs so tests can import storage service without optional deps installed.
if "boto3" not in sys.modules:
    boto3_stub = types.ModuleType("boto3")
    boto3_stub.client = MagicMock()
    sys.modules["boto3"] = boto3_stub

if "botocore" not in sys.modules:
    botocore_stub = types.ModuleType("botocore")
    sys.modules["botocore"] = botocore_stub

if "botocore.client" not in sys.modules:
    botocore_client_stub = types.ModuleType("botocore.client")

    class _Config:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    botocore_client_stub.Config = _Config
    sys.modules["botocore.client"] = botocore_client_stub

if "botocore.exceptions" not in sys.modules:
    botocore_exceptions_stub = types.ModuleType("botocore.exceptions")

    class _ClientError(Exception):
        pass

    botocore_exceptions_stub.ClientError = _ClientError
    sys.modules["botocore.exceptions"] = botocore_exceptions_stub


@pytest.fixture
def mock_async_session():
    return AsyncMock()


@pytest.fixture
def mock_storage_service():
    from app.core.services.storage import S3StorageService

    storage = MagicMock(spec=S3StorageService)
    storage.persist_from_url = AsyncMock(
        return_value="https://s3.example.com/test.png"
    )
    return storage


@pytest.fixture
def sample_image_generation_record():
    return {
        "id": "rec-123",
        "image_url": "https://pub-cdn.modelslab.com/test.png",
        "user_id": "user-123",
        "meta": {},
        "status": "completed",
    }
