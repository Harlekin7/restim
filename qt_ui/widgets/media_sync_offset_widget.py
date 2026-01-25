"""Media Sync Offset Widget for the main window left sidebar."""

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QSpinBox
from qt_ui import settings


class MediaSyncOffsetWidget(QGroupBox):
    """Widget for adjusting media sync offset, visible for all devices."""

    def __init__(self, parent=None):
        super().__init__("Media Sync", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        offset_label = QLabel("Offset:")
        offset_label.setToolTip(
            "Compensate for device latency when syncing with media players.\n"
            "Positive values delay the signal, negative values advance it.\n"
            "Typical range: -500ms to +500ms"
        )

        self.offset_spinbox = QSpinBox()
        self.offset_spinbox.setRange(-2000, 2000)
        self.offset_spinbox.setSingleStep(10)
        self.offset_spinbox.setSuffix(" ms")
        self.offset_spinbox.setValue(settings.media_sync_offset_ms.get())
        self.offset_spinbox.setToolTip(
            "Compensate for device latency when syncing with media players.\n"
            "Positive values delay the signal, negative values advance it."
        )
        self.offset_spinbox.valueChanged.connect(self._on_offset_changed)

        layout.addWidget(offset_label)
        layout.addWidget(self.offset_spinbox)
        layout.addStretch()

    def _on_offset_changed(self, value: int):
        """Handle sync offset change."""
        settings.media_sync_offset_ms.set(value)
