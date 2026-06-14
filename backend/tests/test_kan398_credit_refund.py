"""
KAN-398(c) — Credits must be refunded (reservation released) when a billable
generation fails.

These tests pin the behavior of CreditService.credit_transaction: the async
context manager confirms the deduction on success and releases the reservation
on ANY exception raised inside the `with` block, then re-raises so the caller
still sees the failure.

Run:
    pytest tests/test_kan398_credit_refund.py
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.credits.service import CreditService


@pytest.fixture
def service(mock_async_session):
    """CreditService with a mocked AsyncSession (commit/rollback are no-ops)."""
    svc = CreditService(mock_async_session)
    # Isolate the context-manager logic from the DB-touching helpers.
    svc.confirm_deduction = AsyncMock(return_value=True)
    svc.release_reservation = AsyncMock(return_value=True)
    return svc


@pytest.mark.asyncio
async def test_credit_transaction_confirms_on_success(service):
    reservation_id = uuid.uuid4()
    amount = 2

    async with service.credit_transaction(reservation_id, amount):
        pass  # billable work succeeds

    service.confirm_deduction.assert_awaited_once_with(reservation_id, amount)
    service.release_reservation.assert_not_awaited()


@pytest.mark.asyncio
async def test_credit_transaction_refunds_on_failure(service):
    """On generation failure the reservation is released (credits refunded)."""
    reservation_id = uuid.uuid4()
    amount = 2

    with pytest.raises(RuntimeError, match="generation blew up"):
        async with service.credit_transaction(reservation_id, amount):
            raise RuntimeError("generation blew up")

    # Refund happened ...
    service.release_reservation.assert_awaited_once_with(reservation_id)
    # ... and no deduction was confirmed.
    service.confirm_deduction.assert_not_awaited()


@pytest.mark.asyncio
async def test_credit_transaction_reraises_original_error(service):
    """The caller must still observe the underlying failure after the refund."""
    reservation_id = uuid.uuid4()

    class GenerationError(Exception):
        pass

    with pytest.raises(GenerationError):
        async with service.credit_transaction(reservation_id, 1):
            raise GenerationError("model timeout")

    service.release_reservation.assert_awaited_once_with(reservation_id)
