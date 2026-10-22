"""Reset the support account password with an explicit runtime confirmation.

An earlier script could install a committed password hash. Its plaintext and
current validity are unknown. Removing that code neither rotates a credential
nor purges repository history.

Usage:
    cd backend
    Supply SUPPORT_PW_RESET_PASSWORD securely in the runtime environment.
    python reset_support_pw.py --confirm
"""
import argparse
import asyncio
import os
import sys

TARGET_EMAIL = "support@litinkai.com"
ENV_VAR = "SUPPORT_PW_RESET_PASSWORD"
FAILURE_MESSAGE = "Support password reset failed."


async def main() -> int:
    parser = argparse.ArgumentParser(description="Reset the support account password.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Confirms you intend to write to the live support row.",
    )
    args = parser.parse_args()

    if not args.confirm:
        print(
            "Refusing to run without --confirm: this writes to a live account.",
            file=sys.stderr,
        )
        return 2

    password = os.environ.get(ENV_VAR)
    if not password or not password.strip():
        print(
            f"Refusing to run: set {ENV_VAR} to the new password. "
            "The script intentionally has no built-in default.",
            file=sys.stderr,
        )
        return 2

    try:
        # Import lazily so import and --help need no application/DB configuration.
        from sqlalchemy import text
        from app.auth.utils import generate_password_hash
        from app.core.database import async_session

        hashed = generate_password_hash(password)
        async with async_session() as session:
            result = await session.exec(
                text(
                    'UPDATE "user" SET hashed_password = :h WHERE email = :e'
                ).bindparams(h=hashed, e=TARGET_EMAIL)
            )
            await session.commit()
            rowcount = getattr(result, "rowcount", None)
    except Exception:
        print(FAILURE_MESSAGE, file=sys.stderr)
        return 1

    print(f"updated {rowcount} row(s) for {TARGET_EMAIL}")
    return 0 if rowcount else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
