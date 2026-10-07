"""Global hover/press micro-interactions: a soft animated shadow "lift" on
buttons and stat tiles, applied via a single QApplication-level event
filter rather than wiring animation code into every widget/file
individually. Any QPushButton or StatTile gets this automatically just by
existing -- no per-instance setup needed anywhere else in the codebase.

Qt Style Sheets have no CSS-style `transition`, so a QSS :hover rule
changes state instantly. This animates a real Qt property instead
(QGraphicsDropShadowEffect's blurRadius/yOffset are both proper
Q_PROPERTYs) to get an actual smooth transition.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QWidget

from app.widgets.stat_tile import StatTile

_HOVER_DURATION_MS = 160
_PRESS_DURATION_MS = 90

_PURPLE_GLOW = QColor(139, 92, 246, 140)  # for #PrimaryButton
_NEUTRAL_GLOW = QColor(255, 255, 255, 45)  # generic buttons -- a soft
# light glow reads as elevation on a dark background; a black drop shadow
# (the light-mode default) is nearly invisible against near-black.

_IDLE_BLUR = 0.0
_HOVER_BLUR = 22.0
_PRESS_BLUR = 8.0
_IDLE_Y = 0.0
_HOVER_Y = 5.0
_PRESS_Y = 2.0


def _glow_color_for(widget: QWidget) -> QColor:
    if widget.objectName() == "PrimaryButton":
        return QColor(_PURPLE_GLOW)

    # StatTile carries its own accent color (set in StatTile.__init__) --
    # glowing in the tile's own color reads better and more intentionally
    # than one generic gray for every tile regardless of its meaning.
    accent = widget.property("accent")
    if accent:
        color = QColor(accent)
        color.setAlpha(140)
        return color

    return QColor(_NEUTRAL_GLOW)


class HoverLiftFilter(QObject):
    """Install once: app.installEventFilter(HoverLiftFilter(app))."""

    def _ensure_effect(self, widget: QWidget) -> QGraphicsDropShadowEffect | None:
        existing = widget.graphicsEffect()
        if getattr(widget, "_hover_lift_managed", False) and isinstance(
            existing, QGraphicsDropShadowEffect
        ):
            return existing
        if existing is not None:
            # Something else already owns this widget's graphics effect --
            # don't clobber it (Qt only allows one effect per widget).
            return None

        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setColor(_glow_color_for(widget))
        shadow.setBlurRadius(_IDLE_BLUR)
        shadow.setXOffset(0)
        shadow.setYOffset(_IDLE_Y)
        widget.setGraphicsEffect(shadow)
        widget._hover_lift_managed = True

        blur_anim = QPropertyAnimation(shadow, b"blurRadius", widget)
        blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        y_anim = QPropertyAnimation(shadow, b"yOffset", widget)
        y_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        widget._hover_blur_anim = blur_anim
        widget._hover_y_anim = y_anim

        return shadow

    def _animate(self, widget: QWidget, blur: float, y: float, duration: int) -> None:
        shadow = self._ensure_effect(widget)
        if shadow is None:
            return

        blur_anim = widget._hover_blur_anim
        blur_anim.stop()
        blur_anim.setDuration(duration)
        blur_anim.setStartValue(shadow.blurRadius())
        blur_anim.setEndValue(blur)
        blur_anim.start()

        y_anim = widget._hover_y_anim
        y_anim.stop()
        y_anim.setDuration(duration)
        y_anim.setStartValue(shadow.yOffset())
        y_anim.setEndValue(y)
        y_anim.start()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt override
        if isinstance(obj, (QPushButton, StatTile)):
            if not obj.isEnabled():
                return False

            event_type = event.type()
            if event_type == QEvent.Type.Enter:
                self._animate(obj, _HOVER_BLUR, _HOVER_Y, _HOVER_DURATION_MS)
            elif event_type == QEvent.Type.Leave:
                self._animate(obj, _IDLE_BLUR, _IDLE_Y, _HOVER_DURATION_MS)
            elif event_type == QEvent.Type.MouseButtonPress:
                self._animate(obj, _PRESS_BLUR, _PRESS_Y, _PRESS_DURATION_MS)
            elif event_type == QEvent.Type.MouseButtonRelease:
                # Return to the hover state rather than idle -- the cursor
                # is presumably still over the widget on release; Leave
                # fires separately once it actually moves off.
                self._animate(obj, _HOVER_BLUR, _HOVER_Y, _HOVER_DURATION_MS)

        return False  # never consume -- observe and animate, don't interfere
