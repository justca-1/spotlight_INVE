"""Seed the database with sample data for development and first-run demo."""

from __future__ import annotations

import datetime

from app.database.engine import session_scope
from app.models.models import Category, Item, ItemStatus, Location, User, UserStatus


def seed_if_empty() -> None:
    with session_scope() as session:
        if session.query(User).first() is not None:
            return  # already seeded

        categories = {
            name: Category(name=name)
            for name in ["Electronics", "Furniture", "Software License", "Vehicle"]
        }
        locations = {
            name: Location(name=name)
            for name in ["Office A", "Office B", "Office C", "Warehouse"]
        }
        session.add_all(categories.values())
        session.add_all(locations.values())
        session.flush()

        users = {
            "John": User(
                name="John Doe", department="Engineering",
                contact="john@company.com", status=UserStatus.ACTIVE,
            ),
            "Maria": User(
                name="Maria Lopez", department="Design",
                contact="maria@company.com", status=UserStatus.ACTIVE,
            ),
            "Carlos": User(
                name="Carlos Reyes", department="IT",
                contact="carlos@company.com", status=UserStatus.ACTIVE,
            ),
        }
        session.add_all(users.values())
        session.flush()

        items = [
            Item(
                inventory_number="INV-001",
                name="Laptop",
                category=categories["Electronics"],
                owner=users["John"],
                location=locations["Office A"],
                status=ItemStatus.ACTIVE,
                serial_number="SN-928382",
                date_acquired=datetime.date(2026, 8, 10),
            ),
            Item(
                inventory_number="INV-002",
                name="Monitor",
                category=categories["Electronics"],
                owner=users["Maria"],
                location=locations["Office B"],
                status=ItemStatus.ACTIVE,
                serial_number="SN-114455",
                date_acquired=datetime.date(2026, 6, 2),
            ),
            Item(
                inventory_number="INV-003",
                name="Chair",
                category=categories["Furniture"],
                owner=users["John"],
                location=locations["Office A"],
                status=ItemStatus.AVAILABLE,
                date_acquired=datetime.date(2025, 12, 1),
            ),
            Item(
                inventory_number="INV-004",
                name="Printer",
                category=categories["Electronics"],
                owner=users["Carlos"],
                location=locations["Office C"],
                status=ItemStatus.MAINTENANCE,
                serial_number="SN-778812",
                date_acquired=datetime.date(2024, 3, 15),
            ),
        ]
        session.add_all(items)
