"""Main application window: persistent sidebar + stacked content area.

All four screens (Dashboard, Inventory, Users, Settings) are fully
implemented and available to any logged-in account -- there's exactly one
account type (super admin), so no per-screen access restrictions apply.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import session
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.dashboard_view import DashboardView
from app.ui.inventory_view import InventoryView
from app.ui.settings_view import SettingsView
from app.ui.users_view import UsersView

NAV_ITEMS = ["Dashboard", "Inventory", "Users", "Settings"]


class MainWindow(QMainWindow):
    # Emitted when the person clicks Log Out (as opposed to closing the
    # window normally) -- main.py listens for this to loop back to the
    # login screen instead of exiting the app.
    logoutRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spotlight — Inventory Management")
        self.resize(1200, 720)
        self.logged_out = False

        self._info = session.get_current()

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(180)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for name in NAV_ITEMS:
            item = QListWidgetItem(name)
            self.sidebar.addItem(item)

        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView()
        self.stack.addWidget(self.dashboard_view)
        self.inventory_view = InventoryView()
        self.stack.addWidget(self.inventory_view)
        self.users_view = UsersView()
        self.stack.addWidget(self.users_view)
        self.settings_view = SettingsView()
        self.stack.addWidget(self.settings_view)

        self.sidebar.currentRowChanged.connect(self._on_nav_changed)
        self.sidebar.setCurrentRow(0)  # land on Dashboard now that it's built

        self.dashboard_view.navigateRequested.connect(self._on_dashboard_navigate)

        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(self.sidebar, 1)
        sidebar_layout.addWidget(self._build_account_footer())

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(sidebar_container)
        layout.addWidget(self.stack, 1)

        self.setCentralWidget(central)

    def _build_account_footer(self) -> QWidget:
        footer = QWidget()
        footer.setObjectName("AccountFooter")

        name_label = QLabel(self._info.username if self._info else "Guest")
        name_label.setObjectName("AccountName")

        role_label = QLabel("Super Admin")
        role_label.setObjectName("AccountRoleLabel")

        change_password_button = QPushButton("Change Password")
        change_password_button.setObjectName("LogoutButton")
        change_password_button.clicked.connect(self._on_change_password_clicked)

        logout_button = QPushButton("Log Out")
        logout_button.setObjectName("LogoutButton")
        logout_button.clicked.connect(self._on_logout_clicked)

        v = QVBoxLayout(footer)
        v.setContentsMargins(16, 12, 16, 16)
        v.setSpacing(2)
        v.addWidget(name_label)
        v.addWidget(role_label)
        v.addSpacing(8)
        v.addWidget(change_password_button)
        v.addWidget(logout_button)

        return footer

    def _on_change_password_clicked(self) -> None:
        if self._info is None:
            return
        dialog = ChangePasswordDialog(account_id=self._info.account_id, forced=False, parent=self)
        if dialog.exec():
            QMessageBox.information(self, "Password changed", "Your password has been updated.")

    def _on_logout_clicked(self) -> None:
        self.logged_out = True
        session.clear_current()
        self.logoutRequested.emit()
        self.close()

    def _on_nav_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        # Each screen's data can go stale from edits made on other
        # screens, so refresh on every visit rather than trying to track
        # cross-screen invalidation precisely. Inventory's search box
        # queries categories/locations by name at search time rather than
        # caching a dropdown list, so it never needs an explicit refresh
        # when Settings changes something.
        if index == 0:
            self.dashboard_view.refresh()
        if index == 2:
            self.users_view.refresh()
        if index == 3:
            self.settings_view.refresh()

    def _on_dashboard_navigate(self, target_index: int, inventory_query: str) -> None:
        """A Dashboard tile was clicked. Switch screens via the sidebar
        (so the normal _on_nav_changed refresh logic still runs), then, if
        headed to Inventory, drop the query straight into the search box --
        setText() fires textChanged, which the search box already wires up
        to re-run the query, so no extra refresh call is needed here.
        """
        self.sidebar.setCurrentRow(target_index)
        if target_index == 1:  # Inventory
            self.inventory_view.filter_bar.search_edit.setText(inventory_query)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.inventory_view.close()
        super().closeEvent(event)
