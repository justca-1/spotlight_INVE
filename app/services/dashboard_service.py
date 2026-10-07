"""Aggregate stats for the Dashboard screen. Kept Qt-free, same pattern
as the other services.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func

from app.database.engine import session_scope
from app.models.models import Category, Item, ItemStatus, User


@dataclass
class DashboardStats:
    total_items: int
    active: int
    available: int
    maintenance: int
    archived: int
    owners: int


def fetch_dashboard_stats() -> DashboardStats:
    with session_scope() as session:
        total_items = session.query(Item).count()
        active = session.query(Item).filter(Item.status == ItemStatus.ACTIVE).count()
        available = session.query(Item).filter(Item.status == ItemStatus.AVAILABLE).count()
        maintenance = session.query(Item).filter(Item.status == ItemStatus.MAINTENANCE).count()
        archived = session.query(Item).filter(Item.status == ItemStatus.ARCHIVED).count()
        owners = session.query(User).count()

        return DashboardStats(
            total_items=total_items,
            active=active,
            available=available,
            maintenance=maintenance,
            archived=archived,
            owners=owners,
        )


def fetch_items_by_category() -> list[tuple[str, int]]:
    """Item count per category, descending. Items with no category are
    grouped under "Uncategorized" -- this is the one breakdown the stat
    tiles don't already show (tiles cover status; this covers category),
    so it adds information rather than repeating it.
    """
    with session_scope() as session:
        rows = (
            session.query(Category.name, func.count(Item.id))
            .outerjoin(Item, Item.category_id == Category.id)
            .group_by(Category.id)
            .all()
        )
        uncategorized_count = (
            session.query(Item).filter(Item.category_id.is_(None)).count()
        )

        result = [(name, count) for name, count in rows if count > 0]
        if uncategorized_count:
            result.append(("Uncategorized", uncategorized_count))

        result.sort(key=lambda row: row[1], reverse=True)
        return result
