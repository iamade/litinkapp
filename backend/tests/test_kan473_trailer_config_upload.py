"""KAN-473: trailer_config must never be empty on a real trailer run.

Gap (code-verified independently; matches ticket + PSQ project 5ce1c598):
the upload route declared no trailer_config Form param, so the FE's KAN-147
forward (trailer_config JSON + explicit output_type='trailer') was silently
dropped by FastAPI, and the backend's only config-population branch
(_detect_trailer_intent) is skipped whenever output_type is explicitly set —
so output_type='trailer' persisted while trailer_config stayed {}.

Fix: _resolve_trailer_output() —
- output_type absent      -> legacy KAN-146 detection from consultation_data
- output_type='trailer'   -> config from explicit form JSON (keys filtered,
  merged over defaults) > consultation agreements > defaults: NEVER empty
- any other explicit type -> config stays empty
"""

import os

# Test-safe env BEFORE app imports (same pattern as test_kan470_471).
os.environ.setdefault("ENVIRONMENT", "staging")
os.environ.setdefault("JWT_SECRET_KEY", "x" * 48)
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
os.environ.setdefault("MODELSLAB_API_KEY", "dummy")
os.environ.setdefault("MAIL_FROM", "noreply@example.com")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("STRIPE_PUBLISHABLE_KEY", "pk_test_dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY", "dummy")
os.environ.setdefault("KLINGAI_ACCESS_KEY_SECRET", "dummy")
for _k in [
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "REDIS_URL", "CELERY_BROKER_URL",
]:
    os.environ.setdefault(_k, "dummy" if "PORT" not in _k else "0")

import pytest

from app.api.routes.projects.routes import _resolve_trailer_output

CONSULTATION_TRAILER = {
    "recommended_action": "trailer_promo",
    "agreements": {
        "content_type": "trailer",
        "target_duration_seconds": 45,
        "tone": "dark",
        "style": "gritty",
    },
}

DEFAULTS = {"target_duration_seconds": 90, "tone": "epic", "style": "cinematic"}


def test_explicit_trailer_form_json_wins_over_consultation():
    ot, cfg = _resolve_trailer_output(
        "trailer", '{"target_duration_seconds": 30, "tone": "epic"}',
        CONSULTATION_TRAILER,
    )
    assert ot == "trailer"
    assert cfg == {
        "target_duration_seconds": 30,  # form JSON overrides agreements
        "tone": "epic",
        "style": "cinematic",           # default fill
    }


def test_explicit_trailer_without_form_json_uses_consultation():
    ot, cfg = _resolve_trailer_output("trailer", None, CONSULTATION_TRAILER)
    assert ot == "trailer"
    assert cfg == {
        "target_duration_seconds": 45,
        "tone": "dark",
        "style": "gritty",
    }


def test_explicit_trailer_with_nothing_gets_defaults():
    """THE KAN-473 completion condition: config never empty on a real run."""
    ot, cfg = _resolve_trailer_output("trailer", None, None)
    assert ot == "trailer"
    assert cfg == DEFAULTS


def test_explicit_trailer_malformed_json_falls_back_to_defaults():
    ot, cfg = _resolve_trailer_output("trailer", "{broken json", None)
    assert ot == "trailer"
    assert cfg == DEFAULTS


def test_explicit_trailer_non_dict_json_falls_back():
    ot, cfg = _resolve_trailer_output("trailer", '["not", "a", "dict"]', None)
    assert ot == "trailer"
    assert cfg == DEFAULTS


def test_explicit_trailer_form_json_unknown_keys_filtered():
    ot, cfg = _resolve_trailer_output(
        "trailer", '{"tone": "warm", "evil_key": "injected"}', None
    )
    assert ot == "trailer"
    assert cfg["tone"] == "warm"
    assert "evil_key" not in cfg


def test_absent_output_type_keeps_legacy_kan146_detection():
    ot, cfg = _resolve_trailer_output(None, None, CONSULTATION_TRAILER)
    assert ot == "trailer"
    assert cfg["tone"] == "dark"


def test_absent_output_type_no_consultation_returns_none():
    ot, cfg = _resolve_trailer_output(None, None, None)
    assert ot is None
    assert cfg == {}


def test_absent_output_type_non_trailer_consultation_returns_none():
    ot, cfg = _resolve_trailer_output(
        None, None, {"recommended_action": "full_production", "agreements": {}}
    )
    assert ot is None
    assert cfg == {}


def test_non_trailer_output_type_keeps_empty_config():
    ot, cfg = _resolve_trailer_output(
        "full_production", '{"tone": "x"}', CONSULTATION_TRAILER
    )
    assert ot == "full_production"
    assert cfg == {}
