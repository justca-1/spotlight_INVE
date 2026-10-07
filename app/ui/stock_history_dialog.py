"""Read-only view of an item's full stock-in/stock-out history."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.stock_service import fetch_movements_for_item


class StockHistoryDialog(QDialog):
    def __init__(self, item_id: int, item_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Stock History — {item_name}")
        self.setMinimumSize(460, 420)

        title = QLabel(item_name)
        title.setObjectName("PanelTitle")

        movements = fetch_movements_for_item(item_id)

        table = QTableWidget(len(movements), 3)
        table.setHorizontalHeaderLabels(["Date", "Type", "Notes"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for row, movement in enumerate(movements):
            table.setItem(row, 0, QTableWidgetItem(movement.movement_date.isoformat()))
            type_item = QTableWidgetItem(movement.movement_type.value)
            table.setItem(row, 1, type_item)
            table.setItem(row, 2, QTableWidgetItem(movement.notes or ""))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        if not movements:
            empty = QLabel("No stock movements recorded yet.")
            empty.setObjectName("EmptyState")
            layout.addWidget(empty)
        else:
            layout.addWidget(table)
        layout.addWidget(buttons)
