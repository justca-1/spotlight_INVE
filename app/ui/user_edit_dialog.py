"""Add/Edit dialog for a User (owner)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from app.database.engine import session_scope
from app.models.models import User, UserStatus


class UserEditDialog(QDialog):
    def __init__(self, user_id: Optional[int] = None, parent=None) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self.setWindowTitle("Edit User" if user_id else "Add User")
        self.setMinimumWidth(380)

        self.name_edit = QLineEdit()
        self.department_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        self.status_combo = QComboBox()
        for status in UserStatus:
            self.status_combo.addItem(status.value, userData=status)

        form = QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Department", self.department_edit)
        form.addRow("Contact", self.contact_edit)
        form.addRow("Status", self.status_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)

        if user_id:
            self._load_user(user_id)

    def _load_user(self, user_id: int) -> None:
        with session_scope() as session:
            user = session.get(User, user_id)
            if user is None:
                return
            self.name_edit.setText(user.name)
            self.department_edit.setText(user.department or "")
            self.contact_edit.setText(user.contact or "")
            idx = self.status_combo.findData(user.status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)

    def _on_save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing information", "Name is required.")
            return

        with session_scope() as session:
            if self._user_id:
                user = session.get(User, self._user_id)
            else:
                user = User()
                session.add(user)

            user.name = name
            user.department = self.department_edit.text().strip() or None
            user.contact = self.contact_edit.text().strip() or None
            user.status = self.status_combo.currentData()

        self.accept()
