from urllib.parse import urlparse

from app.core.config import settings
from app.core.services.storage import S3StorageService


def test_minio_presigned_audio_input_url_uses_public_base(monkeypatch):
    monkeypatch.setattr(settings, "USE_MINIO", True)
    monkeypatch.setattr(settings, "MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr(settings, "MINIO_BUCKET_NAME", "litinkai-staging")

    storage = S3StorageService()
    path = "users/test/audio/input.mp3"

    url = storage.presigned_url(path)
    parsed = urlparse(url)

    assert parsed.scheme == "http"
    assert parsed.netloc == "localhost:9000"
    assert parsed.path == f"/{storage.bucket_name}/{path}"
    assert url.startswith("http://localhost:9000/litinkai-staging/")
