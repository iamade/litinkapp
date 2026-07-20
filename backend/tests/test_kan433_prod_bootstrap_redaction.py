import pytest

import algosdk
from app.core.config import settings
from app.core.logging import redact_identity_like_output
from app.core.services.blockchain import BlockchainService


ALGORAND_ADDRESS = "A" * 58


def _creator_account_service() -> BlockchainService:
    return BlockchainService.__new__(BlockchainService)


def _fail_generate_account():
    raise AssertionError("development identity generation must not be called")


def test_production_malformed_creator_mnemonic_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CREATOR_MNEMONIC", "too short")
    monkeypatch.setattr(algosdk.account, "generate_account", _fail_generate_account)

    with pytest.raises(RuntimeError, match="refusing production blockchain bootstrap"):
        _creator_account_service()._init_creator_account()


def test_production_missing_creator_mnemonic_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CREATOR_MNEMONIC", None)
    monkeypatch.setattr(algosdk.account, "generate_account", _fail_generate_account)

    with pytest.raises(RuntimeError, match="CREATOR_MNEMONIC must be configured"):
        _creator_account_service()._init_creator_account()


def test_development_malformed_creator_mnemonic_uses_mock_without_identity(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "CREATOR_MNEMONIC", "too short")
    monkeypatch.setattr(algosdk.account, "generate_account", _fail_generate_account)

    assert _creator_account_service()._init_creator_account() is None

    output = capsys.readouterr().out
    assert "Generated new creator account" not in output
    assert ALGORAND_ADDRESS not in output
    assert "using blockchain mock mode" in output


def test_startup_log_redacts_algorand_identity_like_values() -> None:
    message = f"Generated new creator account: {ALGORAND_ADDRESS}"

    redacted = redact_identity_like_output(message)

    assert ALGORAND_ADDRESS not in redacted
    assert "[REDACTED_IDENTITY]" in redacted
