"""
Theme Manager for Restim Software

Provides centralized dark/light theme management with QPalette-based theming
and runtime theme switching support.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

import qt_ui.settings


class ThemeManager(QObject):
    """
    Singleton class that manages application theming.

    Signals:
        theme_changed(bool): Emitted when theme changes. True = dark mode, False = light mode.
    """

    _instance = None
    theme_changed = Signal(bool)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._is_dark_mode = False
        self._light_palette = None
        self._dark_palette = None
        self._colors = {}
        self._setup_colors()

    @classmethod
    def instance(cls):
        """Get the singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _setup_colors(self):
        """Define color palettes for light and dark themes."""
        # Light theme colors
        self._colors['light'] = {
            'background_primary': QColor(255, 255, 255),
            'background_secondary': QColor(240, 240, 240),
            'background_graphics': QColor(255, 255, 255),
            'text_primary': QColor(0, 0, 0),
            'text_secondary': QColor(100, 100, 100),
            'border': QColor(200, 200, 200),
            'graphics_line': QColor(50, 50, 50),
            'graphics_line_light': QColor(180, 180, 180),
            'cursor_border': QColor(0, 0, 0),
        }

        # Dark theme colors
        self._colors['dark'] = {
            'background_primary': QColor(45, 45, 45),
            'background_secondary': QColor(60, 60, 60),
            'background_graphics': QColor(35, 35, 35),
            'text_primary': QColor(255, 255, 255),
            'text_secondary': QColor(180, 180, 180),
            'border': QColor(80, 80, 80),
            'graphics_line': QColor(200, 200, 200),
            'graphics_line_light': QColor(100, 100, 100),
            'cursor_border': QColor(255, 255, 255),
        }

        # Semantic colors - same in both themes
        self._semantic_colors = {
            'error': QColor(255, 0, 0),
            'success': QColor(0, 200, 0),
            'warning': QColor(255, 165, 0),
            'cursor_dot': QColor(62, 201, 65),  # Green cursor dot
        }

    def _create_light_palette(self) -> QPalette:
        """Create the light mode palette."""
        palette = QPalette()
        colors = self._colors['light']

        # Window
        palette.setColor(QPalette.Window, colors['background_secondary'])
        palette.setColor(QPalette.WindowText, colors['text_primary'])

        # Base (input fields, lists)
        palette.setColor(QPalette.Base, colors['background_primary'])
        palette.setColor(QPalette.AlternateBase, colors['background_secondary'])

        # Text
        palette.setColor(QPalette.Text, colors['text_primary'])
        palette.setColor(QPalette.PlaceholderText, colors['text_secondary'])

        # Buttons
        palette.setColor(QPalette.Button, colors['background_secondary'])
        palette.setColor(QPalette.ButtonText, colors['text_primary'])

        # Selection
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        # Links
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.LinkVisited, QColor(128, 78, 168))

        # Tooltips
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, colors['text_primary'])

        return palette

    def _create_dark_palette(self) -> QPalette:
        """Create the dark mode palette."""
        palette = QPalette()
        colors = self._colors['dark']

        # Window
        palette.setColor(QPalette.Window, colors['background_secondary'])
        palette.setColor(QPalette.WindowText, colors['text_primary'])

        # Base (input fields, lists)
        palette.setColor(QPalette.Base, colors['background_primary'])
        palette.setColor(QPalette.AlternateBase, colors['background_secondary'])

        # Text
        palette.setColor(QPalette.Text, colors['text_primary'])
        palette.setColor(QPalette.PlaceholderText, colors['text_secondary'])

        # Buttons
        palette.setColor(QPalette.Button, colors['background_secondary'])
        palette.setColor(QPalette.ButtonText, colors['text_primary'])

        # Selection
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        # Links
        palette.setColor(QPalette.Link, QColor(100, 160, 255))
        palette.setColor(QPalette.LinkVisited, QColor(160, 120, 200))

        # Tooltips
        palette.setColor(QPalette.ToolTipBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ToolTipText, colors['text_primary'])

        # Disabled
        palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))

        return palette

    def is_dark_mode(self) -> bool:
        """Check if dark mode is currently active."""
        return self._is_dark_mode

    def get_color(self, name: str) -> QColor:
        """
        Get a color by its semantic name.

        Args:
            name: Color name (e.g., 'background_graphics', 'text_primary', 'error')

        Returns:
            QColor for the requested color in the current theme.
        """
        # Check semantic colors first (theme-independent)
        if name in self._semantic_colors:
            return self._semantic_colors[name]

        # Get theme-specific color
        theme = 'dark' if self._is_dark_mode else 'light'
        return self._colors[theme].get(name, QColor(128, 128, 128))

    def get_color_css(self, name: str) -> str:
        """
        Get a color as a CSS-compatible string.

        Args:
            name: Color name

        Returns:
            CSS color string (e.g., '#ff0000' or 'rgb(255,0,0)')
        """
        color = self.get_color(name)
        return color.name()

    def set_dark_mode(self, enabled: bool):
        """
        Set dark mode on or off.

        Args:
            enabled: True for dark mode, False for light mode
        """
        if enabled != self._is_dark_mode:
            self._is_dark_mode = enabled
            qt_ui.settings.theme_dark_mode.set(enabled)
            self._apply_palette()
            self.theme_changed.emit(enabled)

    def toggle_dark_mode(self):
        """Toggle between dark and light mode."""
        self.set_dark_mode(not self._is_dark_mode)

    def _get_dark_stylesheet(self) -> str:
        """Get the dark mode stylesheet."""
        colors = self._colors['dark']
        bg_primary = colors['background_primary'].name()
        bg_secondary = colors['background_secondary'].name()
        text_primary = colors['text_primary'].name()
        text_secondary = colors['text_secondary'].name()
        border = colors['border'].name()

        return f"""
            QWidget {{
                background-color: {bg_secondary};
                color: {text_primary};
            }}
            QMainWindow {{
                background-color: {bg_secondary};
            }}
            QDialog {{
                background-color: {bg_secondary};
            }}
            QGroupBox {{
                background-color: {bg_secondary};
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 4px;
                color: {text_primary};
            }}
            QTabWidget::pane {{
                background-color: {bg_secondary};
                border: 1px solid {border};
            }}
            QTabBar::tab {{
                background-color: {bg_primary};
                color: {text_primary};
                padding: 8px 16px;
                border: 1px solid {border};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background-color: {bg_secondary};
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border};
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_primary};
                color: {text_primary};
                selection-background-color: #2a82da;
            }}
            QListWidget, QTreeWidget, QTableWidget, QTableView, QListView, QTreeView {{
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border};
            }}
            QHeaderView::section {{
                background-color: {bg_secondary};
                color: {text_primary};
                padding: 4px;
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border};
                padding: 6px 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #505050;
            }}
            QPushButton:pressed {{
                background-color: #404040;
            }}
            QSlider::groove:horizontal {{
                background-color: {bg_primary};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: #2a82da;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QProgressBar {{
                background-color: {bg_primary};
                border: 1px solid {border};
                border-radius: 3px;
                text-align: center;
                color: {text_primary};
            }}
            QProgressBar::chunk {{
                background-color: #2a82da;
            }}
            QScrollBar:vertical {{
                background-color: {bg_primary};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {border};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {bg_primary};
                height: 12px;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {border};
                min-width: 20px;
                border-radius: 6px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QMenuBar {{
                background-color: {bg_secondary};
                color: {text_primary};
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 4px 8px;
            }}
            QMenuBar::item:selected {{
                background-color: #505050;
            }}
            QMenu {{
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border};
            }}
            QMenu::item:selected {{
                background-color: #2a82da;
            }}
            QToolBar {{
                background-color: {bg_secondary};
                border: none;
                spacing: 3px;
            }}
            QToolButton {{
                background-color: transparent;
                color: {text_primary};
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: #505050;
            }}
            QToolButton:checked {{
                background-color: #404040;
            }}
            QLabel {{
                background-color: transparent;
                color: {text_primary};
            }}
            QCheckBox {{
                color: {text_primary};
            }}
            QRadioButton {{
                color: {text_primary};
            }}
            QStatusBar {{
                background-color: {bg_secondary};
                color: {text_primary};
            }}
            QToolTip {{
                background-color: {bg_primary};
                color: {text_primary};
                border: 1px solid {border};
            }}
        """

    def _get_light_stylesheet(self) -> str:
        """Get the light mode stylesheet (minimal - mostly use defaults)."""
        return ""

    def _apply_palette(self):
        """Apply the current theme's palette and stylesheet to the application."""
        app = QApplication.instance()
        if app is None:
            return

        if self._is_dark_mode:
            if self._dark_palette is None:
                self._dark_palette = self._create_dark_palette()
            app.setPalette(self._dark_palette)
            app.setStyleSheet(self._get_dark_stylesheet())
        else:
            if self._light_palette is None:
                self._light_palette = self._create_light_palette()
            app.setPalette(self._light_palette)
            app.setStyleSheet(self._get_light_stylesheet())

    def apply_theme(self, app: QApplication = None):
        """
        Apply the saved theme preference to the application.

        Should be called once at application startup after QApplication is created.

        Args:
            app: QApplication instance (optional, will use QApplication.instance() if None)
        """
        # Load saved preference
        self._is_dark_mode = qt_ui.settings.theme_dark_mode.get()

        # Apply the palette and stylesheet
        self._apply_palette()
