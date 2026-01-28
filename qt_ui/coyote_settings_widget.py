import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional
from PySide6 import QtWidgets
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSlider, QHBoxLayout,
                            QGraphicsView, QGraphicsScene, QSpinBox,
                            QGraphicsRectItem)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPen, QColor, QBrush, QFontMetrics
from device.coyote.device import CoyoteDevice, CoyotePulse, CoyotePulses, CoyoteStrengths
from qt_ui import settings
from qt_ui.theme_manager import ThemeManager

class CoyoteSettingsWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.device: Optional[CoyoteDevice] = None
        self.channel_controls: Dict[str, ChannelControl] = {}
        self.coyote_logger = logging.getLogger('restim.coyote')
        self._base_log_level = self.coyote_logger.getEffectiveLevel()
        self.graph_window = settings.coyote_graph_window
        self.setupUi()
        self.apply_debug_logging(settings.coyote_debug_logging.get())

    def setupUi(self):
        self.setLayout(QVBoxLayout())

        # Note: Device status, stage, battery, and reset button are now in CoyoteStatusWidget
        # in the main window's left panel (always visible when in Coyote mode)

        configs = (
            ChannelConfig(
                channel_id='A',
                freq_min_setting=settings.coyote_channel_a_freq_min,
                freq_max_setting=settings.coyote_channel_a_freq_max,
                strength_max_setting=settings.coyote_channel_a_strength_max,
            ),
            ChannelConfig(
                channel_id='B',
                freq_min_setting=settings.coyote_channel_b_freq_min,
                freq_max_setting=settings.coyote_channel_b_freq_max,
                strength_max_setting=settings.coyote_channel_b_strength_max,
            ),
        )

        for config in configs:
            control = ChannelControl(self, config)
            self.channel_controls[config.channel_id] = control
            self.layout().addLayout(control.build_ui())
            control.reset_volume()

    @property
    def channel_a(self) -> 'ChannelControl':
        """Return Channel A control."""
        return self.channel_controls.get('A')

    @property
    def channel_b(self) -> 'ChannelControl':
        """Return Channel B control."""
        return self.channel_controls.get('B')

    def setup_device(self, device: CoyoteDevice):
        self.device = device

        # Note: connection_status_changed and battery_level_changed are handled by CoyoteStatusWidget
        self.device.parameters_changed.connect(self.on_parameters_changed)
        self.device.power_levels_changed.connect(self.on_power_levels_changed)
        self.device.pulse_sent.connect(self.on_pulse_sent)

        # Clear "No Funscript" flag when setting up device (prevents stale state from previous mode)
        for control in self.channel_controls.values():
            if control.pulse_graph and hasattr(control.pulse_graph.plot, 'set_no_funscript_message'):
                control.pulse_graph.plot.set_no_funscript_message(False)

        for control in self.channel_controls.values():
            control.reset_volume()

        if device.strengths:
            for control in self.channel_controls.values():
                control.update_from_device(device.strengths)

    def update_channel_strength(self, control: 'ChannelControl', value: int):
        # Don't send strength commands from UI - let the algorithm control output
        # Strength parameter is for device status tracking only
        # Every Coyote packet must have both intensity AND pulse frequency, or it's rejected
        # The algorithm generates complete packets with both parameters
        if self.device:
            self.device.strengths = control.with_strength(self.device.strengths, value)

    # Note: on_connection_status_changed, on_battery_level_changed, and on_reset_connection_clicked
    # are now handled by CoyoteStatusWidget in the main window

    def on_parameters_changed(self):
        pass

    def on_power_levels_changed(self, strengths: CoyoteStrengths):
        for control in self.channel_controls.values():
            control.update_from_device(strengths)

    def on_pulse_sent(self, pulses: CoyotePulses):
        if not self.device:
            return

        # Check if this is a Motion Algorithm by checking the algorithm type
        from device.coyote.motion_algorithm import CoyoteMotionAlgorithm
        is_motion_algo = isinstance(self.device.algorithm, CoyoteMotionAlgorithm)

        # Only show "No Funscript" message for Motion Algorithm with all zero intensity
        show_no_funscript = False
        if is_motion_algo:
            all_zero = True
            if pulses.channel_a:
                all_zero = all_zero and all(p.intensity == 0 for p in pulses.channel_a)
            if pulses.channel_b:
                all_zero = all_zero and all(p.intensity == 0 for p in pulses.channel_b)
            show_no_funscript = all_zero

        # Always update the flag (clears it for non-Motion modes)
        for control in self.channel_controls.values():
            if control.pulse_graph and hasattr(control.pulse_graph.plot, 'set_no_funscript_message'):
                control.pulse_graph.plot.set_no_funscript_message(show_no_funscript)

        for control in self.channel_controls.values():
            control.apply_pulses(pulses, self.device.strengths)

    def apply_debug_logging(self, enabled: bool):
        new_level = logging.DEBUG if enabled else logging.INFO
        self.coyote_logger.setLevel(new_level)

    def cleanup(self):
        """Clean up widget resources when switching away from Coyote device"""
        if self.device:
            # Note: connection_status_changed and battery_level_changed are handled by CoyoteStatusWidget
            self.device.parameters_changed.disconnect(self.on_parameters_changed)
            self.device.power_levels_changed.disconnect(self.on_power_levels_changed)
            self.device.pulse_sent.disconnect(self.on_pulse_sent)
            self.device = None

    def clear_no_funscript_message(self):
        """Clear the 'No Funscript' message from pulse graphs. Called when starting playback."""
        for control in self.channel_controls.values():
            if control.pulse_graph and hasattr(control.pulse_graph.plot, 'set_no_funscript_message'):
                control.pulse_graph.plot.set_no_funscript_message(False)

@dataclass(frozen=True)
class ChannelConfig:
    channel_id: str
    freq_min_setting: settings.Setting
    freq_max_setting: settings.Setting
    strength_max_setting: settings.Setting

class ChannelControl:
    def __init__(self, parent: 'CoyoteSettingsWidget', config: ChannelConfig):
        self.parent = parent
        self.config = config

        self.freq_min: Optional[QSpinBox] = None
        self.freq_max: Optional[QSpinBox] = None
        self.strength_max: Optional[QSpinBox] = None
        self.volume_slider: Optional[QSlider] = None
        self.volume_label: Optional[QLabel] = None
        self.pulse_graph: Optional[PulseGraphContainer] = None
        self.stats_label: Optional[QLabel] = None

    @property
    def channel_id(self) -> str:
        return self.config.channel_id

    @property
    def _is_channel_a(self) -> bool:
        return self.channel_id.upper() == 'A'

    def build_ui(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        # Left column with fixed width to prevent graph shifts
        left_widget = QWidget()
        left_widget.setFixedWidth(140)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(QLabel(f"Channel {self.channel_id}"))

        freq_min_layout = QHBoxLayout()
        self.freq_min = QSpinBox()
        self.freq_min.setRange(10, 200)
        self.freq_min.setSingleStep(10)
        self.freq_min.setValue(self.config.freq_min_setting.get())
        self.freq_min.valueChanged.connect(self.on_freq_min_changed)
        freq_min_layout.addWidget(QLabel("Min Freq (Hz)"))
        freq_min_layout.addWidget(self.freq_min)
        left.addLayout(freq_min_layout)

        freq_max_layout = QHBoxLayout()
        self.freq_max = QSpinBox()
        self.freq_max.setRange(10, 200)
        self.freq_max.setSingleStep(10)
        self.freq_max.setValue(self.config.freq_max_setting.get())
        self.freq_max.valueChanged.connect(self.on_freq_max_changed)
        freq_max_layout.addWidget(QLabel("Max Freq (Hz)"))
        freq_max_layout.addWidget(self.freq_max)
        left.addLayout(freq_max_layout)

        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Max Strength"))
        self.strength_max = QSpinBox()
        self.strength_max.setRange(1, 200)
        self.strength_max.setSingleStep(1)
        self.strength_max.setValue(self.config.strength_max_setting.get())
        self.strength_max.valueChanged.connect(self.on_strength_max_changed)
        strength_layout.addWidget(self.strength_max)
        left.addLayout(strength_layout)

        layout.addWidget(left_widget)

        self.pulse_graph = PulseGraphContainer(self.parent.graph_window, self.freq_min, self.freq_max)
        self.pulse_graph.plot.setMinimumHeight(100)

        graph_column = QVBoxLayout()
        graph_column.addWidget(self.pulse_graph)

        self.stats_label = QLabel("")
        self.stats_label.setAlignment(Qt.AlignHCenter)
        self.pulse_graph.attach_stats_label(self.stats_label)
        # Don't add stats_label to graph_column - it's hidden now

        layout.addLayout(graph_column)

        volume_layout = QVBoxLayout()
        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setRange(0, self.config.strength_max_setting.get())
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.volume_label = QLabel()
        self.volume_label.setAlignment(Qt.AlignHCenter)
        # Set minimum width to prevent layout shifts when text changes
        # "200 (100%)" is the maximum text, use font metrics to calculate width
        fm = QFontMetrics(self.volume_label.font())
        min_width = fm.horizontalAdvance("200 (100%)") + 4  # Add small padding
        self.volume_label.setMinimumWidth(min_width)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)
        layout.addLayout(volume_layout)

        self.update_volume_label(self.volume_slider.value())
        return layout

    def reset_volume(self):
        self.set_strength_from_device(0)

    def select_strength(self, strengths: CoyoteStrengths) -> int:
        return strengths.channel_a if self._is_channel_a else strengths.channel_b

    def with_strength(self, strengths: CoyoteStrengths, value: int) -> CoyoteStrengths:
        if self._is_channel_a:
            return CoyoteStrengths(channel_a=value, channel_b=strengths.channel_b)
        return CoyoteStrengths(channel_a=strengths.channel_a, channel_b=value)

    def extract_pulses(self, pulses: CoyotePulses) -> list[CoyotePulse]:
        return pulses.channel_a if self._is_channel_a else pulses.channel_b

    def update_from_device(self, strengths: CoyoteStrengths):
        self.set_strength_from_device(self.select_strength(strengths))

    def apply_pulses(self, pulses: CoyotePulses, strengths: CoyoteStrengths):
        channel_pulses = self.extract_pulses(pulses)
        if not channel_pulses:
            return
        self.handle_pulses(channel_pulses, self.select_strength(strengths))

    def on_volume_changed(self, value: int):
        self.update_volume_label(value)
        self.parent.update_channel_strength(self, value)

    def update_volume_label(self, value: int):
        max_strength = max(1, self.config.strength_max_setting.get())
        percentage = int((value / max_strength) * 100)
        self.volume_label.setText(f"{value} ({percentage}%)")

    def set_strength_from_device(self, value: int):
        if self.volume_slider is None:
            return
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(value)
        self.volume_slider.blockSignals(False)

    def cleanup(self):
        """Clean up resources when switching devices"""
        try:
            if self.pulse_graph:
                self.pulse_graph.cleanup()
        except RuntimeError:
            pass  # Qt object already deleted during app shutdown

    def on_strength_max_changed(self, value: int):
        self.config.strength_max_setting.set(value)

        current_value = self.volume_slider.value() if self.volume_slider else 0
        if self.volume_slider:
            self.volume_slider.blockSignals(True)
            self.volume_slider.setRange(0, value)
            clamped_value = min(current_value, value)
            self.volume_slider.setValue(clamped_value)
            self.volume_slider.blockSignals(False)
            self.update_volume_label(clamped_value)
            current_value = clamped_value

        self.parent.update_channel_strength(self, current_value)

    def on_freq_min_changed(self, value: int):
        if self.freq_min is None or self.freq_max is None:
            return

        corrected = value
        if value >= self.freq_max.value():
            corrected = max(self.freq_max.value() - self.freq_min.singleStep(), self.freq_min.minimum())
        if corrected != value:
            self.freq_min.blockSignals(True)
            self.freq_min.setValue(corrected)
            self.freq_min.blockSignals(False)
        self.config.freq_min_setting.set(corrected)

    def on_freq_max_changed(self, value: int):
        if self.freq_min is None or self.freq_max is None:
            return

        corrected = value
        if value <= self.freq_min.value():
            corrected = min(self.freq_min.value() + self.freq_max.singleStep(), self.freq_max.maximum())
        if corrected != value:
            self.freq_max.blockSignals(True)
            self.freq_max.setValue(corrected)
            self.freq_max.blockSignals(False)
        self.config.freq_max_setting.set(corrected)

    def handle_pulses(self, pulses: list[CoyotePulse], strength: int):
        if not self.pulse_graph or not pulses:
            return

        channel_limit = self.config.strength_max_setting.get()
        for pulse in pulses:
            self.pulse_graph.add_pulse(
                frequency=pulse.frequency,
                intensity=pulse.intensity,
                duration=pulse.duration,
                current_strength=strength,
                channel_limit=channel_limit,
            )

class PulseGraphContainer(QWidget):
    def __init__(self, window_seconds: settings.Setting, freq_min: QSpinBox, freq_max: QSpinBox, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store frequency range controls
        self.freq_min = freq_min
        self.freq_max = freq_max

        # Initialize entries list to store CoyotePulse objects
        self.entries = []

        # Time window for stats display (in seconds)
        self.stats_window = window_seconds

        # Create layout
        self.layout = QVBoxLayout(self)

        # Create plot widget with frequency range from channel settings
        self.plot = PulseGraph(window_seconds, freq_min, freq_max, *args, **kwargs)
        self.layout.addWidget(self.plot)

        # Optional stats label managed by parent component
        self.stats_label: Optional[QLabel] = None

    def attach_stats_label(self, label: QLabel):
        self.stats_label = label
        self.stats_label.setText("Intensity: 0%")
        
    def get_frequency_range_text(self, entries) -> str:
        """Get the frequency range text from the given entries."""
        if not entries:
            return "N/A"
        frequencies = [entry.frequency for entry in entries]
        avg_frequency = sum(frequencies) / len(frequencies)
        min_freq = min(frequencies)
        max_freq = max(frequencies)
        
        # If min, max, and average are all the same, just show the single value
        if min_freq == max_freq == round(avg_frequency):
            return f"{int(avg_frequency)} Hz"
        # If min and max differ, show average with range
        return f"{avg_frequency:.0f} Hz ({min_freq} – {max_freq})"

    def format_intensity_text(self, intensities) -> str:
        """Format intensity text with smart range display."""
        if not intensities:
            return "N/A"
        avg_intensity = sum(intensities) / len(intensities)
        min_intensity = min(intensities)
        max_intensity = max(intensities)
        
        # If min, max, and average are all the same, just show the single value
        if min_intensity == max_intensity == round(avg_intensity):
            return f"{int(avg_intensity)}%"
        # If min and max differ, show average with range
        return f"{avg_intensity:.0f}% ({min_intensity} – {max_intensity})"
    
    def clean_old_entries(self):
        """Remove entries outside the time window"""
        current_time = time.time()
        stats_window = self.stats_window.get()
        self.entries = [e for e in self.entries if current_time - e.timestamp <= stats_window]

    def update_label_text(self):
        # Clean up old entries
        self.clean_old_entries()
        
        # Get intensity range from recent entries
        recent_entries = self.entries
        intensities = [entry.intensity for entry in recent_entries]
        intensity_text = self.format_intensity_text(intensities)

        if self.stats_label:
            self.stats_label.setText(f"Intensity: {intensity_text}")

    def add_pulse(self, frequency, intensity, duration, current_strength, channel_limit):
        # Calculate effective intensity after applying current strength
        effective_intensity = intensity * (current_strength / 100)
        
        # For zero intensity pulses, still create them but with zero intensity
        # This shows empty space in the graph
        
        # Create a CoyotePulse object
        pulse = CoyotePulse(
            frequency=frequency, 
            intensity=intensity,
            duration=duration
        )
        
        # Add timestamp for time-window filtering
        pulse.timestamp = time.time()
        
        # Store pulse data
        self.entries.append(pulse)
        
        self.update_label_text()

        # Update the plot - even zero intensity pulses are sent through for visualization
        self.plot.add_pulse(pulse, effective_intensity, channel_limit)

    def cleanup(self):
        """Stop timers and clean up resources"""
        if self.plot:
            self.plot.cleanup()

class PulseGraph(QWidget):
    def __init__(self, window_seconds: settings.Setting, freq_min_spinbox: QSpinBox, freq_max_spinbox: QSpinBox, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        # Set background based on current theme
        self._update_background_brush()

        # Connect to theme changes
        ThemeManager.instance().theme_changed.connect(self._on_theme_changed)

        # Completely disable scrolling and user interaction
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setInteractive(False)  # Disable interaction for performance
        self.view.setDragMode(QGraphicsView.NoDrag)
        self.view.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.view.setResizeAnchor(QGraphicsView.NoAnchor)
        self.view.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

        # Prevent wheel events
        self.view.wheelEvent = lambda event: None

        self.layout().addWidget(self.view)

        # Configuration for time window (in seconds)
        self.time_window = window_seconds

        # Store pulses for visualization
        self.pulses = []
        self.channel_limit = 100  # Default channel limit

        # Packet tracking for FIFO visualization
        self.current_packet_index = 0  # Which 4-pulse packet is currently active
        self.last_packet_time = 0     # When the last packet was received

        # Track if we need to refresh (dirty flag)
        self._dirty = False
        self._last_refresh_time = 0

        # Initialize the scene size
        self.updateSceneRect()

        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(50)  # 20Hz refresh rate (was 60Hz) - sufficient for visualization

        # Colors for visualization
        self.pulse_color = QColor(0, 255, 0, 200)  # Semi-transparent lime
        self.pulse_border_color = QColor("darkgreen")

        # Time scaling factor - how many pixels per ms of duration
        self.time_scale_factor = 0.5  # pixels per ms

        # Frequency range spinboxes from channel settings
        self.freq_min_spinbox = freq_min_spinbox
        self.freq_max_spinbox = freq_max_spinbox
    
    def resizeEvent(self, event):
        """Handle resize events by updating the scene rectangle"""
        super().resizeEvent(event)
        self.updateSceneRect()
        # Mark dirty to force refresh on next timer tick
        self._dirty = True
    
    def updateSceneRect(self):
        """Update the scene rectangle to match the view size"""
        if self.view:
            width = self.view.viewport().width()
            height = self.view.viewport().height()
            self.view.setSceneRect(0, 0, width, height)
    
    def get_color_for_frequency(self, frequency: float) -> QColor:
        """
        Calculate color based on frequency using the channel's min/max settings.
        Green at min frequency, yellow at midpoint, red at max frequency.
        """
        # Get current min/max from spinboxes
        freq_min = self.freq_min_spinbox.value() if self.freq_min_spinbox else 10
        freq_max = self.freq_max_spinbox.value() if self.freq_max_spinbox else 200

        # Calculate normalized position (0 = min freq, 1 = max freq)
        if freq_max <= freq_min:
            t = 0.5  # Avoid division by zero
        else:
            t = (frequency - freq_min) / (freq_max - freq_min)
            t = max(0, min(1, t))  # Clamp to [0, 1]

        # Green (0, 255, 0) → Yellow (255, 255, 0) → Red (255, 0, 0)
        if t <= 0.5:
            # Green to Yellow: R increases from 0 to 255
            r = int(255 * (t * 2))
            g = 255
            b = 0
        else:
            # Yellow to Red: G decreases from 255 to 0
            r = 255
            g = int(255 * (1 - (t - 0.5) * 2))
            b = 0

        # Return with semi-transparency
        return QColor(r, g, b, 200)
    
    def clean_old_pulses(self):
        """Remove pulses outside the time window"""
        current_time = time.time()
        time_window = self.time_window.get()
        old_count = len(self.pulses)
        self.pulses = [p for p in self.pulses if current_time - p.timestamp <= time_window]
        if len(self.pulses) != old_count:
            self._dirty = True

    def add_pulse(self, pulse: CoyotePulse, applied_intensity: float, channel_limit: int):
        """Add a new pulse to the visualization"""
        # Don't skip zero intensity pulses, but display them differently
        self.channel_limit = channel_limit

        # Show every pulse - no deduplication
        current_time = time.time()

        # Store the CoyotePulse with additional metadata
        pulse_copy = CoyotePulse(
            frequency=pulse.frequency,
            intensity=pulse.intensity,
            duration=pulse.duration
        )

        # Add additional attributes to the pulse
        pulse_copy.applied_intensity = applied_intensity
        pulse_copy.packet_index = self.current_packet_index
        pulse_copy.timestamp = current_time

        # Add the pulse
        self.pulses.append(pulse_copy)
        self._dirty = True

        # Clean up old pulses that are outside our time window (periodically)
        if len(self.pulses) > 200:  # Only clean when list gets large
            self.clean_old_pulses()

    def set_no_funscript_message(self, show: bool):
        """Set whether to show 'No Funscript' message"""
        self._show_no_funscript = show
        self._dirty = True

    def refresh(self):
        """Redraw the pulse visualization"""
        # Skip refresh if widget is not visible
        if not self.isVisible():
            return

        # Skip refresh if nothing changed and we refreshed recently
        now = time.time()
        if not self._dirty and (now - self._last_refresh_time) < 0.1:
            return

        self._dirty = False
        self._last_refresh_time = now

        # Clean up old pulses periodically
        self.clean_old_pulses()

        self.scene.clear()

        # Always ensure we're using the current viewport size
        self.updateSceneRect()

        width = self.view.viewport().width()
        height = self.view.viewport().height()

        # Show "No Funscript" message if flag is set or no pulses
        if not self.pulses:
            if getattr(self, '_show_no_funscript', False):
                text_item = self.scene.addText("No Funscript")
                text_item.setDefaultTextColor(QColor(150, 150, 150))
                # Center the text
                text_rect = text_item.boundingRect()
                text_item.setPos((width - text_rect.width()) / 2, (height - text_rect.height()) / 2)
            return

        # Sort pulses by timestamp so they display in chronological order
        sorted_pulses = sorted(self.pulses, key=lambda p: p.timestamp)

        # Find the maximum intensity in current visible pulses
        max_intensity = max(pulse.applied_intensity for pulse in sorted_pulses)
        # Use either the channel limit or the current max intensity, whichever is larger
        scale_max = max(max_intensity, self.channel_limit)

        # Get the time span of the visible pulses
        time_window = self.time_window.get()
        oldest_time = now - time_window
        newest_time = now
        time_span_sec = time_window

        # Calculate total width available for all pulses
        usable_width = width - 10  # Leave small margin on right side

        # Group pulses by packet for continuous display
        pulses_by_packet = {}
        for pulse in sorted_pulses:
            packet_idx = pulse.packet_index
            if packet_idx not in pulses_by_packet:
                pulses_by_packet[packet_idx] = []
            pulses_by_packet[packet_idx].append(pulse)

        # Get sorted list of packet indices
        packet_indices = sorted(pulses_by_packet.keys())

        # Draw each packet's pulses as a continuous sequence
        for i, packet_idx in enumerate(packet_indices):
            packet_pulses = pulses_by_packet[packet_idx]  # Already sorted by timestamp from earlier

            # Determine the time range this packet covers
            if i < len(packet_indices) - 1:
                # This packet runs until the next packet starts
                next_packet_idx = packet_indices[i + 1]
                next_packet_start = pulses_by_packet[next_packet_idx][0].timestamp
                packet_end_time = next_packet_start
            else:
                # This is the last packet, it runs until now
                packet_end_time = now

            # Draw each pulse in this packet
            for j, pulse in enumerate(packet_pulses):
                # Calculate time positions
                pulse_start_time = pulse.timestamp

                # For continuity, calculate the end time:
                if j < len(packet_pulses) - 1:
                    # If there's another pulse in this packet, it extends to that pulse
                    pulse_end_time = packet_pulses[j + 1].timestamp
                else:
                    # If this is the last pulse in the packet, it extends to the packet end
                    pulse_end_time = packet_end_time

                # Ensure we're within the visible time window
                pulse_start_time = max(pulse_start_time, oldest_time)
                pulse_end_time = min(pulse_end_time, newest_time)

                # Skip if entirely outside window
                if pulse_end_time <= oldest_time or pulse_start_time >= newest_time:
                    continue

                # Calculate positions and dimensions
                time_position_start = (pulse_start_time - oldest_time) / time_span_sec
                time_position_end = (pulse_end_time - oldest_time) / time_span_sec

                x_start = 5 + (time_position_start * usable_width)
                x_end = 5 + (time_position_end * usable_width)
                rect_width = max(3, x_end - x_start)  # Minimum 3px, but allow full width to fill gaps

                # Calculate height based on intensity (always define rect_height)
                height_ratio = pulse.applied_intensity / scale_max if scale_max > 0 else 0
                rect_height = height * height_ratio

                # Get color based on frequency
                pulse_color = self.get_color_for_frequency(pulse.frequency)

                # For zero-intensity pulses, still show something to indicate timing
                if pulse.applied_intensity <= 0:
                    # Draw a thin line or empty rectangle to show timing without intensity
                    empty_rect = QGraphicsRectItem(
                        x_start, height - 2,  # Just a thin line at the bottom
                        rect_width, 2
                    )
                    empty_rect.setBrush(QBrush(QColor(100, 100, 100, 50)))  # Almost transparent
                    self.scene.addItem(empty_rect)
                else:
                    # Create simple rectangle for the pulse (no hover events for performance)
                    rect = QGraphicsRectItem(
                        x_start, height - rect_height,  # x, y (bottom-aligned)
                        rect_width, rect_height         # width, height
                    )
                    rect.setBrush(QBrush(pulse_color))
                    self.scene.addItem(rect)

    def _update_background_brush(self):
        """Update background brush based on current theme."""
        self.view.setBackgroundBrush(ThemeManager.instance().get_color('background_graphics'))

    def _on_theme_changed(self, is_dark: bool):
        """Handle theme change."""
        self._update_background_brush()
        self._dirty = True

    def cleanup(self):
        """Stop the timer to prevent errors on close"""
        if self.timer:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None
