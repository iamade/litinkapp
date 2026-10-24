"""
KAN-494 — empty celery worker ping must be UNHEALTHY even when the broker
connection succeeds.

Defect (health.py check_celery): when celery_app.control.inspect().ping()
returned an empty result, the check opened a broker connection and, when the
broker was reachable, logged "No celery workers found, but Rabbitmq is
reachable" and returned True (healthy). Broker reachability must remain a
separate informational field and never become the celery health value; the
warning must name the broker from configuration without logging credentials.

Runs with dummy env per litinkapp-test-runs (no real broker/database needed):
  DATABASE_URL='postgresql+asyncpg://u:p@localhost:5432/db' \
  STRIPE_SECRET_KEY='sk_test-dummy' MAIL_FROM='test@litinkai.dev' \
  PYTHONPATH=. /usr/bin/python3 -m pytest tests/test_kan494_celery_empty_ping_unhealthy.py -q
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from loguru import logger as loguru_logger

import app.core.health as health_module
from app.core.health import HealthCheck

# Fake broker URL carrying a sentinel credential: proves the warning names
# the broker from configuration without ever logging the URL itself.
BROKER_URL = "amqp://unit:secret-password@broker.internal:5672/litink"


class _FakeInspect:
    def __init__(self, ping_result):
        self._ping_result = ping_result

    def ping(self):
        return self._ping_result


class _FakeControl:
    def __init__(self, ping_result):
        self._inspect = _FakeInspect(ping_result)

    def inspect(self, *args, **kwargs):
        return self._inspect


class _FakeBrokerConnection:
    """Broker connection that always succeeds (broker is reachable)."""

    def ensure_connection(self, *args, **kwargs):
        return None

    def close(self):
        pass


class _FakeCeleryApp:
    def __init__(self, ping_result, broker_url=BROKER_URL):
        self.control = _FakeControl(ping_result)
        self.conf = SimpleNamespace(broker_url=broker_url)

    def connection(self):
        return _FakeBrokerConnection()


@pytest.mark.asyncio
@pytest.mark.parametrize("ping_result", [{}, None], ids=["empty-dict", "none"])
async def test_empty_ping_with_reachable_broker_is_unhealthy(monkeypatch, ping_result):
    """Regression: no worker replies + broker connect OK => celery UNHEALTHY."""
    monkeypatch.setattr(
        health_module, "celery_app", _FakeCeleryApp(ping_result=ping_result)
    )
    checker = HealthCheck()

    captured = io.StringIO()
    handler = loguru_logger.add(captured, level="WARNING")
    try:
        result = await checker.check_celery()
    finally:
        loguru_logger.remove(handler)

    assert result is False, (
        "empty ping().ping() result must be UNHEALTHY even when the broker "
        "connection succeeds; broker reachability may never be the celery "
        "health value (KAN-494)"
    )

    # Broker reachability stays a separate informational field only.
    assert checker._celery_broker_reachable is True

    warning = captured.getvalue()
    assert "No celery workers found" in warning
    # Warning names the actual broker from configuration (amqp => RabbitMQ) ...
    assert "RabbitMQ" in warning
    # ... without logging credentials or the broker host.
    assert "unit:secret-password" not in warning
    assert "broker.internal" not in warning
    assert BROKER_URL not in warning


@pytest.mark.asyncio
async def test_nonempty_ping_is_healthy(monkeypatch):
    """Control: live workers answering ping remains healthy (guard, not repair)."""
    live = {
        "worker1@litink-host": {"ok": "pong"},
        "worker2@litink-host": {"ok": "pong"},
    }
    monkeypatch.setattr(health_module, "celery_app", _FakeCeleryApp(ping_result=live))
    checker = HealthCheck()
    assert await checker.check_celery() is True
