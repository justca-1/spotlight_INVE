"""Log a stock-in or stock-out event for a single item. Same dialog for
both directions -- only the title, button label, and which service
function gets called differ.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
)

from app.models.models import MovementType
from app.services.stock_service import log_stock_in, log_stock_out


class StockMovementDialog(QDialog):
    def __init__(self, item_id: int, item_name: str, movement_type: MovementType, parent=None) -> None:
        super().__init__(parent)
        self._item_id = item_id
        self._movement_type = movement_type

        is_in = movement_type == MovementType.IN
        self.setWindowTitle("Stock In" if is_in else "Stock Out")
        self.setMinimumWidth(360)

        subtitle = QLabel(f"{item_name}")
        subtitle.setObjectName("PanelTitle")

        hint = QLabel(
            "Marks this item Available again."
            if is_in
            else "Marks this item Archived (disposed)."
        )
        hint.setObjectName("SearchHint")
        hint.setWordWrap(True)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText(
            "e.g. purchased, returned from repair"
            if is_in
            else "e.g. sold, broken, lost, donated"
        )

        form = QFormLayout()
        form.addRow(subtitle)
        form.addRow(hint)
        form.addRow("Date", self.date_edit)
        form.addRow("Notes (optional)", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Stock In" if is_in else "Stock Out"
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.setLayout(form)

    def _on_save(self) -> None:
        movement_date = self.date_edit.date().toPython()
        notes = self.notes_edit.text().strip()

        if self._movement_type == MovementType.IN:
            success, message = log_stock_in(self._item_id, movement_date, notes)
        else:
            success, message = log_stock_out(self._item_id, movement_date, notes)

        if not success:
            QMessageBox.warning(self, "Couldn't save", message)
            return

        self.accept()
