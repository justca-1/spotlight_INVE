"""The Dashboard screen: at-a-glance inventory stats, per the product plan.

Stats and the chart are cheap aggregate queries, so this runs
synchronously like Users and Settings rather than going through the
background query worker used by Inventory.

Each stat tile is clickable and jumps into a pre-filtered view -- e.g.
clicking "Maintenance" opens Inventory already searched for
status:maintenance, using the same field:value search syntax a person
could type by hand.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.services.dashboard_service import fetch_dashboard_stats, fetch_items_by_category
from app.widgets.bar_chart import BarChart
from app.widgets.stat_tile import StatTile

# Screen indices as ordered in MainWindow.NAV_ITEMS: Dashboard, Inventory,
# Users, Settings. Kept as plain constants here rather than importing
# MainWindow, since this widget shouldn't depend on its container.
NAV_INVENTORY = 1
NAV_USERS = 2


class DashboardView(QWidget):
    # (target_screen_index, inventory_search_query) -- query is only
    # meaningful when target_screen_index == NAV_INVENTORY.
    navigateRequested = Signal(int, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DashboardView")

        title = QLabel("Dashboard")
        title.setObjectName("ScreenTitle")

        self.total_tile = StatTile("Total Items", accent="#8b5cf6", glyph="Σ")
        self.active_tile = StatTile("Active", accent="#34d399", glyph="✓")
        self.available_tile = StatTile("Available", accent="#60a5fa", glyph="◇")
        self.maintenance_tile = StatTile("Maintenance", accent="#fb923c", glyph="⚙")
        self.owners_tile = StatTile("Owners", accent="#a78bfa", glyph="◎")

        self.total_tile.clicked.connect(lambda: self.navigateRequested.emit(NAV_INVENTORY, ""))
        self.active_tile.clicked.connect(
            lambda: self.navigateRequested.emit(NAV_INVENTORY, "status:active")
        )
        self.available_tile.clicked.connect(
            lambda: self.navigateRequested.emit(NAV_INVENTORY, "status:available")
        )
        self.maintenance_tile.clicked.connect(
            lambda: self.navigateRequested.emit(NAV_INVENTORY, "status:maintenance")
        )
        self.owners_tile.clicked.connect(lambda: self.navigateRequested.emit(NAV_USERS, ""))

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(self.total_tile, 0, 0)
        grid.addWidget(self.active_tile, 0, 1)
        grid.addWidget(self.available_tile, 0, 2)
        grid.addWidget(self.maintenance_tile, 0, 3)
        grid.addWidget(self.owners_tile, 0, 4)

        chart_title = QLabel("Items by Category")
        chart_title.setObjectName("PanelTitle")
        self.category_chart = BarChart()
        self.category_chart.barClicked.connect(self._on_category_bar_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addSpacing(24)
        layout.addWidget(chart_title)
        layout.addWidget(self.category_chart)
        layout.addStretch(1)

        self.refresh()

    def refresh(self) -> None:
        stats = fetch_dashboard_stats()
        self.total_tile.set_value(stats.total_items)
        self.active_tile.set_value(stats.active)
        self.available_tile.set_value(stats.available)
        self.maintenance_tile.set_value(stats.maintenance)
        self.owners_tile.set_value(stats.owners)

        self.category_chart.set_data(fetch_items_by_category())

    def _on_category_bar_clicked(self, label: str) -> None:
        if label == "Uncategorized":
            return  # no matching category: field value to filter by
        self.navigateRequested.emit(NAV_INVENTORY, f'category:"{label}"')
