"""A single stat tile: icon badge + label row, then a big number.

Clickable by default (emits `clicked`) so the Dashboard can wire each tile
to a pre-filtered Inventory/Users view -- e.g. clicking "Maintenance" jumps
to Inventory already filtered to status:maintenance.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class IconBadge(QWidget):
    """A small colored circle with a centered glyph, hand-painted rather
    than relying on an icon font/asset pack -- keeps the app dependency-free
    and matches the same custom-painting approach used by BarChart.
    """

    def __init__(self, glyph: str, accent: str, size: int = 34, parent=None) -> None:
        super().__init__(parent)
        self._glyph = glyph
        self._accent = QColor(accent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent)
        painter.drawEllipse(self.rect())

        font = QFont(painter.font())
        font.setBold(True)
        font.setPixelSize(15)  # pixel size, not point size -- avoids an
        # invalid-pointSizeF warning when the base font was set in px (see
        # bar_chart.py for the same fix applied there).
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._glyph)
        painter.end()


class StatTile(QWidget):
    clicked = Signal()

    def __init__(self, label: str, accent: str = "#8b5cf6", glyph: str = "•", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatTile")
        self.setProperty("accent", accent)
        # Plain QWidget subclasses ignore stylesheet background/border by
        # default; this attribute makes the #StatTile / #StatTile:hover
        # rules in style.qss actually paint.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        badge = IconBadge(glyph, accent)

        caption_label = QLabel(label)
        caption_label.setObjectName("StatCaption")

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        header_row.addWidget(badge)
        header_row.addWidget(caption_label, 1)

        self.value_label = QLabel("—")
        self.value_label.setObjectName("StatValue")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addLayout(header_row)
        layout.addWidget(self.value_label)

    def set_value(self, value: int) -> None:
        self.value_label.setText(f"{value:,}")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
