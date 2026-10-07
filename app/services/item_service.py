"""Business logic for querying and filtering inventory items.

Kept free of any Qt imports so it can be unit tested directly.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import contains_eager

from app.database.engine import session_scope
from app.models.models import Category, Item, ItemStatus, Location, StockMovement, User

# Past this many matching rows, stop materializing full ORM objects (each
# with 3 eagerly-loaded relationships) and tell the person to narrow their
# search instead. A stress test showed an unfiltered/broad search against
# 250k items took ~9 seconds and pulled the entire table into memory --
# this cap turns that into a near-constant-time query regardless of how
# large the underlying table gets.
DEFAULT_RESULT_LIMIT = 500

# field: -> canonical field name. Multiple aliases per field so people can
# type whichever word comes naturally (owner/user, category/cat, etc.)
FIELD_ALIASES = {
    "owner": "owner",
    "user": "owner",
    "category": "category",
    "cat": "category",
    "location": "location",
    "loc": "location",
    "status": "status",
    "id": "id",
    "inv": "id",
    "number": "id",
}


@dataclass
class ItemQueryResult:
    """What fetch_items() returns: the (possibly capped) page of items,
    plus the true total so the UI can tell the person "showing 500 of
    12,458 -- refine your search" rather than silently truncating.
    """

    items: list[Item]
    total_count: int
    limit: int

    @property
    def is_capped(self) -> bool:
        return self.total_count > len(self.items)


@dataclass
class FilterState:
    """The Inventory screen's entire filter state is just the search box
    text. Structured filtering (owner:, category:, status:, location:, id:)
    is parsed out of that text in fetch_items() rather than tracked as
    separate fields, since there's no longer any UI (dropdowns) that sets
    them directly.
    """

    search_text: str = ""

    def is_empty(self) -> bool:
        return not self.search_text.strip()


def _parse_search_text(search_text: str) -> tuple[dict[str, list[str]], list[str]]:
    """Split search text into structured field:value tokens (AND'd together,
    same effect as the old dropdown filters) and leftover free-text terms
    (OR'd across all fields, same as the plain search box).

    "owner:john status:active office" ->
        structured={'owner': ['john'], 'status': ['active']}, free=['office']

    Quoted values are supported for multi-word matches: location:"Office A".
    """
    try:
        tokens = shlex.split(search_text)
    except ValueError:
        # Unbalanced quotes -- fall back to naive whitespace splitting
        # rather than raising, since this is user-typed search text.
        tokens = search_text.split()

    structured: dict[str, list[str]] = {}
    free_terms: list[str] = []

    for token in tokens:
        field_raw, sep, value = token.partition(":")
        field = FIELD_ALIASES.get(field_raw.lower()) if sep else None
        if field and value:
            structured.setdefault(field, []).append(value)
        else:
            free_terms.append(token)

    return structured, free_terms


def fetch_items(
    filters: FilterState, limit: int | None = DEFAULT_RESULT_LIMIT
) -> ItemQueryResult:
    """Return items matching the given filters, with related entities eagerly
    loaded so the table model can read owner/category/location names without
    extra queries.

    Explicit outerjoins (rather than joinedload) are used so the same
    joined tables can be both filtered on and eager-loaded in one query via
    contains_eager.

    Results beyond `limit` are not materialized into ORM objects at all --
    only counted -- since a stress test showed row hydration (not the SQL
    execution itself) is what gets expensive on broad queries against a
    large table. Pass limit=None to fetch every matching row regardless of
    count -- used by CSV/print export, where truncating silently would be
    wrong (someone exporting expects everything that matches, not a UI-
    sized page of it).
    """
    with session_scope() as session:
        query = (
            session.query(Item)
            .outerjoin(Item.owner)
            .outerjoin(Item.category)
            .outerjoin(Item.location)
            .options(
                contains_eager(Item.owner),
                contains_eager(Item.category),
                contains_eager(Item.location),
            )
        )

        structured, free_terms = _parse_search_text(filters.search_text)

        for value in structured.get("owner", []):
            query = query.filter(User.name.ilike(f"%{value}%"))
        for value in structured.get("category", []):
            query = query.filter(Category.name.ilike(f"%{value}%"))
        for value in structured.get("location", []):
            query = query.filter(Location.name.ilike(f"%{value}%"))
        for value in structured.get("id", []):
            query = query.filter(Item.inventory_number.ilike(f"%{value}%"))
        for value in structured.get("status", []):
            # ItemStatus.value ("Active", "Maintenance", ...) isn't a real
            # column, so it can't be matched with ilike at the DB level --
            # resolve it in Python and fold in an IN clause instead.
            term_lower = value.lower()
            matches = [s for s in ItemStatus if term_lower in s.value.lower()]
            if not matches:
                return ItemQueryResult(items=[], total_count=0, limit=limit or 0)
            query = query.filter(Item.status.in_(matches))

        if free_terms:
            free_text = " ".join(free_terms)
            like = f"%{free_text}%"

            conditions = [
                Item.name.ilike(like),
                Item.inventory_number.ilike(like),
                Item.serial_number.ilike(like),
                User.name.ilike(like),
                Category.name.ilike(like),
                Location.name.ilike(like),
            ]

            term_lower = free_text.lower()
            matching_statuses = [
                status for status in ItemStatus if term_lower in status.value.lower()
            ]
            if matching_statuses:
                conditions.append(Item.status.in_(matching_statuses))

            query = query.filter(or_(*conditions))

        # COUNT first -- this doesn't hydrate ORM objects, so it stays cheap
        # even when the filter matches a large fraction of the table.
        total_count = query.count()

        query = query.order_by(Item.inventory_number)
        if limit is not None:
            query = query.limit(limit)
        items = query.all()

        # Detach-safe: expire_on_commit=False on the session factory means
        # these objects remain usable after the session closes.
        return ItemQueryResult(items=items, total_count=total_count, limit=limit or total_count)


def delete_item(item_id: int) -> None:
    with session_scope() as session:
        item = session.get(Item, item_id)
        if item is not None:
            # StockMovement rows belong to this specific item (not shared
            # reference data like a category), so they're cleaned up
            # alongside it rather than blocking the delete.
            session.query(StockMovement).filter(StockMovement.item_id == item_id).delete()
            session.delete(item)
