"""Add/Edit dialog for a single inventory item.

DB reads for populating dropdowns and the save operation both go through
direct session queries; staying off the UI thread is not critical here
since these are trivial local reads/writes, but larger deployments could
route save() through the same worker pattern used by the Inventory view.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
)

from app.database.engine import session_scope
from app.models.models import Category, Item, ItemStatus, Location, MovementType, StockMovement, User


class ItemEditDialog(QDialog):
    def __init__(self, item_id: Optional[int] = None, parent=None) -> None:
        super().__init__(parent)
        self._item_id = item_id
        self.setWindowTitle("Edit Item" if item_id else "Add Item")
        self.setMinimumWidth(420)

        self.inventory_number_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.category_combo = QComboBox()
        self.owner_combo = QComboBox()
        self.location_combo = QComboBox()
        self.status_combo = QComboBox()
        for status in ItemStatus:
            self.status_combo.addItem(status.value, userData=status)
        self.serial_edit = QLineEdit()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setFixedHeight(80)

        form = QFormLayout()
        form.addRow("Inventory #", self.inventory_number_edit)
        form.addRow("Name", self.name_edit)
        form.addRow("Category", self.category_combo)
        form.addRow("Owner", self.owner_combo)
        form.addRow("Location", self.location_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Serial Number", self.serial_edit)
        form.addRow("Date Acquired", self.date_edit)
        form.addRow("Notes", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)

        self._load_reference_data()
        if item_id:
            self._load_item(item_id)

    def _load_reference_data(self) -> None:
        with session_scope() as session:
            categories = session.query(Category).order_by(Category.name).all()
            owners = session.query(User).order_by(User.name).all()
            locations = session.query(Location).order_by(Location.name).all()

            self.category_combo.addItem("— None —", userData=None)
            for c in categories:
                self.category_combo.addItem(c.name, userData=c.id)

            self.owner_combo.addItem("Unassigned", userData=None)
            for u in owners:
                self.owner_combo.addItem(u.name, userData=u.id)

            self.location_combo.addItem("— None —", userData=None)
            for l in locations:
                self.location_combo.addItem(l.name, userData=l.id)

    def _load_item(self, item_id: int) -> None:
        with session_scope() as session:
            item = session.get(Item, item_id)
            if item is None:
                return
            self.inventory_number_edit.setText(item.inventory_number)
            self.name_edit.setText(item.name)
            self._select_combo_data(self.category_combo, item.category_id)
            self._select_combo_data(self.owner_combo, item.owner_id)
            self._select_combo_data(self.location_combo, item.location_id)
            self._select_combo_data(self.status_combo, item.status)
            self.serial_edit.setText(item.serial_number or "")
            if item.date_acquired:
                self.date_edit.setDate(item.date_acquired)
            self.notes_edit.setPlainText(item.notes or "")

    @staticmethod
    def _select_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _on_save(self) -> None:
        inventory_number = self.inventory_number_edit.text().strip()
        name = self.name_edit.text().strip()

        if not inventory_number or not name:
            QMessageBox.warning(
                self, "Missing information", "Inventory # and Name are required."
            )
            return

        with session_scope() as session:
            # Uniqueness check on inventory_number (excluding self when editing)
            existing = (
                session.query(Item)
                .filter(Item.inventory_number == inventory_number)
                .first()
            )
            if existing and existing.id != self._item_id:
                QMessageBox.warning(
                    self,
                    "Duplicate Inventory #",
                    f"Inventory number '{inventory_number}' is already in use.",
                )
                return

            is_new_item = self._item_id is None

            if self._item_id:
                item = session.get(Item, self._item_id)
            else:
                item = Item()
                session.add(item)

            item.inventory_number = inventory_number
            item.name = name
            item.category_id = self.category_combo.currentData()
            item.owner_id = self.owner_combo.currentData()
            item.location_id = self.location_combo.currentData()
            item.status = self.status_combo.currentData()
            item.serial_number = self.serial_edit.text().strip() or None
            item.date_acquired = self.date_edit.date().toPython()
            item.notes = self.notes_edit.toPlainText().strip() or None

            if is_new_item:
                # First stock-in entry, backdated to whatever Date Acquired
                # was set to -- doesn't touch status (unlike a manual
                # Stock In on an existing item), since the person already
                # picked a status in this same form.
                session.flush()  # populates item.id for the FK below
                session.add(
                    StockMovement(
                        item_id=item.id,
                        movement_type=MovementType.IN,
                        movement_date=item.date_acquired or date.today(),
                        notes="Initial stock-in (item created)",
                    )
                )

        self.accept()
