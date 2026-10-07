"""Stock in/out movement logging: when an item entered inventory and when
it was disposed. Kept Qt-free, same pattern as the other services.
"""

from __future__ import annotations

import datetime

from app.database.engine import session_scope
from app.models.models import Item, ItemStatus, MovementType, StockMovement


def log_stock_in(
    item_id: int, movement_date: datetime.date, notes: str | None = None
) -> tuple[bool, str]:
    """Records an In movement. If the item is currently Archived, brings it
    back to Available -- clicking "Stock In" on a disposed item is the
    explicit signal that it's back in service. Does NOT touch status for
    an item that isn't archived (e.g. the automatic log entry created when
    a new item is added -- that shouldn't silently override whatever
    status the person picked in the Add Item form).
    """
    with session_scope() as session:
        item = session.get(Item, item_id)
        if item is None:
            return False, "Item not found."

        session.add(
            StockMovement(
                item_id=item_id,
                movement_type=MovementType.IN,
                movement_date=movement_date,
                notes=notes or None,
            )
        )

        if item.status == ItemStatus.ARCHIVED:
            item.status = ItemStatus.AVAILABLE

    return True, "Stock in recorded."


def log_stock_out(
    item_id: int, movement_date: datetime.date, notes: str | None = None
) -> tuple[bool, str]:
    """Records an Out movement and marks the item Archived -- this is the
    "proper" disposal path (dated, with a reason), as opposed to just
    changing the status dropdown quietly in the edit dialog.
    """
    with session_scope() as session:
        item = session.get(Item, item_id)
        if item is None:
            return False, "Item not found."

        session.add(
            StockMovement(
                item_id=item_id,
                movement_type=MovementType.OUT,
                movement_date=movement_date,
                notes=notes or None,
            )
        )
        item.status = ItemStatus.ARCHIVED

    return True, "Stock out recorded."


def fetch_movements_for_item(item_id: int) -> list[StockMovement]:
    with session_scope() as session:
        return (
            session.query(StockMovement)
            .filter(StockMovement.item_id == item_id)
            .order_by(StockMovement.movement_date.desc(), StockMovement.id.desc())
            .all()
        )
