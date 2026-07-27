"""
KAN-402: MinIO env-key drift detection.

After a `docker compose down -v` the local MinIO container recreates with
whatever MINIO_ROOT_USER / MINIO_ROOT_PASSWORD the compose file sets. The
app's MINIO_ACCESS_KEY / MINIO_SECRET_KEY must agree or uploads 500.

These tests pin the warning behavior added in KAN-402 so future drift
regressions are caught at CI time, not by a 500 in production.
"""

from __future__ import annotations

import os
import warnings

import pytest

from app.core import config as config_module


def _reload_settings(monkeypatch: pytest.MonkeyPatch, **env_overrides: str) -> None:
    """Reload app.core.config.Settings with the given env overrides applied.

    Uses monkeypatch.setenv so the original process environment is restored
    after the test. We bypass the module-level `settings = Settings()` cache
    by re-instantiating directly.
    """
    for key, value in env_overrides.items():
        monkeypatch.setenv(key, value)
    # Force the test-environment to the same path the Settings class uses.
    new_settings = config_module.Settings()
    config_module.settings = new_settings  # type: ignore[attr-defined]
    return new_settings


def test_minio_env_check_warns_on_access_key_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MINIO_ACCESS_KEY != MINIO_ROOT_USER must raise a RuntimeWarning in staging."""
    _reload_settings(
        monkeypatch,
        ENVIRONMENT="staging",
        USE_MINIO="true",
        MINIO_ACCESS_KEY="app-side-key",
        MINIO_SECRET_KEY="shared-secret",
        MINIO_ROOT_USER="container-side-key",
        MINIO_ROOT_PASSWORD="shared-secret",
    )
    settings = config_module.settings  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings.minio_env_check()
    drift_warnings = [
        str(w.message) for w in captured if "KAN-402 drift" in str(w.message)
    ]
    assert drift_warnings, "expected a KAN-402 drift warning for access key"
    assert any("MINIO_ACCESS_KEY" in m for m in drift_warnings)


def test_minio_env_check_warns_on_secret_key_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MINIO_SECRET_KEY != MINIO_ROOT_PASSWORD must raise a RuntimeWarning in staging."""
    _reload_settings(
        monkeypatch,
        ENVIRONMENT="staging",
        USE_MINIO="true",
        MINIO_ACCESS_KEY="shared-key",
        MINIO_SECRET_KEY="app-side-secret",
        MINIO_ROOT_USER="shared-key",
        MINIO_ROOT_PASSWORD="container-side-secret",
    )
    settings = config_module.settings  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings.minio_env_check()
    drift_warnings = [
        str(w.message) for w in captured if "KAN-402 drift" in str(w.message)
    ]
    assert drift_warnings, "expected a KAN-402 drift warning for secret key"
    assert any("MINIO_SECRET_KEY" in m for m in drift_warnings)


def test_minio_env_check_silent_when_keys_aligned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No drift warning when app + container keys match (the post-fix happy path)."""
    _reload_settings(
        monkeypatch,
        ENVIRONMENT="staging",
        USE_MINIO="true",
        MINIO_ACCESS_KEY="minioadmin",
        MINIO_SECRET_KEY="minioadmin",
        MINIO_ROOT_USER="minioadmin",
        MINIO_ROOT_PASSWORD="minioadmin",
    )
    settings = config_module.settings  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings.minio_env_check()
    drift_warnings = [
        str(w.message) for w in captured if "KAN-402 drift" in str(w.message)
    ]
    assert not drift_warnings, (
        f"unexpected drift warnings when keys are aligned: {drift_warnings}"
    )


def test_minio_env_check_silent_when_root_user_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When MINIO_ROOT_USER is not provided we cannot detect drift; skip silently."""
    # Ensure MINIO_ROOT_USER is unset.
    monkeypatch.delenv("MINIO_ROOT_USER", raising=False)
    monkeypatch.delenv("MINIO_ROOT_PASSWORD", raising=False)
    _reload_settings(
        monkeypatch,
        ENVIRONMENT="staging",
        USE_MINIO="true",
        MINIO_ACCESS_KEY="minioadmin",
        MINIO_SECRET_KEY="minioadmin",
    )
    settings = config_module.settings  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings.minio_env_check()
    drift_warnings = [
        str(w.message) for w in captured if "KAN-402 drift" in str(w.message)
    ]
    assert not drift_warnings, (
        f"drift warning should be silent when MINIO_ROOT_USER is unset: {drift_warnings}"
    )


def test_minio_env_check_skipped_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The drift check only fires in staging / production (per existing KAN-402 scope)."""
    _reload_settings(
        monkeypatch,
        ENVIRONMENT="development",
        USE_MINIO="true",
        MINIO_ACCESS_KEY="app-side-key",
        MINIO_SECRET_KEY="app-side-secret",
        MINIO_ROOT_USER="container-side-key",
        MINIO_ROOT_PASSWORD="container-side-secret",
    )
    settings = config_module.settings  # type: ignore[attr-defined]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        settings.minio_env_check()
    drift_warnings = [
        str(w.message) for w in captured if "KAN-402 drift" in str(w.message)
    ]
    assert not drift_warnings, (
        f"drift warnings should be suppressed in development: {drift_warnings}"
    )
