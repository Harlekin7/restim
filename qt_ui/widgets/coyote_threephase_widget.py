"""
Coyote Three-Phase Visualization Widget.

Displays a simple horizontal line representing the alpha axis (left-right channel balance),
with a moving dot showing the current position. The CoyoteThreePhaseAlgorithm only uses
alpha for position control (beta is ignored), so this widget shows just left-right movement.

Visual layout: A label on the left, B label on the right.
Center = Equal intensity on both channels.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem
from PySide6.QtGui import QColor, QPen, QFont, QPainter, QMouseEvent

from qt_ui.theme_manager import ThemeManager


class CoyoteThreePhaseWidget(QGraphicsView):
    """
    A QGraphicsView that displays a horizontal line for Coyote three-phase position control.

    Visual layout: A label on the left, B label on the right.
    The dot moves along the alpha axis (-1 to +1).
    """

    mousePositionChanged = Signal(float, float)

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

        self.setMouseTracking(True)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Coordinate system: use same scale as threephase widget (-100 to 100)
        # Alpha maps to X: -1 -> -83, +1 -> +83
        self._scale = 83  # Same as threephase widget

        # Create the visualization elements
        self._create_line()
        self._create_center_mark()
        self._create_labels()
        self._create_dot()

        self.last_state = None

    def _alpha_to_x(self, alpha: float) -> float:
        """Convert alpha (-1 to +1) to x coordinate."""
        return alpha * self._scale

    def _x_to_alpha(self, x: float) -> float:
        """Convert x coordinate to alpha (-1 to +1)."""
        return max(-1.0, min(1.0, x / self._scale))

    def _create_line(self):
        """Create the main horizontal line."""
        pen = QPen(ThemeManager.instance().get_color('graphics_line'))
        pen.setWidth(2)

        # Main horizontal line from left to right
        self.main_line = QGraphicsLineItem(-self._scale, 0, self._scale, 0)
        self.main_line.setPen(pen)
        self.scene.addItem(self.main_line)

        # Left end cap (vertical tick)
        self.left_cap = QGraphicsLineItem(-self._scale, -10, -self._scale, 10)
        self.left_cap.setPen(pen)
        self.scene.addItem(self.left_cap)

        # Right end cap (vertical tick)
        self.right_cap = QGraphicsLineItem(self._scale, -10, self._scale, 10)
        self.right_cap.setPen(pen)
        self.scene.addItem(self.right_cap)

    def _create_center_mark(self):
        """Create the center/neutral marker."""
        pen = QPen(ThemeManager.instance().get_color('graphics_line_light'))
        pen.setWidth(2)

        # Center tick mark
        self.center_mark = QGraphicsLineItem(0, -15, 0, 15)
        self.center_mark.setPen(pen)
        self.scene.addItem(self.center_mark)

    def _create_labels(self):
        """Create Channel A and Channel B labels."""
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)

        # Channel A label (left side - dominant when alpha = -1)
        self.label_a = QGraphicsTextItem("A")
        self.label_a.setFont(font)
        self.label_a.setDefaultTextColor(ThemeManager.instance().get_color('text_secondary'))
        # Position below the left end
        self.label_a.setPos(-self._scale - 5, 15)
        self.scene.addItem(self.label_a)

        # Channel B label (right side - dominant when alpha = +1)
        self.label_b = QGraphicsTextItem("B")
        self.label_b.setFont(font)
        self.label_b.setDefaultTextColor(ThemeManager.instance().get_color('text_secondary'))
        # Position below the right end
        self.label_b.setPos(self._scale - 8, 15)
        self.scene.addItem(self.label_b)

    def _create_dot(self):
        """Create the position indicator dot."""
        self.dot = QGraphicsEllipseItem(0, 0, 10, 10)
        self.dot.setBrush(QColor.fromRgb(62, 201, 65))  # Same green as threephase
        self.dot.setPen(QColor.fromRgb(62, 201, 65))
        self.dot.setZValue(10)  # Ensure dot is on top
        self.scene.addItem(self.dot)

        # Start at center
        self._set_dot_position(0)

    def _set_dot_position(self, alpha: float):
        """Set the dot position based on alpha value."""
        alpha = max(-1.0, min(1.0, alpha))
        x = self._alpha_to_x(alpha)
        # Center the dot on the position (dot is 10x10, so offset by -5)
        self.dot.setPos(x - 5, -5)

    def resizeEvent(self, event):
        """Handle resize to maintain aspect ratio."""
        super().resizeEvent(event)
        self.fitInView(-100, -100, 200, 200, Qt.KeepAspectRatio)

    def set_cursor_position_ab(self, alpha: float, beta: float):
        """
        Set the cursor position. For Coyote three-phase mode, only alpha matters.
        Beta is ignored since the algorithm only uses alpha for channel balance.
        """
        state = (alpha, beta)
        if state == self.last_state:
            return  # Skip drawing to save CPU cycles
        self.last_state = state

        # Invert alpha to match the mirrored label layout (A on left, B on right)
        self._set_dot_position(-alpha)

    def mousePressEvent(self, event: QMouseEvent):
        self._handle_mouse_event(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._handle_mouse_event(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._handle_mouse_event(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._handle_mouse_event(event)

    def _handle_mouse_event(self, event: QMouseEvent):
        """Handle mouse events for position control."""
        if not (event.buttons() & Qt.LeftButton):
            return

        # Map screen position to scene coordinates
        scene_pos = self.mapToScene(event.pos())

        # Convert x to alpha, then invert to match mirrored layout (A on left, B on right)
        alpha = -self._x_to_alpha(scene_pos.x())

        # For Coyote three-phase mode, we emit the alpha position with beta=0
        # since beta is ignored by the algorithm anyway
        beta = 0.0

        self.mousePositionChanged.emit(alpha, beta)

    def _update_background_brush(self):
        """Update background brush based on current theme."""
        self.setBackgroundBrush(ThemeManager.instance().get_color('background_graphics'))

    def _on_theme_changed(self, is_dark: bool):
        """Handle theme change by updating colors."""
        self._update_background_brush()

        # Update line colors
        line_color = ThemeManager.instance().get_color('graphics_line')
        line_pen = QPen(line_color)
        line_pen.setWidth(2)
        self.main_line.setPen(line_pen)
        self.left_cap.setPen(line_pen)
        self.right_cap.setPen(line_pen)

        # Update center mark color
        center_pen = QPen(ThemeManager.instance().get_color('graphics_line_light'))
        center_pen.setWidth(2)
        self.center_mark.setPen(center_pen)

        # Update label colors
        label_color = ThemeManager.instance().get_color('text_secondary')
        self.label_a.setDefaultTextColor(label_color)
        self.label_b.setDefaultTextColor(label_color)

        self.update()
