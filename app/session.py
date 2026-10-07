"""Tracks who's currently logged in, for the lifetime of this process.

A plain module-level variable is enough here: Spotlight is a single-
process desktop app used by one person at a time, not a server handling
concurrent requests from different users -- there's no need for
thread-locals or request-scoped state.

No role/permission info: there's exactly one account type (super admin,
full access), so being logged in at all means full access.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionInfo:
    account_id: int
    username: str
    must_change_password: bool = False


_current: SessionInfo | None = None


def set_current(info: SessionInfo) -> None:
    global _current
    _current = info


def get_current() -> SessionInfo | None:
    return _current


def clear_current() -> None:
    global _current
    _current = None


def is_logged_in() -> bool:
    return _current is not None
