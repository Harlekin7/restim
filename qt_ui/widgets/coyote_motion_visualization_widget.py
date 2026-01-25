"""
Coyote Motion Visualization Widget.

Displays a vertical bar representing the funscript position (Alpha axis),
with a moving green bar showing the current position. "Top" and "Bottom" labels
indicate the stroke position extremes.

Only visible when in Coyote Motion Algorithm mode.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPainter

from qt_ui.theme_manager import ThemeManager


class CoyoteMotionVisualizationWidget(QGraphicsView):
    """
    A QGraphicsView that displays a vertical bar for Motion Algorithm position.

    Visual layout: "Top" label at top, "Bottom" label at bottom.
    The green bar moves vertically based on the Alpha axis position (0 to 1).
    Position 0 = Bottom, Position 1 = Top.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self._update_background_brush()

        # Connect to theme changes
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)

        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHint(QPainter.Antialiasing, True)

        # Coordinate system: vertical range
        self._bar_width = 40
        self._bar_height = 160
        self._position_bar_height = 8  # Height of the green position indicator

        # Create the visualization elements
        self._create_outline()
        self._create_labels()
        self._create_position_bar()

        self.last_position = None

    def _create_outline(self):
        """Create the outer rectangle frame."""
        pen = QPen(ThemeManager.instance().get_color('graphics_line'))
        pen.setWidth(2)

        # Main rectangle outline
        self.outline_rect = QGraphicsRectItem(
            -self._bar_width / 2, -self._bar_height / 2,
            self._bar_width, self._bar_height
        )
        self.outline_rect.setPen(pen)
        self.outline_rect.setBrush(Qt.NoBrush)
        self.scene.addItem(self.outline_rect)

    def _create_labels(self):
        """Create Top and Bottom labels."""
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)

        # Top label (above the bar)
        self.label_top = QGraphicsTextItem("Top")
        self.label_top.setFont(font)
        self.label_top.setDefaultTextColor(ThemeManager.instance().get_color('text_secondary'))
        # Center the label above the bar
        text_width = self.label_top.boundingRect().width()
        self.label_top.setPos(-text_width / 2, -self._bar_height / 2 - 25)
        self.scene.addItem(self.label_top)

        # Bottom label (below the bar)
        self.label_bottom = QGraphicsTextItem("Bottom")
        self.label_bottom.setFont(font)
        self.label_bottom.setDefaultTextColor(ThemeManager.instance().get_color('text_secondary'))
        # Center the label below the bar
        text_width = self.label_bottom.boundingRect().width()
        self.label_bottom.setPos(-text_width / 2, self._bar_height / 2 + 5)
        self.scene.addItem(self.label_bottom)

    def _create_position_bar(self):
        """Create the green position indicator bar."""
        self.position_bar = QGraphicsRectItem(
            -self._bar_width / 2 + 2, 0,
            self._bar_width - 4, self._position_bar_height
        )
        self.position_bar.setBrush(QBrush(QColor.fromRgb(62, 201, 65)))  # Same green as other widgets
        self.position_bar.setPen(QPen(QColor.fromRgb(62, 201, 65)))
        self.position_bar.setZValue(10)  # Ensure bar is on top
        self.scene.addItem(self.position_bar)

        # Start at center (position 0.5)
        self._set_bar_position(0.5)

    def _set_bar_position(self, position: float):
        """
        Set the position bar location based on normalized position value.

        Args:
            position: 0.0 = bottom, 1.0 = top
        """
        position = max(0.0, min(1.0, position))

        # Calculate y position
        # Position 0 (bottom) = bar_height/2 - bar_height (near bottom edge)
        # Position 1 (top) = -bar_height/2 (near top edge)
        usable_height = self._bar_height - self._position_bar_height - 4  # Leave small margin

        # Invert: position 1.0 should be at top (negative y), position 0.0 at bottom (positive y)
        y_pos = (self._bar_height / 2 - self._position_bar_height - 2) - (position * usable_height)

        self.position_bar.setRect(
            -self._bar_width / 2 + 2, y_pos,
            self._bar_width - 4, self._position_bar_height
        )

    def set_position(self, alpha: float):
        """
        Set the position from the alpha axis.

        Alpha ranges from -1 to 1 in the system. We convert it to 0-1 for display.
        -1 = Bottom, +1 = Top

        Args:
            alpha: Position value in -1 to 1 range.
        """
        # Convert from -1,1 range to 0,1 range
        position = (alpha + 1) / 2  # -1 -> 0, 0 -> 0.5, 1 -> 1

        if position == self.last_position:
            return  # Skip update if position unchanged
        self.last_position = position

        self._set_bar_position(position)

    def resizeEvent(self, event):
        """Handle resize to maintain aspect ratio."""
        super().resizeEvent(event)
        # Set scene rect with some padding for labels
        self.fitInView(-60, -120, 120, 240, Qt.KeepAspectRatio)

    def _update_background_brush(self):
        """Update background brush based on current theme."""
        self.setBackgroundBrush(ThemeManager.instance().get_color('background_graphics'))

    def _on_theme_changed(self, is_dark: bool):
        """Handle theme change by updating colors."""
        self._update_background_brush()

        # Update outline color
        line_color = ThemeManager.instance().get_color('graphics_line')
        line_pen = QPen(line_color)
        line_pen.setWidth(2)
        self.outline_rect.setPen(line_pen)

        # Update label colors
        label_color = ThemeManager.instance().get_color('text_secondary')
        self.label_top.setDefaultTextColor(label_color)
        self.label_bottom.setDefaultTextColor(label_color)

        self.update()
