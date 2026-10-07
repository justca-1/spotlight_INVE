"""Database engine and session management for Spotlight.

SQLite is not safe to share across threads. This module hands out a fresh
connection/session per call via `session_scope()`, which is the pattern
used by the dedicated DB worker thread (see app/services/db_worker.py).
Do not hold a single global Session open across threads.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.models.models import Base

DEFAULT_DB_PATH = Path.home() / ".spotlight" / "spotlight.db"


def get_engine(db_path: Path = DEFAULT_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False is safe here ONLY because every session is
    # opened, used, and closed within a single call on the DB worker thread.
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )


_engine = None
_SessionFactory = None


def _run_lightweight_migrations(engine) -> None:
    """create_all() only creates missing tables/indexes for tables that
    don't exist yet -- it never alters an existing table. For a project
    this size, hand-rolled checks are simpler than pulling in Alembic;
    revisit if the schema grows much further.
    """
    with engine.connect() as conn:
        existing_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(users)"))
        }
        if existing_cols and "status" not in existing_cols:
            # SQLAlchemy's Enum type stores the member NAME by default
            # (e.g. "ACTIVE"), not its display value ("Active") -- the
            # raw SQL here must match that or reads will raise a
            # LookupError when SQLAlchemy tries to map the stored string
            # back to a UserStatus member.
            conn.execute(
                text("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'ACTIVE'")
            )
            conn.execute(text("UPDATE users SET status = 'ACTIVE' WHERE status IS NULL"))
            conn.commit()

        # Added after a stress test showed filtered/unfiltered Inventory
        # queries degrading badly past ~50k items (full table scans on
        # owner_id/category_id/location_id/status). Unlike the column add
        # above, CREATE INDEX works directly on existing SQLite tables --
        # no table rebuild needed -- so this is safe to run unconditionally
        # every startup; IF NOT EXISTS makes it a no-op after the first run.
        # Names match what Column(index=True) generates on a fresh install,
        # so both paths converge on identical schema.
        for statement in (
            "CREATE INDEX IF NOT EXISTS ix_items_owner_id ON items (owner_id)",
            "CREATE INDEX IF NOT EXISTS ix_items_category_id ON items (category_id)",
            "CREATE INDEX IF NOT EXISTS ix_items_location_id ON items (location_id)",
            "CREATE INDEX IF NOT EXISTS ix_items_status ON items (status)",
        ):
            conn.execute(text(statement))
        conn.commit()

        # Same story as the users.status column above, but for accounts:
        # anyone who ran the version of the app that first introduced
        # login (before must_change_password existed) already has an
        # `accounts` table without this column. A brand-new install gets
        # it for free via create_all() above, since it's part of the
        # model from the start -- this block only fires for that one
        # upgrade path.
        account_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(accounts)"))
        }
        if account_cols and "must_change_password" not in account_cols:
            conn.execute(
                text("ALTER TABLE accounts ADD COLUMN must_change_password BOOLEAN DEFAULT 1")
            )
            conn.commit()

            # Don't just default every existing account to "must change" --
            # that would force a change on someone who already changed
            # their password under the previous version. Instead, check
            # whether each account's current password still verifies
            # against the known seeded default; only those still on it get
            # forced. Deferred import: auth_service imports session_scope
            # from this module, so importing it at module level here would
            # create a circular import.
            from app.services.auth_service import (
                DEFAULT_PASSWORD,
                DEFAULT_USERNAME,
                verify_password,
            )

            rows = conn.execute(
                text("SELECT id, username, password_hash FROM accounts")
            ).fetchall()
            for row in rows:
                account_id, username, password_hash = row[0], row[1], row[2]
                still_on_default = username == DEFAULT_USERNAME and verify_password(
                    DEFAULT_PASSWORD, password_hash
                )
                conn.execute(
                    text(
                        "UPDATE accounts SET must_change_password = :val WHERE id = :account_id"
                    ),
                    {"val": 1 if still_on_default else 0, "account_id": account_id},
                )
            conn.commit()


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    global _engine, _SessionFactory
    _engine = get_engine(db_path)
    Base.metadata.create_all(_engine)
    _run_lightweight_migrations(_engine)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    if _SessionFactory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
