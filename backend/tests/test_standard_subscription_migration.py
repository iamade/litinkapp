import pytest

from migrations.versions import (
    scriptstandard02_backfill_standard_subscriptions as migration,
)


def test_backfill_reads_canonical_standard_price_env_vars(monkeypatch):
    monkeypatch.setenv("STRIPE_STANDARD_PRICE_ID", "price_standard_canonical")
    monkeypatch.setenv("STRIPE_STANDARD_MONTHLY_PRICE_ID", "price_standard_monthly")
    monkeypatch.setenv("STRIPE_STANDARD_ANNUAL_PRICE_ID", "price_standard_annual")
    assert migration._standard_price_ids() == [
        "price_standard_canonical",
        "price_standard_monthly",
        "price_standard_annual",
    ]


def test_backfill_rejects_missing_or_malformed_price_ids(monkeypatch):
    monkeypatch.delenv("STRIPE_STANDARD_PRICE_ID", raising=False)
    monkeypatch.delenv("STRIPE_STANDARD_MONTHLY_PRICE_ID", raising=False)
    monkeypatch.delenv("STRIPE_STANDARD_ANNUAL_PRICE_ID", raising=False)
    with pytest.raises(RuntimeError, match="requires"):
        migration._standard_price_ids()

    monkeypatch.setenv("STRIPE_STANDARD_PRICE_ID", "not-a-price")
    with pytest.raises(RuntimeError, match="invalid format"):
        migration._standard_price_ids()
