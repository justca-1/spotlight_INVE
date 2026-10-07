"""Change-password dialog.

Used two ways: forced immediately after logging in with an account that
still has must_change_password set (see main.py's run_session), and
voluntarily any time via the "Change Password" button in the sidebar
footer (see main_window.py). Same dialog either way -- only the Cancel
button's label/behavior differs, since cancelling out of a forced change
needs to mean "log out", not "proceed with the default password anyway".
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
)

from app.services.auth_service import change_password


class ChangePasswordDialog(QDialog):
    def __init__(self, account_id: int, forced: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._account_id = account_id
        self.setWindowTitle("Change Password")
        self.setMinimumWidth(360)

        intro = None
        if forced:
            intro = QLabel(
                "You're still using the default password. Choose a new one to continue."
            )
            intro.setObjectName("SearchHint")
            intro.setWordWrap(True)

        self.current_password_edit = QLineEdit()
        self.current_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_edit.returnPressed.connect(self._on_save)

        self.error_label = QLabel()
        self.error_label.setObjectName("CappedNotice")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        form = QFormLayout()
        if intro is not None:
            form.addRow(intro)
        form.addRow("Current password", self.current_password_edit)
        form.addRow("New password", self.new_password_edit)
        form.addRow("Confirm new password", self.confirm_password_edit)
        form.addRow(self.error_label)

        # In forced mode, "Cancel" can't mean "keep using the app with the
        # default password" -- it has to log the person back out instead.
        # Relabeling makes that consequence explicit rather than
        # surprising.
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        if forced:
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Log Out Instead")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)
        self.current_password_edit.setFocus()

    def _on_save(self) -> None:
        current = self.current_password_edit.text()
        new = self.new_password_edit.text()
        confirm = self.confirm_password_edit.text()

        if new != confirm:
            self._show_error("New password and confirmation don't match.")
            return

        success, message = change_password(self._account_id, current, new)
        if not success:
            self._show_error(message)
            return

        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
