"""Table model backing the Inventory QTableView.

Uses Qt's Model/View framework rather than manually populating a
QTableWidget, since the row count can reach into the thousands and
data changes on every filter/search change.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models.models import Item

COLUMNS = ["ID", "Item", "Category", "Owner", "Location", "Status"]


class InventoryTableModel(QAbstractTableModel):
    def __init__(self, items: list[Item] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._items: list[Item] = items or []

    # -- data access -------------------------------------------------

    def item_at(self, row: int) -> Item | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def set_items(self, items: list[Item]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    # -- QAbstractTableModel overrides --------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        item = self._items[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return item.inventory_number
            if column == 1:
                return item.name
            if column == 2:
                return item.category.name if item.category else "—"
            if column == 3:
                return item.owner.name if item.owner else "Unassigned"
            if column == 4:
                return item.location.name if item.location else "—"
            if column == 5:
                return item.status.value if item.status else "—"

        if role == Qt.ItemDataRole.TextAlignmentRole and column == 0:
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        return None
