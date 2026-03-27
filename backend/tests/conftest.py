import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


# Ensure imports like `from app...` work when running pytest from backend/
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


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
