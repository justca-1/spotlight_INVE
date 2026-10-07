"""A reusable panel for managing a single reference list (categories or
locations): name + item-count list, with add/rename/delete. Used twice
by SettingsView with a different model/title each time, so the entity
type stays a parameter rather than two near-identical widget classes.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.settings_service import (
    create_reference,
    delete_reference,
    fetch_reference_rows,
    rename_reference,
)


class ReferenceListPanel(QWidget):
    def __init__(self, title: str, model, singular_label: str, parent=None) -> None:
        super().__init__(parent)
        self._model = model
        self._singular_label = singular_label

        heading = QLabel(title)
        heading.setObjectName("PanelTitle")

        self.add_button = QPushButton(f"+ Add {singular_label}")
        self.add_button.clicked.connect(self._on_add)

        header_row = QHBoxLayout()
        header_row.addWidget(heading)
        header_row.addStretch(1)
        header_row.addWidget(self.add_button)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "# Items"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        self.rename_button = QPushButton("Rename")
        self.delete_button = QPushButton("Delete")
        self.rename_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.rename_button.clicked.connect(self._on_rename)
        self.delete_button.clicked.connect(self._on_delete)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        actions_row.addWidget(self.rename_button)
        actions_row.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.table)
        layout.addLayout(actions_row)

        self.refresh()

    def refresh(self) -> None:
        rows = fetch_reference_rows(self._model)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name_item = QTableWidgetItem(row.name)
            name_item.setData(Qt.ItemDataRole.UserRole, row.id)
            count_item = QTableWidgetItem(str(row.item_count))
            self.table.setItem(r, 0, name_item)
            self.table.setItem(r, 1, count_item)

    def _selected_row(self):
        items = self.table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        name_item = self.table.item(row, 0)
        return name_item.data(Qt.ItemDataRole.UserRole), name_item.text()

    def _on_selection_changed(self) -> None:
        has_selection = bool(self.table.selectedItems())
        self.rename_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _on_add(self) -> None:
        text, ok = QInputDialog.getText(self, f"Add {self._singular_label}", "Name:")
        if not ok:
            return
        success, message = create_reference(self._model, text)
        if not success:
            QMessageBox.warning(self, "Could not add", message)
            return
        self.refresh()

    def _on_rename(self) -> None:
        selected = self._selected_row()
        if selected is None:
            return
        entity_id, current_name = selected
        text, ok = QInputDialog.getText(
            self, f"Rename {self._singular_label}", "Name:", text=current_name
        )
        if not ok:
            return
        success, message = rename_reference(self._model, entity_id, text)
        if not success:
            QMessageBox.warning(self, "Could not rename", message)
            return
        self.refresh()

    def _on_delete(self) -> None:
        selected = self._selected_row()
        if selected is None:
            return
        entity_id, current_name = selected
        confirm = QMessageBox.question(
            self,
            f"Delete {self._singular_label}",
            f'Delete "{current_name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        success, message = delete_reference(self._model, entity_id)
        if not success:
            QMessageBox.warning(self, "Cannot delete", message)
            return
        self.refresh()
