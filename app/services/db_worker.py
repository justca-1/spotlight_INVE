"""Runs inventory queries on a background thread so the UI never blocks
on SQLite I/O. Pattern: a QObject worker moved to a QThread; requests go
in and results come back via signals, which Qt automatically marshals
across threads with a queued connection since sender and receiver live
on different threads.

For the MVP dataset sizes involved, queries are fast, but the pattern is
established here so it holds as data grows.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.services.item_service import FilterState, fetch_items


class InventoryQueryWorker(QObject):
    resultReady = Signal(object)  # ItemQueryResult
    errorRaised = Signal(str)

    @Slot(object)
    def run_query(self, filters: FilterState) -> None:
        try:
            result = fetch_items(filters)
            self.resultReady.emit(result)
        except Exception as exc:  # noqa: BLE001 - surface to UI, don't swallow
            self.errorRaised.emit(str(exc))


class InventoryQueryController(QObject):
    """Owns the worker thread and exposes a simple request/response API
    to the UI. Created and owned by the Inventory view; call shutdown()
    from the view's closeEvent/destructor path to stop the thread cleanly.
    """

    resultReady = Signal(object)  # ItemQueryResult
    errorRaised = Signal(str)
    _requestQuery = Signal(object)  # internal: UI thread -> worker thread

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._worker = InventoryQueryWorker()
        self._worker.moveToThread(self._thread)

        # Connections made while both objects still live on the main
        # thread are automatically promoted to queued connections once
        # the worker is moved, because Qt inspects thread affinity at
        # emit time, not at connect time.
        self._requestQuery.connect(self._worker.run_query)
        self._worker.resultReady.connect(self.resultReady)
        self._worker.errorRaised.connect(self.errorRaised)

        self._thread.start()

    def request(self, filters: FilterState) -> None:
        self._requestQuery.emit(filters)

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait()
