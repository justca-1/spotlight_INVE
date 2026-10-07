"""The Inventory screen: filter bar + table + add/edit/delete/stock/export
actions.

Query execution runs on a background thread via InventoryQueryController
so filtering/searching never blocks the UI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.models.models import MovementType
from app.services.db_worker import InventoryQueryController
from app.services.export_service import build_html_report, export_to_csv, fetch_items_for_export
from app.services.item_service import FilterState, delete_item
from app.ui.item_edit_dialog import ItemEditDialog
from app.ui.stock_history_dialog import StockHistoryDialog
from app.ui.stock_movement_dialog import StockMovementDialog
from app.widgets.filter_bar import FilterBar
from app.widgets.inventory_table_model import InventoryTableModel


class InventoryView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("InventoryView")

        # -- Header row: title + Export + Add buttons --
        title = QLabel("Inventory")
        title.setObjectName("ScreenTitle")

        self.export_button = QPushButton("Export")
        self.export_button.setMenu(self._build_export_menu())

        self.add_button = QPushButton("+ Add Item")
        self.add_button.setObjectName("PrimaryButton")
        self.add_button.clicked.connect(self._on_add_item)

        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.export_button)
        header_row.addWidget(self.add_button)

        # -- Filter bar --
        self.filter_bar = FilterBar()
        self.filter_bar.filtersChanged.connect(self._on_filters_changed)

        # -- Table --
        self.table_model = InventoryTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)

        # -- Row action buttons --
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.stock_in_button = QPushButton("Stock In")
        self.stock_out_button = QPushButton("Stock Out")
        self.history_button = QPushButton("History")
        for btn in (
            self.edit_button,
            self.delete_button,
            self.stock_in_button,
            self.stock_out_button,
            self.history_button,
        ):
            btn.setEnabled(False)
        self.edit_button.clicked.connect(self._on_edit_selected)
        self.delete_button.clicked.connect(self._on_delete_selected)
        self.stock_in_button.clicked.connect(self._on_stock_in_selected)
        self.stock_out_button.clicked.connect(self._on_stock_out_selected)
        self.history_button.clicked.connect(self._on_history_selected)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        actions_row.addWidget(self.history_button)
        actions_row.addWidget(self.stock_in_button)
        actions_row.addWidget(self.stock_out_button)
        actions_row.addWidget(self.edit_button)
        actions_row.addWidget(self.delete_button)

        self.empty_label = QLabel("No items match the current filters.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.hide()

        # Shown when a query matches more rows than DEFAULT_RESULT_LIMIT --
        # see item_service.fetch_items(). Only the visible page is ever
        # loaded, so this is the person's cue that there's more data than
        # they're seeing and how to narrow it down. Export ignores this
        # cap entirely (see export_service.fetch_items_for_export).
        self.capped_label = QLabel()
        self.capped_label.setObjectName("CappedNotice")
        self.capped_label.hide()

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.filter_bar)
        layout.addWidget(self.capped_label)
        layout.addWidget(self.table_view)
        layout.addWidget(self.empty_label)
        layout.addLayout(actions_row)

        # -- Background query controller --
        self.query_controller = InventoryQueryController(self)
        self.query_controller.resultReady.connect(self._on_results_ready)
        self.query_controller.errorRaised.connect(self._on_query_error)

        self.refresh()

    # -- lifecycle -----------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.query_controller.shutdown()
        super().closeEvent(event)

    # -- data loading ----------------------------------------------------

    def refresh(self) -> None:
        self.query_controller.request(self.filter_bar.current_filters())

    def _on_filters_changed(self, filters: FilterState) -> None:
        self.query_controller.request(filters)

    def _on_results_ready(self, result) -> None:
        self.table_model.set_items(result.items)
        self.empty_label.setVisible(len(result.items) == 0)
        self.table_view.setVisible(len(result.items) > 0)

        if result.is_capped:
            self.capped_label.setText(
                f"Showing {len(result.items):,} of {result.total_count:,} matching items — "
                "refine your search to narrow the results."
            )
            self.capped_label.show()
        else:
            self.capped_label.hide()

        if self.table_view.selectionModel() is not None:
            self.table_view.selectionModel().selectionChanged.connect(
                self._on_selection_changed, Qt.ConnectionType.UniqueConnection
            )

    def _on_query_error(self, message: str) -> None:
        QMessageBox.critical(self, "Failed to load inventory", message)

    # -- selection / row actions -----------------------------------------

    def _on_selection_changed(self, *_args) -> None:
        has_selection = self.table_view.selectionModel().hasSelection()
        for btn in (
            self.edit_button,
            self.delete_button,
            self.stock_in_button,
            self.stock_out_button,
            self.history_button,
        ):
            btn.setEnabled(has_selection)

    def _selected_item(self):
        indexes = self.table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        return self.table_model.item_at(indexes[0].row())

    def _selected_item_id(self):
        item = self._selected_item()
        return item.id if item else None

    def _on_row_double_clicked(self, index) -> None:
        item = self.table_model.item_at(index.row())
        if item:
            self._open_edit_dialog(item.id)

    def _on_edit_selected(self) -> None:
        item_id = self._selected_item_id()
        if item_id is not None:
            self._open_edit_dialog(item_id)

    def _on_add_item(self) -> None:
        self._open_edit_dialog(None)

    def _open_edit_dialog(self, item_id) -> None:
        dialog = ItemEditDialog(item_id=item_id, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_delete_selected(self) -> None:
        item_id = self._selected_item_id()
        if item_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete item",
            "Are you sure you want to delete this item? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            delete_item(item_id)
            self.refresh()

    # -- stock in/out/history ---------------------------------------------

    def _on_stock_in_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        dialog = StockMovementDialog(item.id, item.name, MovementType.IN, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_stock_out_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        dialog = StockMovementDialog(item.id, item.name, MovementType.OUT, parent=self)
        if dialog.exec():
            self.refresh()

    def _on_history_selected(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        StockHistoryDialog(item.id, item.name, parent=self).exec()

    # -- export -------------------------------------------------------------

    def _build_export_menu(self) -> QMenu:
        menu = QMenu(self)

        csv_action = QAction("Export to CSV...", self)
        csv_action.triggered.connect(self._on_export_csv)
        menu.addAction(csv_action)

        pdf_action = QAction("Save as PDF...", self)
        pdf_action.triggered.connect(self._on_export_pdf)
        menu.addAction(pdf_action)

        print_action = QAction("Print...", self)
        print_action.triggered.connect(self._on_print)
        menu.addAction(print_action)

        return menu

    def _current_export_items(self):
        """Exports respect whatever's currently typed in the search box
        (same filters as the visible table), but never the 500-row UI cap
        -- see export_service.fetch_items_for_export.
        """
        return fetch_items_for_export(self.filter_bar.current_filters())

    def _on_export_csv(self) -> None:
        items = self._current_export_items()
        if not items:
            QMessageBox.information(self, "Nothing to export", "No items match the current search.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export to CSV", "spotlight_inventory.csv", "CSV Files (*.csv)"
        )
        if not filepath:
            return

        try:
            export_to_csv(items, filepath)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        QMessageBox.information(self, "Export complete", f"Saved {len(items)} item(s) to:\n{filepath}")

    def _build_report_document(self, items) -> QTextDocument:
        html = build_html_report(items)
        document = QTextDocument()
        document.setHtml(html)
        return document

    def _on_export_pdf(self) -> None:
        items = self._current_export_items()
        if not items:
            QMessageBox.information(self, "Nothing to export", "No items match the current search.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save as PDF", "spotlight_inventory.pdf", "PDF Files (*.pdf)"
        )
        if not filepath:
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filepath)

        document = self._build_report_document(items)
        document.print_(printer)

        QMessageBox.information(self, "Export complete", f"Saved {len(items)} item(s) to:\n{filepath}")

    def _on_print(self) -> None:
        items = self._current_export_items()
        if not items:
            QMessageBox.information(self, "Nothing to print", "No items match the current search.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return

        document = self._build_report_document(items)
        document.print_(printer)
