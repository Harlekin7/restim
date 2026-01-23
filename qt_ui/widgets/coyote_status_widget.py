"""
Coyote Status Widget for the main window.

Displays device connection status, stage, battery level, and reset button.
Only visible when in Coyote device mode.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QSizePolicy, QSpinBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics

from device.coyote.device import CoyoteDevice
from device.coyote.types import ConnectionStage
from qt_ui import settings


class ElidedLabel(QLabel):
    """A QLabel that elides text with '...' when it doesn't fit."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text: str):
        self._full_text = text
        self._update_elided_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        # Don't elide if widget hasn't been laid out yet
        if self.width() <= 0:
            super().setText(self._full_text)
            return
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.ElideRight, self.width())
        super().setText(elided)


class CoyoteStatusWidget(QGroupBox):
    """Widget displaying Coyote device status in the main window."""

    def __init__(self, parent=None):
        super().__init__("Coyote", parent)
        self.device: Optional[CoyoteDevice] = None
        self._setup_ui()
        # Start hidden - will be shown when Coyote mode is active
        self.setVisible(False)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Status labels in a horizontal layout
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        self.label_device = ElidedLabel("Disconnected")
        self.label_device.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label_stage = ElidedLabel("—")
        self.label_stage.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label_battery = ElidedLabel("—")
        self.label_battery.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        status_layout.addWidget(QLabel("Device:"))
        status_layout.addWidget(self.label_device)
        status_layout.addStretch()

        layout.addLayout(status_layout)

        # Stage and battery on second row
        status_layout2 = QHBoxLayout()
        status_layout2.setSpacing(8)

        status_layout2.addWidget(QLabel("Stage:"))
        status_layout2.addWidget(self.label_stage)
        status_layout2.addStretch()
        status_layout2.addWidget(QLabel("Battery:"))
        status_layout2.addWidget(self.label_battery)

        layout.addLayout(status_layout2)

        # Reset button
        self.button_reset = QPushButton("Reset Connection")
        self.button_reset.clicked.connect(self._on_reset_clicked)
        layout.addWidget(self.button_reset)

        # Media sync offset for Bluetooth latency compensation
        offset_layout = QHBoxLayout()
        offset_layout.setSpacing(4)
        offset_label = QLabel("Sync Offset:")
        offset_label.setToolTip(
            "Compensate for Bluetooth latency when syncing with media players.\n"
            "Positive values delay the signal, negative values advance it.\n"
            "Typical range: -500ms to +500ms"
        )
        self.offset_spinbox = QSpinBox()
        self.offset_spinbox.setRange(-2000, 2000)
        self.offset_spinbox.setSingleStep(10)
        self.offset_spinbox.setSuffix(" ms")
        self.offset_spinbox.setValue(settings.media_sync_offset_ms.get())
        self.offset_spinbox.setToolTip(
            "Compensate for Bluetooth latency when syncing with media players.\n"
            "Positive values delay the signal, negative values advance it."
        )
        self.offset_spinbox.valueChanged.connect(self._on_offset_changed)
        offset_layout.addWidget(offset_label)
        offset_layout.addWidget(self.offset_spinbox)
        offset_layout.addStretch()
        layout.addLayout(offset_layout)

    def set_device(self, device: Optional[CoyoteDevice]):
        """Connect to a Coyote device and listen for status updates."""
        # Disconnect from previous device
        if self.device:
            try:
                self.device.connection_status_changed.disconnect(self._on_connection_status_changed)
                self.device.battery_level_changed.disconnect(self._on_battery_level_changed)
            except RuntimeError:
                pass  # Already disconnected

        self.device = device

        if device:
            device.connection_status_changed.connect(self._on_connection_status_changed)
            device.battery_level_changed.connect(self._on_battery_level_changed)
            # Update with current state
            is_connected = device.connection_stage == ConnectionStage.CONNECTED
            self._update_connection_display(is_connected, device.connection_stage)
            # Only show battery if connected
            if is_connected:
                self._on_battery_level_changed(device.battery_level)
        else:
            # No device - reset display
            self._update_connection_display(False, None)
            self.label_battery.setText("—")

    def _on_connection_status_changed(self, connected: bool, stage: str = None):
        """Handle connection status changes."""
        self._update_connection_display(connected, stage)

    def _update_connection_display(self, connected: bool, stage: str = None):
        """Update the connection status display."""
        self.label_device.setText("Connected" if connected else "Disconnected")

        if stage:
            normalized_stage = stage.strip()
            if connected and normalized_stage.lower() == "connected":
                stage_text = "Ready"
            else:
                stage_text = normalized_stage
            self.label_stage.setText(stage_text)
        else:
            self.label_stage.setText("—")

        # Show battery as "—" when not connected
        if not connected:
            self.label_battery.setText("—")

    def _on_battery_level_changed(self, level: int):
        """Handle battery level changes."""
        # Only show battery level if we have a connected device
        if self.device and self.device.connection_stage == ConnectionStage.CONNECTED:
            self.label_battery.setText(f"{level}%")
        else:
            self.label_battery.setText("—")

    def _on_reset_clicked(self):
        """Handle reset button click."""
        if self.device:
            self.device.reset_connection()

    def _on_offset_changed(self, value: int):
        """Handle sync offset change."""
        settings.media_sync_offset_ms.set(value)

    def cleanup(self):
        """Disconnect from device when cleaning up."""
        self.set_device(None)
