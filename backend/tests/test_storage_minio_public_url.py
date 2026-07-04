from app.core.services import storage as storage_module
from app.core.services.storage import S3StorageService


def _storage_for_minio(bucket_name: str = "litinkai-staging") -> S3StorageService:
    storage = object.__new__(S3StorageService)
    storage.use_minio = True
    storage.bucket_name = bucket_name
    return storage


def test_minio_public_url_uses_provider_port_when_public_url_omits_port(monkeypatch):
    monkeypatch.setattr(
        storage_module.settings,
        "MINIO_PUBLIC_URL",
        "https://minio-staging.litinkai.com",
    )
    monkeypatch.setattr(
        storage_module.settings,
        "MINIO_PROVIDER_PUBLIC_URL",
        "https://minio-staging.litinkai.com:8443",
    )
    monkeypatch.setattr(storage_module.settings, "MODELSLAB_MEDIA_PUBLIC_URL", None)

    storage = _storage_for_minio()

    assert (
        storage.get_public_url("users/u1/images/object.png")
        == "https://minio-staging.litinkai.com:8443/litinkai-staging/users/u1/images/object.png"
    )


def test_minio_public_url_adds_staging_default_port_when_no_provider_url(monkeypatch):
    monkeypatch.setattr(
        storage_module.settings,
        "MINIO_PUBLIC_URL",
        "https://minio-staging.litinkai.com",
    )
    monkeypatch.setattr(storage_module.settings, "MINIO_PROVIDER_PUBLIC_URL", None)
    monkeypatch.setattr(storage_module.settings, "MODELSLAB_MEDIA_PUBLIC_URL", None)

    storage = _storage_for_minio()

    assert (
        storage.get_public_url("users/u1/images/object.png")
        == "https://minio-staging.litinkai.com:8443/litinkai-staging/users/u1/images/object.png"
    )


def test_minio_public_url_preserves_existing_port(monkeypatch):
    monkeypatch.setattr(
        storage_module.settings,
        "MINIO_PUBLIC_URL",
        "https://minio-staging.litinkai.com:8443",
    )
    monkeypatch.setattr(
        storage_module.settings,
        "MINIO_PROVIDER_PUBLIC_URL",
        "https://minio-staging.litinkai.com:9443",
    )

    storage = _storage_for_minio()

    assert (
        storage.get_public_url("users/u1/images/object.png")
        == "https://minio-staging.litinkai.com:8443/litinkai-staging/users/u1/images/object.png"
    )

