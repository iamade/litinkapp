"""Offline signed Stripe SDK events: parse the items key, not dict.items."""
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock

import pytest
import stripe

from app.core.services.stripe import StripeService

SIGNING_SECRET = "whsec_offline_kan523_fixture"


def signed_payload(items, cancel=False):
    subscription = {
        "id": "sub_offline", "object": "subscription", "customer": "cus_offline",
        "status": "active", "current_period_start": 1700000000,
        "current_period_end": 1800000000, "cancel_at_period_end": cancel,
    }
    if items is not None:
        subscription["items"] = {"object": "list", "data": items}
    payload = json.dumps({"id": "evt_offline", "object": "event",
                          "type": "customer.subscription.updated",
                          "data": {"object": subscription}}).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(SIGNING_SECRET.encode(), timestamp.encode() + b"." + payload,
                      hashlib.sha256).hexdigest()
    return payload, f"t={timestamp},v1={digest}"


@pytest.fixture
def service(monkeypatch):
    service = StripeService()
    service.webhook_secret = SIGNING_SECRET
    def no_network(*args, **kwargs):
        raise AssertionError("Stripe API calls are forbidden in this unit proof")
    monkeypatch.setattr(stripe.Subscription, "retrieve", no_network)
    monkeypatch.setattr(stripe.Subscription, "modify", no_network)
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_signed_updated_sdk_items_key_parses_without_method_collision(service, cancel):
    payload, signature = signed_payload([
        {"id": "si_offline", "object": "subscription_item",
         "price": {"id": "price_offline", "object": "price"}}
    ], cancel)
    event = stripe.Webhook.construct_event(payload, signature, SIGNING_SECRET)
    assert callable(event.data.object.items)
    assert event.data.object["items"].data[0].price.id == "price_offline"
    result = await service.handle_webhook(payload, signature)
    assert result == {
        "event_type": "subscription.updated", "subscription_id": "sub_offline",
        "customer_id": "cus_offline", "status": "active", "price_id": "price_offline",
        "current_period_start": 1700000000, "current_period_end": 1800000000,
        "cancel_at_period_end": cancel,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("items", [[], None])
async def test_signed_updated_missing_or_empty_items_has_no_price(service, items):
    payload, signature = signed_payload(items)
    result = await service.handle_webhook(payload, signature)
    assert result["price_id"] is None
    assert result["subscription_id"] == "sub_offline"


@pytest.mark.asyncio
@pytest.mark.parametrize("tampered", [False, True])
async def test_invalid_signature_rejected_before_updated_parser(service, monkeypatch, tampered):
    payload, signature = signed_payload([])
    handler = AsyncMock()
    monkeypatch.setattr(service, "_handle_subscription_updated", handler)
    if tampered:
        payload = payload.replace(b"sub_offline", b"sub_tampered")
    else:
        signature = signature[:-1] + ("0" if signature[-1] != "0" else "1")
    with pytest.raises(stripe.error.SignatureVerificationError):
        await service.handle_webhook(payload, signature)
    handler.assert_not_awaited()
