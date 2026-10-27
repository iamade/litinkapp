"""KAN-499/498/500: no usable credential may be committed to the repo.

These are source-level assertions on purpose. The defect in all three
tickets is that a secret was committed and usable *as written*, so the
lock has to fail if a literal ever comes back - not merely if runtime
behaviour happens to differ.
"""
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text()


def test_kan499_reset_script_has_no_hash_literal():
    src = _read("reset_support_pw.py")
    # A real argon2id hash, not the docstring's "$argon2id$..." mention.
    assert "$argon2id$v=" not in src, "reset_support_pw.py must not embed a hash"
    assert "SUPPORT_PW_RESET_PASSWORD" in src, "password must come from env"
    assert "--confirm" in src, "live-account write must require explicit confirm"


def test_kan498_seeder_has_no_default_passwords():
    from app.core.admin_seeder import ADMIN_ACCOUNTS

    for account in ADMIN_ACCOUNTS:
        assert "password" not in account, (
            f"{account['email']} must not carry a literal password"
        )
        assert "security_answer" not in account, (
            f"{account['email']} must not carry a literal security answer"
        )
        assert account["password_env"].startswith("SEED_")
        assert account["answer_env"].startswith("SEED_")


def test_kan498_seeder_skips_accounts_without_secret(monkeypatch):
    """Missing env must SKIP the account, never seed a guessable default."""
    from app.core import admin_seeder

    for a in admin_seeder.ADMIN_ACCOUNTS:
        monkeypatch.delenv(a["password_env"], raising=False)
        monkeypatch.delenv(a["answer_env"], raising=False)

    account = admin_seeder.ADMIN_ACCOUNTS[0]
    assert admin_seeder._account_secret(account, "password_env") is None
    assert admin_seeder._account_secret(account, "answer_env") is None

    monkeypatch.setenv(account["password_env"], "s3cret")
    assert admin_seeder._account_secret(account, "password_env") == "s3cret"

    # Blank/whitespace must be treated as absent, not as a password.
    monkeypatch.setenv(account["password_env"], "   ")
    assert admin_seeder._account_secret(account, "password_env") is None


def test_kan500_verify_backend_has_no_password_literal():
    import re
    src = _read("verify_backend.py")
    # Shape match, not an exact string: any literal assigned to TEST_PASSWORD
    # fails, whatever the quote style or spacing. An exact-match assertion was
    # proven bypassable by a same-value single-quoted or reformatted literal.
    assignment = re.search(r"TEST_PASSWORD\s*=\s*['\"][^'\"]*['\"]", src)
    # Assert on a BOOLEAN, never on the match object: reporting a re.Match lets
    # pytest echo match='<the literal>' in its repr, which writes the secret into
    # CI output and logs and reproduces the leak this guard exists to stop.
    is_literal = assignment is not None
    where = (src[: assignment.start()].count("\n") + 1) if assignment else 0
    assert not is_literal, (
        f"verify_backend.py must not assign a string literal to TEST_PASSWORD "
        f"(literal assignment at line {where}; value withheld)"
    )
    # Any residual occurrence of a known-committed secret, comments included.
    known = "pass" + "word" + "123"
    leaked = known in src.lower()
    assert not leaked, "a previously-committed secret reappeared in verify_backend.py (value withheld)"
    assert "VERIFY_BACKEND_PASSWORD" in src
    assert "VERIFY_BACKEND_EMAIL" in src
