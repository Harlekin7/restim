import logging
from PySide6.QtWidgets import QDialog

from qt_ui.about_dialog_ui import Ui_AboutDialog
from qt_ui.theme_manager import ThemeManager
from version import VERSION

logger = logging.getLogger('restim.bake_audio')

class AboutDialog(QDialog, Ui_AboutDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setupUi(self)
        self._update_label()

        # Connect to theme changes
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)

    def _update_label(self):
        # Use a readable link color based on theme
        link_color = "#64a0ff" if ThemeManager.instance().is_dark_mode() else "#334327"
        self.label.setText(
            f"""
<html>
	<head/>
	<body>
		<p><span style=" font-size:18pt; font-weight:700;">
			Restim
			</span>
		</p>
		<p>
			version: {VERSION}
		</p>
		<p>
			homepage: <a href="https://github.com/diglet48/restim">
			<span style=" text-decoration: underline; color:{link_color};">
			https://github.com/diglet48/restim</span>
			</a>
		</p>
	</body>
</html>
            """
        )

    def _on_theme_changed(self, is_dark: bool):
        self._update_label()