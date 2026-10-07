"""Business logic for the Users screen. Kept Qt-free for testability,
mirroring item_service.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.database.engine import session_scope
from app.models.models import Item, User, UserStatus


@dataclass
class UserRow:
    """Flat, detached-safe row for the Users table: the ORM User plus a
    precomputed item count (avoids N+1 queries in the table model).
    """

    id: int
    name: str
    department: str | None
    contact: str | None
    status: UserStatus
    item_count: int


def fetch_users_with_item_counts() -> list[UserRow]:
    with session_scope() as session:
        rows = (
            session.query(
                User.id,
                User.name,
                User.department,
                User.contact,
                User.status,
                func.count(Item.id).label("item_count"),
            )
            .outerjoin(Item, Item.owner_id == User.id)
            .group_by(User.id)
            .order_by(User.name)
            .all()
        )
        return [
            UserRow(
                id=r.id,
                name=r.name,
                department=r.department,
                contact=r.contact,
                status=r.status,
                item_count=r.item_count,
            )
            for r in rows
        ]


def fetch_user_with_items(user_id: int) -> tuple[User | None, list[Item]]:
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            return None, []
        items = (
            session.query(Item)
            .options(joinedload(Item.category), joinedload(Item.location))
            .filter(Item.owner_id == user_id)
            .order_by(Item.inventory_number)
            .all()
        )
        return user, items


def delete_user(user_id: int) -> tuple[bool, str]:
    """Returns (success, message). Refuses to delete a user who still
    owns items, since Item.owner_id has no ON DELETE behavior configured
    at the DB level -- silently deleting the user would leave dangling
    references. Caller should prompt to reassign/unassign items first.
    """
    with session_scope() as session:
        user = session.get(User, user_id)
        if user is None:
            return False, "User not found."

        item_count = session.query(Item).filter(Item.owner_id == user_id).count()
        if item_count > 0:
            return (
                False,
                f"{user.name} still owns {item_count} item(s). "
                "Reassign or unassign those items before deleting this user.",
            )

        session.delete(user)
        return True, "User deleted."
