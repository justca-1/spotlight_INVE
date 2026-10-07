"""A small, dependency-free horizontal bar chart.

Deliberately hand-painted with QPainter rather than pulling in QtCharts:
it's one chart, on one screen, and this way it inherits the app's exact
fonts/colors from style.qss instead of fighting a separate charting
theme system.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

BAR_COLORS = [
    "#8b5cf6",  # purple -- matches primary accent
    "#34d399",  # green
    "#fb923c",  # orange
    "#60a5fa",  # blue
    "#a78bfa",  # violet
    "#f472b6",  # pink
    "#5c5f70",  # overflow / "Other" bucket falls back to neutral gray
]

ROW_HEIGHT = 28
ROW_SPACING = 10
LABEL_WIDTH = 130
TOP_PADDING = 8
BOTTOM_PADDING = 8


class BarChart(QWidget):
    # Emits the clicked row's label (e.g. category name) so the parent
    # screen can wire it into navigation without needing to know this
    # widget's internal paint geometry.
    barClicked = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("BarChart")
        self._data: list[tuple[str, int]] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_data(self, data: list[tuple[str, int]]) -> None:
        """data: list of (label, count), any order -- displayed as given
        (callers should pre-sort, typically descending by count)."""
        self._data = data
        row_count = max(len(data), 1)
        self.setFixedHeight(TOP_PADDING + BOTTOM_PADDING + row_count * (ROW_HEIGHT + ROW_SPACING))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self._data:
            painter.setPen(QColor("#6d7086"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data yet")
            painter.end()
            return

        max_count = max(count for _, count in self._data) or 1
        chart_left = LABEL_WIDTH
        chart_right = self.width() - 50  # leave room for the count label
        chart_width = max(chart_right - chart_left, 10)

        label_font = QFont(painter.font())
        count_font = QFont(label_font)
        count_font.setBold(True)

        y = TOP_PADDING
        for i, (label, count) in enumerate(self._data):
            color = QColor(BAR_COLORS[i % len(BAR_COLORS)])

            # Label (left-aligned, truncated with ellipsis if too long)
            painter.setPen(QColor("#9a9db0"))
            painter.setFont(label_font)
            label_rect = QRectF(0, y, LABEL_WIDTH - 12, ROW_HEIGHT)
            elided = painter.fontMetrics().elidedText(
                label, Qt.TextElideMode.ElideRight, int(label_rect.width())
            )
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

            # Bar
            bar_width = (count / max_count) * chart_width
            bar_rect = QRectF(chart_left, y + 4, max(bar_width, 3), ROW_HEIGHT - 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(bar_rect, 4, 4)

            # Count label, right of the bar
            painter.setPen(QColor("#f2f2f7"))
            painter.setFont(count_font)
            count_rect = QRectF(chart_left + bar_width + 8, y, 40, ROW_HEIGHT)
            painter.drawText(count_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(count))

            y += ROW_HEIGHT + ROW_SPACING

        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() != Qt.MouseButton.LeftButton or not self._data:
            super().mousePressEvent(event)
            return

        click_y = event.position().y() if hasattr(event, "position") else event.y()
        row_span = ROW_HEIGHT + ROW_SPACING
        index = int((click_y - TOP_PADDING) // row_span)

        if 0 <= index < len(self._data):
            label, _count = self._data[index]
            self.barClicked.emit(label)

        super().mousePressEvent(event)
