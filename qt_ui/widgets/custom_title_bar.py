"""
Custom Title Bar Widget

Replaces the native Windows title bar with a Qt-styled one that follows the application theme.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QIcon, QPixmap, QMouseEvent

from qt_ui.theme_manager import ThemeManager


class CustomTitleBar(QWidget):
    """
    A custom title bar widget that can be themed with the application.

    Provides window controls (minimize, maximize, close) and supports
    window dragging.
    """

    # Signals for window control
    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        self._drag_position = None
        self._is_dragging = False

        self.setFixedHeight(32)
        self.setAutoFillBackground(True)

        self._setup_ui()
        self._apply_theme()

        # Connect to theme changes
        ThemeManager.instance().theme_changed.connect(self._apply_theme)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        # Window icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setScaledContents(True)
        layout.addWidget(self.icon_label)

        layout.addSpacing(8)

        # Window title
        self.title_label = QLabel("restim")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.title_label)

        # Window control buttons - set fixed size directly
        # Minimize button
        self.btn_minimize = QPushButton("─")
        self.btn_minimize.setFixedSize(46, 32)
        self.btn_minimize.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.btn_minimize)

        # Maximize button
        self.btn_maximize = QPushButton("□")
        self.btn_maximize.setFixedSize(46, 32)
        self.btn_maximize.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(self.btn_maximize)

        # Close button
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setFixedSize(46, 32)
        self.btn_close.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.btn_close)

    def set_title(self, title: str):
        """Set the window title."""
        self.title_label.setText(title)

    def set_icon(self, icon: QIcon):
        """Set the window icon."""
        pixmap = icon.pixmap(20, 20)
        self.icon_label.setPixmap(pixmap)

    def _apply_theme(self, is_dark: bool = None):
        """Apply the current theme to the title bar."""
        if is_dark is None:
            is_dark = ThemeManager.instance().is_dark_mode()

        if is_dark:
            bg_color = "#3c3c3c"
            text_color = "#ffffff"
            hover_color = "#505050"
            close_hover = "#e81123"
        else:
            bg_color = "#f0f0f0"
            text_color = "#000000"
            hover_color = "#e0e0e0"
            close_hover = "#e81123"

        # Apply stylesheet to title bar and children
        self.setStyleSheet(f"""
            CustomTitleBar {{
                background-color: {bg_color};
            }}
            CustomTitleBar QLabel {{
                color: {text_color};
                background-color: transparent;
            }}
            CustomTitleBar QPushButton {{
                background-color: transparent;
                color: {text_color};
                border: none;
                font-size: 12px;
            }}
            CustomTitleBar QPushButton:hover {{
                background-color: {hover_color};
            }}
            CustomTitleBar QPushButton#btn_close:hover {{
                background-color: {close_hover};
                color: white;
            }}
        """)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.LeftButton:
            # Check if click is not on buttons
            if not self._is_on_button(event.position().toPoint()):
                self._is_dragging = True
                self._drag_position = event.globalPosition().toPoint() - self._parent_window.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            if self._parent_window.isMaximized():
                # Restore window before dragging
                self._parent_window.showNormal()
                # Adjust drag position to center of title bar
                self._drag_position = QPoint(self.width() // 2, self.height() // 2)
            self._parent_window.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop dragging."""
        self._is_dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click to maximize/restore."""
        if event.button() == Qt.LeftButton:
            if not self._is_on_button(event.position().toPoint()):
                self.maximize_clicked.emit()

    def _is_on_button(self, pos: QPoint) -> bool:
        """Check if position is over a control button."""
        for btn in [self.btn_minimize, self.btn_maximize, self.btn_close]:
            if btn.geometry().contains(pos):
                return True
        return False
