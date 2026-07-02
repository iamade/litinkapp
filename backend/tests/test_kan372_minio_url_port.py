"""Regression test for KAN-372: MinIO public URL must include an explicit port.

Some MinIO deployments (notably VPS staging) terminate TLS only on a non-default
port (e.g. :8443) behind a reverse proxy. If the configured ``MINIO_PUBLIC_URL``
omits an explicit port, the URL silently falls back to the scheme default
(443/80) and never resolves.

This test pins the helper so any future change that bypasses it (or that
re-introduces a raw ``f"{settings.MINIO_PUBLIC_URL}/{bucket}/{path}"``
expression) is caught in CI.
"""

import pytest
from unittest.mock import patch

from app.core.services.storage import _enforce_minio_port


class TestEnforceMinioPort:
    """Unit tests for the URL port-enforcement helper."""

    def test_append_port_when_missing(self):
        """Scheme-only URL gets the configured port appended."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            result = _enforce_minio_port("https://minio-staging.litinkai.com")
            assert result == "https://minio-staging.litinkai.com:8443"

    def test_preserve_existing_port(self):
        """URLs that already declare a port must be left alone."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            result = _enforce_minio_port("https://minio-staging.litinkai.com:9000")
            assert result == "https://minio-staging.litinkai.com:9000"

    def test_no_port_configured(self):
        """If MINIO_PUBLIC_PORT is unset, URLs are returned untouched."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = None
            result = _enforce_minio_port("https://minio-staging.litinkai.com")
            assert result == "https://minio-staging.litinkai.com"

    def test_empty_url(self):
        """Empty input returns empty."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            assert _enforce_minio_port("") == ""

    def test_none_url(self):
        """None input returns None."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            assert _enforce_minio_port(None) is None

    def test_http_url(self):
        """HTTP scheme URLs get the port too."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            result = _enforce_minio_port("http://minio.local")
            assert result == "http://minio.local:8443"

    def test_invalid_url_passthrough(self):
        """Unparseable URLs are returned unchanged (defensive)."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            # Not a URL at all (no scheme/netloc)
            assert _enforce_minio_port("not-a-url") == "not-a-url"

    def test_bucket_path_uses_port(self):
        """Realistic MinIO bucket URL gets the port inserted."""
        with patch("app.core.services.storage.settings") as mock_settings:
            mock_settings.MINIO_PUBLIC_PORT = 8443
            base = "https://minio-staging.litinkai.com"
            full_url = f"{base}/litinkai-staging/users/abc/images/rec.png"
            result = _enforce_minio_port(full_url)
            assert result == (
                "https://minio-staging.litinkai.com:8443/"
                "litinkai-staging/users/abc/images/rec.png"
            )
