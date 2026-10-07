"""The login screen, shown before MainWindow. A modal QDialog rather than
a separate top-level window -- app/main.py blocks on exec() and only
proceeds to MainWindow if login succeeds.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app import session
from app.services.auth_service import authenticate


class LoginDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spotlight — Log In")
        self.setMinimumWidth(360)
        self.setModal(True)

        title = QLabel("Spotlight")
        title.setObjectName("ScreenTitle")

        subtitle = QLabel("Sign in to continue")
        subtitle.setObjectName("FilterLabel")

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username")

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.returnPressed.connect(self._on_login)

        # Enter in the username field should move to the password field,
        # not submit -- without this, Qt's default-button behavior (see
        # below) fires the Login button immediately with whatever the
        # password field currently contains, which is usually nothing.
        # This was a real bug found via an actual screenshot: someone
        # typed their username, pressed Enter out of habit, and got
        # "Enter a username and password" because the submit fired before
        # they ever typed the password.
        self.username_edit.returnPressed.connect(self.password_edit.setFocus)

        self.error_label = QLabel()
        self.error_label.setObjectName("CappedNotice")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        login_button = QPushButton("Log In")
        login_button.setObjectName("PrimaryButton")
        login_button.clicked.connect(self._on_login)
        # Deliberately NOT setDefault(True). A QPushButton is auto-
        # triggered by Enter in ANY focused field in the dialog by default
        # (via autoDefault, true even without setDefault) -- that's what
        # was causing Enter in the username field to submit the form
        # before the password was ever typed. Submission is handled
        # explicitly via the returnPressed connections above instead.
        login_button.setAutoDefault(False)

        # There's no account-management UI yet (see auth_service docstring),
        # so the only way in is the one seeded account. Shown directly
        # rather than buried in a README so it's actually discoverable at
        # the point someone needs it.
        hint = QLabel("First time? Default login: admin / admin123")
        hint.setObjectName("SearchHint")
        hint.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.username_edit)
        layout.addWidget(self.password_edit)
        layout.addWidget(self.error_label)
        layout.addWidget(login_button)
        layout.addSpacing(12)
        layout.addWidget(hint)

        self.username_edit.setFocus()

    def _on_login(self) -> None:
        result = authenticate(self.username_edit.text(), self.password_edit.text())
        if not result.success:
            self.error_label.setText(result.message)
            self.error_label.show()
            self.password_edit.clear()
            self.password_edit.setFocus()
            return

        session.set_current(
            session.SessionInfo(
                account_id=result.account_id,
                username=result.username,
                must_change_password=result.must_change_password,
            )
        )
        self.accept()
