from urllib.parse import urlparse

from app.core.config import settings
from app.core.services.storage import S3StorageService


def test_minio_public_and_presigned_input_urls_include_bucket_and_path(monkeypatch):
    monkeypatch.setattr(settings, "USE_MINIO", True)
    monkeypatch.setattr(settings, "MINIO_PUBLIC_URL", "http://localhost:9000")
    monkeypatch.setattr(settings, "MINIO_BUCKET_NAME", "litinkai-staging")

    storage = S3StorageService()
    path = "users/test/images/input.png"

    public_url = storage.get_public_url(path)
    presigned_url = storage.presigned_url(path)

    for url in (public_url, presigned_url):
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.netloc == "localhost:9000"
        assert parsed.path == f"/{storage.bucket_name}/{path}"
        assert url.startswith("http://localhost:9000/litinkai-staging/")
