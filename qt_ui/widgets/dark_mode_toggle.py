"""
Dark Mode Toggle Switch Widget

A rectangular toggle switch with 'Darkmode' label for dark mode control.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, Property, QEasingCurve, QSize
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget


class DarkModeToggle(QWidget):
    """
    A rectangular toggle switch widget with 'Darkmode' label.

    Signals:
        toggled(bool): Emitted when the toggle state changes. True = dark mode on.
    """

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Toggle state
        self._checked = False

        # Animation position (0.0 = left/off, 1.0 = right/on)
        self._position = 0.0

        # Colors
        self._track_color_off = QColor(200, 200, 200)
        self._track_color_on = QColor(66, 133, 244)  # Nice blue
        self._thumb_color = QColor(255, 255, 255)
        self._border_color = QColor(140, 140, 140)
        self._text_color = QColor(60, 60, 60)

        # Dimensions
        self._track_width = 32
        self._track_height = 16
        self._thumb_width = 14
        self._thumb_height = 12
        self._padding = 2
        self._text_spacing = 6
        self._corner_radius = 3

        # Animation
        self._animation = QPropertyAnimation(self, b"position", self)
        self._animation.setDuration(120)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Calculate total width with label
        self._label_text = "Darkmode"
        self._calculate_size()

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        # Tooltip
        self._update_tooltip()

    def _calculate_size(self):
        """Calculate widget size based on text and toggle dimensions."""
        font = QFont()
        font.setPointSize(9)
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(font)
        text_width = metrics.horizontalAdvance(self._label_text)

        total_width = text_width + self._text_spacing + self._track_width + 8
        total_height = max(self._track_height, metrics.height()) + 4

        self.setFixedSize(total_width, total_height)
        self._text_width = text_width

    def sizeHint(self):
        return self.size()

    def minimumSizeHint(self):
        return self.sizeHint()

    def isChecked(self) -> bool:
        """Return whether dark mode is enabled."""
        return self._checked

    def setChecked(self, checked: bool):
        """Set the toggle state without emitting signal (for external sync)."""
        if checked != self._checked:
            self._checked = checked
            self._animate_to_position(1.0 if checked else 0.0)
            self._update_tooltip()

    def set_checked(self, checked: bool):
        """Alias for setChecked for signal connection."""
        self.setChecked(checked)

    def _get_position(self) -> float:
        return self._position

    def _set_position(self, pos: float):
        self._position = pos
        self.update()

    position = Property(float, _get_position, _set_position)

    def _animate_to_position(self, target: float):
        """Animate the thumb to the target position."""
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(target)
        self._animation.start()

    def _update_tooltip(self):
        """Update tooltip based on current state."""
        if self._checked:
            self.setToolTip("Switch to Light Mode")
        else:
            self.setToolTip("Switch to Dark Mode")

    def mousePressEvent(self, event):
        """Handle mouse press to toggle."""
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._animate_to_position(1.0 if self._checked else 0.0)
            self._update_tooltip()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Paint the toggle switch with label."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw label text
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)

        # Adjust text color based on dark mode state
        if self._checked:
            painter.setPen(QColor(220, 220, 220))
        else:
            painter.setPen(self._text_color)

        text_y = (self.height() + painter.fontMetrics().ascent() - painter.fontMetrics().descent()) // 2
        painter.drawText(4, text_y, self._label_text)

        # Calculate track position (after the text)
        track_x = self._text_width + self._text_spacing + 4
        track_y = (self.height() - self._track_height) // 2

        # Interpolate track color based on position
        track_color = self._interpolate_color(
            self._track_color_off,
            self._track_color_on,
            self._position
        )

        # Draw track (rectangular with small corner radius)
        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(
            track_x, track_y,
            self._track_width, self._track_height,
            self._corner_radius, self._corner_radius
        )

        # Calculate thumb position
        thumb_travel = self._track_width - self._thumb_width - 2 * self._padding
        thumb_x = track_x + self._padding + (thumb_travel * self._position)
        thumb_y = track_y + (self._track_height - self._thumb_height) // 2

        # Draw thumb (rectangular)
        painter.setBrush(QBrush(self._thumb_color))
        painter.setPen(QPen(self._border_color, 0.5))
        painter.drawRoundedRect(
            int(thumb_x), int(thumb_y),
            self._thumb_width, self._thumb_height,
            2, 2
        )

    def _interpolate_color(self, color1: QColor, color2: QColor, t: float) -> QColor:
        """Interpolate between two colors."""
        r = int(color1.red() + (color2.red() - color1.red()) * t)
        g = int(color1.green() + (color2.green() - color1.green()) * t)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * t)
        return QColor(r, g, b)
