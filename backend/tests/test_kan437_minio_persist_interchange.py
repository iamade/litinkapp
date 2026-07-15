from unittest.mock import AsyncMock

import pytest

from app.core.services.storage import S3StorageService


class FakeStreamResponse:
    def __init__(self, body: bytes):
        self.body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def aiter_bytes(self, chunk_size=8192):
        yield self.body


class FakeAsyncClient:
    def __init__(self, bodies_by_url):
        self.bodies_by_url = bodies_by_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url):
        assert method == "GET"
        return FakeStreamResponse(self.bodies_by_url[url])


@pytest.mark.asyncio
async def test_modelslab_and_piapi_urls_persist_through_same_minio_mapping(monkeypatch):
    bodies_by_url = {
        "https://pub-cdn.modelslab.com/result.png": b"modelslab-image",
        "https://cdn.piapi.ai/result.png": b"piapi-image",
    }

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kwargs: FakeAsyncClient(bodies_by_url),
    )

    storage = S3StorageService()

    async def fake_upload_stream(file_stream, path, content_type=None):
        return f"{storage._minio_public_url_base()}/{storage.bucket_name}/{path}"

    storage.upload_stream = AsyncMock(side_effect=fake_upload_stream)

    modelslab_url = await storage.persist_from_url(
        "https://pub-cdn.modelslab.com/result.png",
        "users/system/images/modelslab.png",
        content_type="image/png",
    )
    piapi_url = await storage.persist_from_url(
        "https://cdn.piapi.ai/result.png",
        "users/system/images/piapi.png",
        content_type="image/png",
    )

    expected_prefix = f"{storage._minio_public_url_base()}/{storage.bucket_name}/"
    assert modelslab_url.startswith(expected_prefix)
    assert piapi_url.startswith(expected_prefix)
    assert storage.upload_stream.await_count == 2
