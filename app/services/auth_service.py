"""Password hashing and login verification.

Uses Python's built-in hashlib.pbkdf2_hmac rather than a third-party
library like bcrypt/argon2-cffi. Both would work, but adding a dependency
that needs a native wheel is exactly the kind of thing that's been
tripping up this particular install (missing pip, wrong venv, PySide6
version pins) -- pbkdf2_hmac is stdlib, no install required, and is still
a NIST-recommended algorithm for password hashing.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from app.database.engine import session_scope
from app.models.models import Account

PBKDF2_ITERATIONS = 260_000
_ALGO = "pbkdf2_sha256"

# There's exactly one account type -- a single super-admin login gating
# the whole app. No roles/permissions to differentiate.
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{_ALGO}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations_str, salt_hex, digest_hex = stored_hash.split("$")
        if algo != _ALGO:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        iterations = int(iterations_str)
    except (ValueError, AttributeError):
        return False  # malformed hash -- fail closed, not open

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    # Constant-time comparison so a failed login can't be timed to leak
    # how many leading bytes of the hash matched.
    return hmac.compare_digest(actual, expected)


@dataclass
class AuthResult:
    success: bool
    account_id: int | None = None
    username: str | None = None
    must_change_password: bool = False
    message: str = ""


def authenticate(username: str, password: str) -> AuthResult:
    username = username.strip()
    if not username or not password:
        return AuthResult(False, message="Enter a username and password.")

    with session_scope() as session:
        account = session.query(Account).filter(Account.username == username).first()
        if account is None or not verify_password(password, account.password_hash):
            # Deliberately identical message for "no such user" and "wrong
            # password" -- distinguishing them tells an attacker which
            # usernames exist.
            return AuthResult(False, message="Incorrect username or password.")

        return AuthResult(
            success=True,
            account_id=account.id,
            username=account.username,
            must_change_password=account.must_change_password,
        )


def change_password(account_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
    """Verifies the current password before allowing a change (even in the
    forced first-login flow) so a session that was somehow left open can't
    be used to silently take over the account. Clears must_change_password
    on success.
    """
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."
    if new_password == current_password:
        return False, "New password must be different from your current password."

    with session_scope() as session:
        account = session.get(Account, account_id)
        if account is None:
            return False, "Account not found."
        if not verify_password(current_password, account.password_hash):
            return False, "Current password is incorrect."

        account.password_hash = hash_password(new_password)
        account.must_change_password = False

    return True, "Password changed."


def seed_accounts_if_empty() -> None:
    """Creates the single starter account on first run. There's no account
    management UI yet (no way to create another account or change this
    password from within the app), so this default is the only way in --
    change it directly in the database if that matters for your use case
    before relying on this for anything sensitive.
    """
    with session_scope() as session:
        if session.query(Account).first() is not None:
            return
        session.add(
            Account(
                username=DEFAULT_USERNAME,
                password_hash=hash_password(DEFAULT_PASSWORD),
                must_change_password=True,
            )
        )
