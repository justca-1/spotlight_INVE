"""SQLAlchemy ORM models for Spotlight inventory data."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ItemStatus(str, enum.Enum):
    ACTIVE = "Active"
    AVAILABLE = "Available"
    MAINTENANCE = "Maintenance"
    ARCHIVED = "Archived"


class UserStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Account(Base):
    """A login credential -- deliberately separate from User (which
    represents inventory owners like John/Maria/Carlos, not people who log
    into the app). An owner doesn't need to be able to log in, and someone
    who logs in doesn't need to own any inventory; conflating the two would
    force every owner to have a password or every account to own items.

    No role field: there's exactly one account type (super admin, full
    access to everything), so there's nothing to differentiate. If
    multiple permission tiers are wanted later, that's what a role column
    would be for -- deliberately left out for now rather than built and
    unused.
    """

    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    # True for the seeded default account until it's changed at least
    # once -- forces a password change on first login rather than
    # silently trusting a known, documented default forever.
    must_change_password = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Account id={self.id} username={self.username!r}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    department = Column(String(120), nullable=True)
    contact = Column(String(200), nullable=True)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE)
    created_at = Column(DateTime, server_default=func.now())

    items = relationship("Item", back_populates="owner")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} name={self.name!r}>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False, unique=True)

    items = relationship("Item", back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category id={self.id} name={self.name!r}>"


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)

    items = relationship("Item", back_populates="location")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Location id={self.id} name={self.name!r}>"


class MovementType(str, enum.Enum):
    IN = "In"
    OUT = "Out"


class StockMovement(Base):
    """A single stock-in or stock-out event for an item -- when it arrived
    or was disposed, and why. Kept as an append-only log (never edited or
    deleted) rather than a single "last movement" field on Item, so the
    full history survives even if an item goes out and comes back in
    multiple times.
    """

    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    movement_type = Column(Enum(MovementType), nullable=False)
    movement_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    item = relationship("Item", back_populates="movements")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<StockMovement item_id={self.item_id} type={self.movement_type} date={self.movement_date}>"


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    inventory_number = Column(String(40), nullable=False, unique=True)
    name = Column(String(160), nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)

    status = Column(Enum(ItemStatus), nullable=False, default=ItemStatus.AVAILABLE, index=True)
    serial_number = Column(String(120), nullable=True)
    date_acquired = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="items")
    owner = relationship("User", back_populates="items")
    location = relationship("Location", back_populates="items")
    movements = relationship(
        "StockMovement", back_populates="item", order_by="StockMovement.movement_date.desc()"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Item id={self.id} inventory_number={self.inventory_number!r}>"
