"""The Users screen: table of owners with item counts, click-through to
each owner's item list, plus add/edit/delete.

Unlike Inventory, user list queries are cheap (no filtering, small table),
so this runs synchronously rather than through a background worker.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.services.user_service import delete_user, fetch_users_with_item_counts
from app.ui.user_detail_dialog import UserDetailDialog
from app.ui.user_edit_dialog import UserEditDialog
from app.widgets.users_table_model import UsersTableModel


class UsersView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("UsersView")

        title = QLabel("Users")
        title.setObjectName("ScreenTitle")

        self.add_button = QPushButton("+ Add User")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self._on_add_user)

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.add_button)

        self.table_model = UsersTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)

        self.view_button = QPushButton("View Items")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        for btn in (self.view_button, self.edit_button, self.delete_button):
            btn.setEnabled(False)
        self.view_button.clicked.connect(self._on_view_selected)
        self.edit_button.clicked.connect(self._on_edit_selected)
        self.delete_button.clicked.connect(self._on_delete_selected)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        actions_row.addWidget(self.view_button)
        actions_row.addWidget(self.edit_button)
        actions_row.addWidget(self.delete_button)

        self.empty_label = QLabel("No users yet. Add one to get started.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.hide()

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.table_view)
        layout.addWidget(self.empty_label)
        layout.addLayout(actions_row)

        self.refresh()

    def refresh(self) -> None:
        users = fetch_users_with_item_counts()
        self.table_model.set_users(users)
        self.empty_label.setVisible(len(users) == 0)
        self.table_view.setVisible(len(users) > 0)
        if self.table_view.selectionModel() is not None:
            self.table_view.selectionModel().selectionChanged.connect(
                self._on_selection_changed, type=self._unique_connection_type()
            )

    @staticmethod
    def _unique_connection_type():
        from PySide6.QtCore import Qt

        return Qt.ConnectionType.UniqueConnection

    def _on_selection_changed(self, *_args) -> None:
        has_selection = self.table_view.selectionModel().hasSelection()
        self.view_button.setEnabled(has_selection)
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _selected_user_id(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        row = self.table_model.user_at(indexes[0].row())
        return row.id if row else None

    def _on_row_double_clicked(self, index) -> None:
        row = self.table_model.user_at(index.row())
        if row:
            UserDetailDialog(row.id, parent=self).exec()

    def _on_view_selected(self) -> None:
        user_id = self._selected_user_id()
        if user_id is not None:
            UserDetailDialog(user_id, parent=self).exec()

    def _on_add_user(self) -> None:
        dialog = UserEditDialog(user_id=None, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_edit_selected(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        dialog = UserEditDialog(user_id=user_id, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_delete_selected(self) -> None:
        user_id = self._selected_user_id()
        if user_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete user",
            "Are you sure you want to delete this user?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        success, message = delete_user(user_id)
        if not success:
            QMessageBox.warning(self, "Cannot delete user", message)
            return
        self.refresh()
