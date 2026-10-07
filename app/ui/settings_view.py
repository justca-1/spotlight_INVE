"""The Settings screen: manage Categories and Locations side by side.
These are the two reference lists that feed the Inventory filter bar
and item dropdowns.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.models.models import Category, Location
from app.widgets.reference_list_panel import ReferenceListPanel


class SettingsView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsView")

        title = QLabel("Settings")
        title.setObjectName("ScreenTitle")

        self.categories_panel = ReferenceListPanel(
            "Categories", Category, "Category", parent=self
        )
        self.locations_panel = ReferenceListPanel(
            "Locations", Location, "Location", parent=self
        )

        panels_row = QHBoxLayout()
        panels_row.addWidget(self.categories_panel, 1)
        panels_row.addWidget(self.locations_panel, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(panels_row)

    def refresh(self) -> None:
        self.categories_panel.refresh()
        self.locations_panel.refresh()
