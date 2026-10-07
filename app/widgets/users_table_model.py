"""Table model backing the Users QTableView."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.services.user_service import UserRow

COLUMNS = ["Name", "Department", "Contact", "# Items", "Status"]


class UsersTableModel(QAbstractTableModel):
    def __init__(self, users: list[UserRow] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._users: list[UserRow] = users or []

    def user_at(self, row: int) -> UserRow | None:
        if 0 <= row < len(self._users):
            return self._users[row]
        return None

    def set_users(self, users: list[UserRow]) -> None:
        self.beginResetModel()
        self._users = users
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._users)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return section + 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        user = self._users[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return user.name
            if column == 1:
                return user.department or "—"
            if column == 2:
                return user.contact or "—"
            if column == 3:
                return str(user.item_count)
            if column == 4:
                return user.status.value if user.status else "—"

        return None
