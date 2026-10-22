"""Reset the support account password.

KAN-499: this script previously shipped a literal ``$argon2id$...`` hash and
wrote it straight to the live support@litinkai.com row. A committed hash is a
committed credential - anyone with repo access could authenticate as support,
and rotating the password in the database could never revoke the literal
because the literal is only invalid once the row no longer matches it.

Now the script carries no credential at all. It reads the new password from
the environment, hashes it at runtime with the application's own hasher, and
requires an explicit confirmation flag because it writes to a live account.

Usage:
    SUPPORT_PW_RESET_PASSWORD=... python -m backend.reset_support_pw --confirm
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import text

TARGET_EMAIL = "support@litinkai.com"
ENV_VAR = "SUPPORT_PW_RESET_PASSWORD"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Reset the support account password.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Confirms you intend to write to the live support row.",
    )
    parser.add_argument(
        "--email",
        default=TARGET_EMAIL,
        help=f"Account to update (default: {TARGET_EMAIL}).",
    )
    args = parser.parse_args()

    if not args.confirm:
        print(
            "Refusing to run without --confirm: this writes to a live account.",
            file=sys.stderr,
        )
        return 2

    password = os.environ.get(ENV_VAR)
    if not password:
        print(
            f"Refusing to run: set {ENV_VAR} to the new password. "
            "The script intentionally has no built-in default.",
            file=sys.stderr,
        )
        return 2

    # Imported lazily so --help works without app settings/bindings.
    from app.auth.utils import generate_password_hash
    from app.core.database import async_session

    hashed = generate_password_hash(password)

    async with async_session() as s:
        r = await s.exec(
            text(
                'UPDATE "user" SET hashed_password = :h WHERE email = :e'
            ).bindparams(h=hashed, e=args.email)
        )
        await s.commit()
        rowcount = getattr(r, "rowcount", None)

    # Never print the password or the hash; only whether a row moved.
    print(f"updated {rowcount} row(s) for {args.email}")
    return 0 if rowcount else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
