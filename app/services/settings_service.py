"""Business logic for the Settings screen: managing categories and
locations. Both entities are structurally identical (id + unique name),
so this module handles them with shared helper functions parameterized
by model class, rather than duplicating the same logic twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type, Union

from sqlalchemy import func

from app.database.engine import session_scope
from app.models.models import Category, Item, Location

ReferenceModel = Union[Type[Category], Type[Location]]


@dataclass
class ReferenceRow:
    """Flat row: entity id/name plus how many items currently reference it."""

    id: int
    name: str
    item_count: int


def _fk_column(model: ReferenceModel):
    return Item.category_id if model is Category else Item.location_id


def fetch_reference_rows(model: ReferenceModel) -> list[ReferenceRow]:
    fk_column = _fk_column(model)
    with session_scope() as session:
        rows = (
            session.query(model.id, model.name, func.count(Item.id).label("item_count"))
            .outerjoin(Item, fk_column == model.id)
            .group_by(model.id)
            .order_by(model.name)
            .all()
        )
        return [ReferenceRow(id=r.id, name=r.name, item_count=r.item_count) for r in rows]


def create_reference(model: ReferenceModel, name: str) -> tuple[bool, str]:
    name = name.strip()
    if not name:
        return False, "Name cannot be empty."
    with session_scope() as session:
        exists = session.query(model).filter(model.name == name).first()
        if exists:
            return False, f'"{name}" already exists.'
        session.add(model(name=name))
    return True, "Created."


def rename_reference(model: ReferenceModel, entity_id: int, new_name: str) -> tuple[bool, str]:
    new_name = new_name.strip()
    if not new_name:
        return False, "Name cannot be empty."
    with session_scope() as session:
        duplicate = (
            session.query(model)
            .filter(model.name == new_name, model.id != entity_id)
            .first()
        )
        if duplicate:
            return False, f'"{new_name}" already exists.'
        entity = session.get(model, entity_id)
        if entity is None:
            return False, "Not found."
        entity.name = new_name
    return True, "Renamed."


def delete_reference(model: ReferenceModel, entity_id: int) -> tuple[bool, str]:
    """Refuses to delete a category/location still referenced by items,
    for the same reason delete_user refuses when a user still owns items:
    the FK column allows NULL but nothing here nulls it out automatically,
    so an unguarded delete would leave dangling references.
    """
    fk_column = _fk_column(model)
    label = "category" if model is Category else "location"
    with session_scope() as session:
        entity = session.get(model, entity_id)
        if entity is None:
            return False, "Not found."

        in_use = session.query(Item).filter(fk_column == entity_id).count()
        if in_use > 0:
            return (
                False,
                f'"{entity.name}" is still used by {in_use} item(s). '
                f"Reassign those items to a different {label} before deleting.",
            )

        session.delete(entity)
    return True, "Deleted."
