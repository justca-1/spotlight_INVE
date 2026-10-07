"""The Inventory search bar.

A single free-text box handles everything: plain words do a broad
OR-search across name/ID/serial/owner/category/location/status, and
field:value tokens (owner:, category:, location:, status:, id:) apply
precise AND filters -- the same combining power the old dropdown filters
had, without a UI element that gets unwieldy once owners/categories/
locations number in the dozens or hundreds. See item_service._parse_search_text
for the parsing logic.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget

from app.services.item_service import FilterState

SEARCH_PLACEHOLDER = (
    'Search anything, or filter with owner: category: location: status: id: '
    '(e.g. owner:maria status:active)'
)
SEARCH_HINT = (
    'Try:  owner:john   ·   category:electronics   ·   location:"office a"   ·   '
    'status:maintenance   ·   id:inv-001   — combine several, plus plain words'
)


class FilterBar(QWidget):
    filtersChanged = Signal(FilterState)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("FilterBar")

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(SEARCH_PLACEHOLDER)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._emit_filters)

        hint_label = QLabel(SEARCH_HINT)
        hint_label.setObjectName("SearchHint")
        hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.search_edit)
        layout.addWidget(hint_label)

    def current_filters(self) -> FilterState:
        return FilterState(search_text=self.search_edit.text())

    def _emit_filters(self, *_args) -> None:
        self.filtersChanged.emit(self.current_filters())
