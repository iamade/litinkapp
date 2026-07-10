import os
import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

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


_fake_logging.get_logger = _get_logger
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
