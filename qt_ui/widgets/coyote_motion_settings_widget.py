from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QSlider, QCheckBox, QSpinBox,
                             QComboBox, QFrame)
from PySide6.QtCore import Qt
from qt_ui import settings

# Tooltip strings for all controls
TOOLTIP_FREQUENCY_ALGORITHM = (
    "Selects how pulse frequency varies during playback.\n"
    "See description below for details on each algorithm."
)
TOOLTIP_VELOCITY_FACTOR = (
    "How much velocity affects frequency.\n"
    "0% = algorithm only, 100% = velocity only"
)
TOOLTIP_VELOCITY_TIMEFRAME = (
    "Time window for averaging velocity.\n"
    "Larger values smooth out speed changes."
)
TOOLTIP_THROBBING_ENABLED = (
    "Reduces opposite channel intensity when strokes\n"
    "are confined to the top or bottom region."
)
TOOLTIP_THROBBING_INTENSITY = (
    "How much to reduce the opposite channel.\n"
    "Higher values create stronger regional focus."
)
TOOLTIP_BOTTOM_THRESHOLD = (
    "Strokes staying below this threshold\n"
    "reduce Channel B (top) intensity."
)
TOOLTIP_UPPER_THRESHOLD = (
    "Strokes staying above this threshold\n"
    "reduce Channel A (bottom) intensity."
)
TOOLTIP_BASE_AMPLITUDE = (
    "Base output level during movement.\n"
    "Minimum amplitude at center position."
)
TOOLTIP_EXTREME_BOOST = (
    "Extra intensity at position extremes (0% and 100%).\n"
    "Creates stronger sensation at top and bottom of strokes."
)
TOOLTIP_DYNAMIC_VOLUME_ENABLED = "Automatically adjust volume based on section intensity."
TOOLTIP_DYNAMIC_SENSITIVITY = (
    "How much dynamic volume affects output.\n"
    "0% = constant, 100% = full variation"
)
TOOLTIP_WINDOW_SIZE = (
    "Time window for measuring section intensity.\n"
    "Longer windows provide smoother transitions."
)
TOOLTIP_MIX_RATIO = "Balance between Section Stroke count and Section Velocity"
TOOLTIP_FADE_OUT_TIME = "Time to fade out when movement stops."
TOOLTIP_FADE_IN_TIME = "Time to fade in when movement resumes."
TOOLTIP_VARIED_RANGE = (
    "How much the frequency varies from center.\n"
    "Higher values create wider frequency swings."
)
TOOLTIP_BLEND_RATIO = (
    "Balance between Position and Noise algorithms.\n"
    "0% = pure position, 100% = pure noise"
)

# Descriptions for frequency algorithm dropdown
FREQ_ALGO_DESCRIPTIONS = {
    "Position (Standard)": (
        "Frequency varies directly with stroke position.\n"
        "Bottom = min frequency, Top = max frequency."
    ),
    "Varied (Noise-based)": (
        "Frequency oscillates around the center using noise.\n"
        "Adjust the range slider to control variation size."
    ),
    "Blend (Position + Noise)": (
        "Mix of position-based and noise-based frequency.\n"
        "Adjust the ratio slider to control the blend."
    ),
    "Fixed (Constant)": (
        "Frequency stays constant at the midpoint.\n"
        "Position has no effect on pulse rate."
    ),
}


class CoyoteMotionSettingsWidget(QWidget):
    """UI settings for Coyote Motion Algorithm enhancement"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.bind_to_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Frequency Options (Algorithm + Velocity Factor)
        freq_group = QGroupBox("Frequency Options")
        freq_layout = QVBoxLayout(freq_group)

        self.frequency_algorithm = QComboBox()
        self.frequency_algorithm.addItems([
            "Position (Standard)",
            "Varied (Noise-based)",
            "Blend (Position + Noise)",
            "Fixed (Constant)"
        ])
        freq_layout.addWidget(QLabel("Algorithm:"))
        freq_layout.addWidget(self.frequency_algorithm)

        # Dynamic description label for selected algorithm
        self.frequency_algorithm_description = QLabel()
        self.frequency_algorithm_description.setWordWrap(True)
        self.frequency_algorithm_description.setStyleSheet("color: gray; font-size: 11px; padding: 4px;")
        freq_layout.addWidget(self.frequency_algorithm_description)

        # Varied Range slider (visible only for Varied mode)
        self.varied_range_widget = QWidget()
        varied_range_layout = QHBoxLayout(self.varied_range_widget)
        varied_range_layout.setContentsMargins(0, 0, 0, 0)
        varied_range_layout.addWidget(QLabel("Range:"))
        self.varied_range = QSlider(Qt.Horizontal)
        self.varied_range.setRange(0, 100)
        self.varied_range.setValue(30)
        varied_range_layout.addWidget(self.varied_range)
        self.varied_range_label = QLabel("30%")
        varied_range_layout.addWidget(self.varied_range_label)
        freq_layout.addWidget(self.varied_range_widget)
        self.varied_range_widget.setVisible(False)

        # Blend Ratio slider (visible only for Blend mode)
        self.blend_ratio_widget = QWidget()
        blend_ratio_layout = QHBoxLayout(self.blend_ratio_widget)
        blend_ratio_layout.setContentsMargins(0, 0, 0, 0)
        self.blend_position_label = QLabel("50%")
        blend_ratio_layout.addWidget(self.blend_position_label)
        blend_ratio_layout.addWidget(QLabel("Position"))
        self.blend_ratio = QSlider(Qt.Horizontal)
        self.blend_ratio.setRange(0, 100)
        self.blend_ratio.setValue(50)
        blend_ratio_layout.addWidget(self.blend_ratio)
        blend_ratio_layout.addWidget(QLabel("Noise"))
        self.blend_noise_label = QLabel("50%")
        blend_ratio_layout.addWidget(self.blend_noise_label)
        freq_layout.addWidget(self.blend_ratio_widget)
        self.blend_ratio_widget.setVisible(False)

        # Velocity Factor (integrated into Frequency Options)
        freq_layout.addSpacing(10)

        vel_factor_layout = QHBoxLayout()
        vel_factor_layout.addWidget(QLabel("Velocity Factor:"))
        self.velocity_factor = QSlider(Qt.Horizontal)
        self.velocity_factor.setRange(0, 100)  # 0% to 100%
        self.velocity_factor.setValue(50)
        vel_factor_layout.addWidget(self.velocity_factor)
        self.velocity_factor_label = QLabel("50%")
        vel_factor_layout.addWidget(self.velocity_factor_label)
        freq_layout.addLayout(vel_factor_layout)

        # Velocity timeframe setting
        timeframe_layout = QHBoxLayout()
        timeframe_layout.addWidget(QLabel("Timeframe:"))
        self.velocity_timeframe = QSpinBox()
        self.velocity_timeframe.setRange(1, 60)  # 1 to 60 seconds
        self.velocity_timeframe.setValue(5)
        self.velocity_timeframe.setSuffix(" sec")
        timeframe_layout.addWidget(self.velocity_timeframe)
        timeframe_layout.addStretch()
        freq_layout.addLayout(timeframe_layout)

        freq_layout.addWidget(QLabel("(Faster movement = higher pulse frequency)"))

        # Intensity Options (Regional Throbbing)
        self.intensity_group = QGroupBox("Intensity Options")
        intensity_opts_layout = QVBoxLayout(self.intensity_group)

        # Enable Regional Throbbing checkbox
        self.throbbing_enabled = QCheckBox("Enable Regional Throbbing")
        intensity_opts_layout.addWidget(self.throbbing_enabled)

        # Throbbing Intensity (reduction amount)
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        self.throbbing_intensity = QSlider(Qt.Horizontal)
        self.throbbing_intensity.setRange(0, 100)
        self.throbbing_intensity.setValue(30)
        intensity_layout.addWidget(self.throbbing_intensity)
        self.throbbing_intensity_label = QLabel("0.3")
        intensity_layout.addWidget(self.throbbing_intensity_label)
        intensity_opts_layout.addLayout(intensity_layout)
        
        # Region Thresholds
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("Bottom Region:"))
        self.bottom_threshold = QSlider(Qt.Horizontal)
        self.bottom_threshold.setRange(10, 50)
        self.bottom_threshold.setValue(30)
        bottom_layout.addWidget(self.bottom_threshold)
        self.bottom_threshold_label = QLabel("30%")
        bottom_layout.addWidget(self.bottom_threshold_label)
        intensity_opts_layout.addLayout(bottom_layout)
        
        upper_layout = QHBoxLayout()
        upper_layout.addWidget(QLabel("Upper Region:"))
        self.upper_threshold = QSlider(Qt.Horizontal)
        self.upper_threshold.setRange(50, 90)
        self.upper_threshold.setValue(70)
        upper_layout.addWidget(self.upper_threshold)
        self.upper_threshold_label = QLabel("70%")
        upper_layout.addWidget(self.upper_threshold_label)
        intensity_opts_layout.addLayout(upper_layout)

        # Visual separator between Regional Throbbing and Amplitude settings
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        intensity_opts_layout.addSpacing(8)
        intensity_opts_layout.addWidget(separator)
        intensity_opts_layout.addSpacing(4)

        # Base Amplitude slider
        base_amp_layout = QHBoxLayout()
        base_amp_layout.addWidget(QLabel("Base Amplitude:"))
        self.base_amplitude = QSlider(Qt.Horizontal)
        self.base_amplitude.setRange(0, 100)
        self.base_amplitude.setValue(60)
        base_amp_layout.addWidget(self.base_amplitude)
        self.base_amplitude_label = QLabel("60%")
        base_amp_layout.addWidget(self.base_amplitude_label)
        intensity_opts_layout.addLayout(base_amp_layout)

        # Extreme Boost slider
        extreme_boost_layout = QHBoxLayout()
        extreme_boost_layout.addWidget(QLabel("Extreme Boost:"))
        self.extreme_boost = QSlider(Qt.Horizontal)
        self.extreme_boost.setRange(0, 100)
        self.extreme_boost.setValue(30)
        extreme_boost_layout.addWidget(self.extreme_boost)
        self.extreme_boost_label = QLabel("30%")
        extreme_boost_layout.addWidget(self.extreme_boost_label)
        intensity_opts_layout.addLayout(extreme_boost_layout)
        intensity_opts_layout.addWidget(QLabel("(Extra intensity at position extremes)"))

        # Dynamic Volume Controls
        self.volume_group = QGroupBox("Dynamic Volume")
        volume_layout = QVBoxLayout(self.volume_group)

        self.dynamic_volume_enabled = QCheckBox("Enable Dynamic Volume")
        self.dynamic_volume_enabled.setChecked(True)
        volume_layout.addWidget(self.dynamic_volume_enabled)
        
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("Sensitivity:"))
        self.dynamic_sensitivity = QSlider(Qt.Horizontal)
        self.dynamic_sensitivity.setRange(0, 100)
        self.dynamic_sensitivity.setValue(50)
        sensitivity_layout.addWidget(self.dynamic_sensitivity)
        self.sensitivity_label = QLabel("0.5")
        sensitivity_layout.addWidget(self.sensitivity_label)
        volume_layout.addLayout(sensitivity_layout)
        
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Time Window:"))
        self.window_size = QSpinBox()
        self.window_size.setRange(1, 300)  # Up to 5 minutes
        self.window_size.setValue(2)
        self.window_size.setSuffix(" sec")
        window_layout.addWidget(self.window_size)
        window_layout.addStretch()
        volume_layout.addLayout(window_layout)

        # Mix ratio slider (velocity vs stroke count)
        mix_layout = QHBoxLayout()
        self.strokes_ratio_label = QLabel("50%")
        mix_layout.addWidget(self.strokes_ratio_label)
        mix_layout.addWidget(QLabel("Strokes"))
        self.mix_ratio = QSlider(Qt.Horizontal)
        self.mix_ratio.setRange(0, 100)
        self.mix_ratio.setValue(50)
        mix_layout.addWidget(self.mix_ratio)
        mix_layout.addWidget(QLabel("Velocity"))
        self.mix_ratio_label = QLabel("50%")
        mix_layout.addWidget(self.mix_ratio_label)
        volume_layout.addLayout(mix_layout)
        volume_layout.addWidget(QLabel("(Balance between stroke count and velocity detection)"))

        # Pause Fade Controls
        fade_group = QGroupBox("Pause Fade")
        fade_layout = QVBoxLayout(fade_group)

        fade_layout.addWidget(QLabel("Smooth fade when movement stops/starts"))

        # Fade out time
        fade_out_layout = QHBoxLayout()
        fade_out_layout.addWidget(QLabel("Fade Out:"))
        self.fade_out_time = QSpinBox()
        self.fade_out_time.setRange(0, 2000)  # 0 to 2000ms
        self.fade_out_time.setSingleStep(50)
        self.fade_out_time.setValue(300)
        self.fade_out_time.setSuffix(" ms")
        fade_out_layout.addWidget(self.fade_out_time)
        fade_out_layout.addStretch()
        fade_layout.addLayout(fade_out_layout)

        # Fade in time
        fade_in_layout = QHBoxLayout()
        fade_in_layout.addWidget(QLabel("Fade In:"))
        self.fade_in_time = QSpinBox()
        self.fade_in_time.setRange(0, 2000)  # 0 to 2000ms
        self.fade_in_time.setSingleStep(50)
        self.fade_in_time.setValue(100)
        self.fade_in_time.setSuffix(" ms")
        fade_in_layout.addWidget(self.fade_in_time)
        fade_in_layout.addStretch()
        fade_layout.addLayout(fade_in_layout)

        # Add all groups to main layout
        layout.addWidget(freq_group)
        layout.addWidget(self.intensity_group)
        layout.addWidget(self.volume_group)
        layout.addWidget(fade_group)
        layout.addStretch()

        # Connect signals
        self.throbbing_intensity.valueChanged.connect(self.update_throbbing_labels)
        self.bottom_threshold.valueChanged.connect(self.update_region_labels)
        self.upper_threshold.valueChanged.connect(self.update_region_labels)
        self.dynamic_sensitivity.valueChanged.connect(self.update_sensitivity_label)
        self.velocity_factor.valueChanged.connect(self.update_velocity_factor_label)
        self.base_amplitude.valueChanged.connect(self.update_amplitude_labels)
        self.extreme_boost.valueChanged.connect(self.update_amplitude_labels)
        self.mix_ratio.valueChanged.connect(self.update_mix_ratio_label)
        self.frequency_algorithm.currentTextChanged.connect(self._update_algorithm_description)
        self.varied_range.valueChanged.connect(self._update_varied_range_label)
        self.blend_ratio.valueChanged.connect(self._update_blend_ratio_label)

        # Apply tooltips and initialize description
        self._apply_tooltips()
        self._update_algorithm_description()
        
    def update_throbbing_labels(self, value):
        """Update throbbing intensity label"""
        self.throbbing_intensity_label.setText(f"{value/100:.2f}")
        
    def update_region_labels(self):
        """Update region threshold labels"""
        self.bottom_threshold_label.setText(f"{self.bottom_threshold.value()}%")
        self.upper_threshold_label.setText(f"{self.upper_threshold.value()}%")
        
    def update_sensitivity_label(self, value):
        """Update sensitivity label"""
        self.sensitivity_label.setText(f"{value/100:.2f}")

    def update_velocity_factor_label(self, value):
        """Update velocity factor label"""
        self.velocity_factor_label.setText(f"{value}%")

    def update_amplitude_labels(self):
        """Update base amplitude and extreme boost labels"""
        self.base_amplitude_label.setText(f"{self.base_amplitude.value()}%")
        self.extreme_boost_label.setText(f"{self.extreme_boost.value()}%")

    def update_mix_ratio_label(self, value):
        """Update mix ratio labels (strokes and velocity)"""
        self.mix_ratio_label.setText(f"{value}%")
        self.strokes_ratio_label.setText(f"{100 - value}%")

    def _update_varied_range_label(self, value):
        """Update varied range label"""
        self.varied_range_label.setText(f"{value}%")

    def _update_blend_ratio_label(self, value):
        """Update blend ratio labels"""
        self.blend_noise_label.setText(f"{value}%")
        self.blend_position_label.setText(f"{100 - value}%")

    def setup_device(self, device):
        """Setup connection to Coyote device (for Motion Algorithm)"""
        # For now, this is a placeholder to prevent errors
        pass

    def bind_to_settings(self):
        """Bind all controls to settings"""
        # Frequency algorithm
        current_algorithm = settings.COYOTE_MOTION_FREQUENCY_ALGORITHM.get()
        index = self.frequency_algorithm.findText(current_algorithm)
        if index >= 0:
            self.frequency_algorithm.setCurrentIndex(index)
            
        # Throbbing settings
        self.throbbing_enabled.setChecked(settings.COYOTE_MOTION_THROBBING_ENABLED.get())
        self.throbbing_intensity.setValue(int(settings.COYOTE_MOTION_THROBBING_INTENSITY.get() * 100))
        self.bottom_threshold.setValue(int(settings.COYOTE_MOTION_BOTTOM_REGION_THRESHOLD.get() * 100))
        self.upper_threshold.setValue(int(settings.COYOTE_MOTION_UPPER_REGION_THRESHOLD.get() * 100))
        
        # Velocity-to-frequency settings
        self.velocity_factor.setValue(int(settings.COYOTE_MOTION_FREQUENCY_VELOCITY_FACTOR.get() * 100))
        self.velocity_timeframe.setValue(int(settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()))

        # Dynamic volume settings
        self.dynamic_volume_enabled.setChecked(settings.COYOTE_MOTION_DYNAMIC_VOLUME_ENABLED.get())
        self.dynamic_sensitivity.setValue(int(settings.COYOTE_MOTION_DYNAMIC_SENSITIVITY.get() * 100))
        self.window_size.setValue(int(settings.COYOTE_MOTION_DYNAMIC_WINDOW_SIZE.get()))
        self.mix_ratio.setValue(int(settings.COYOTE_MOTION_DYNAMIC_MIX_RATIO.get() * 100))
        
        # Connect change signals to save settings
        self.frequency_algorithm.currentTextChanged.connect(
            lambda text: settings.COYOTE_MOTION_FREQUENCY_ALGORITHM.set(text)
        )
        self.throbbing_enabled.toggled.connect(
            settings.COYOTE_MOTION_THROBBING_ENABLED.set
        )
        self.throbbing_intensity.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_THROBBING_INTENSITY.set(value / 100.0)
        )
        self.bottom_threshold.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_BOTTOM_REGION_THRESHOLD.set(value / 100.0)
        )
        self.upper_threshold.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_UPPER_REGION_THRESHOLD.set(value / 100.0)
        )
        self.velocity_factor.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_FREQUENCY_VELOCITY_FACTOR.set(value / 100.0)
        )
        self.velocity_timeframe.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.set(float(value))
        )
        self.dynamic_volume_enabled.toggled.connect(
            settings.COYOTE_MOTION_DYNAMIC_VOLUME_ENABLED.set
        )
        self.dynamic_sensitivity.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_DYNAMIC_SENSITIVITY.set(value / 100.0)
        )
        self.window_size.valueChanged.connect(
            settings.COYOTE_MOTION_DYNAMIC_WINDOW_SIZE.set
        )
        self.mix_ratio.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_DYNAMIC_MIX_RATIO.set(value / 100.0)
        )

        # Amplitude settings
        self.base_amplitude.setValue(int(settings.COYOTE_MOTION_BASE_AMPLITUDE.get() * 100))
        self.extreme_boost.setValue(int(settings.COYOTE_MOTION_EXTREME_BOOST.get() * 100))

        self.base_amplitude.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_BASE_AMPLITUDE.set(value / 100.0)
        )
        self.extreme_boost.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_EXTREME_BOOST.set(value / 100.0)
        )

        # Fade settings (stored in seconds, displayed as milliseconds)
        self.fade_out_time.setValue(int(settings.COYOTE_MOTION_FADE_OUT_TIME.get() * 1000))
        self.fade_in_time.setValue(int(settings.COYOTE_MOTION_FADE_IN_TIME.get() * 1000))

        self.fade_out_time.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_FADE_OUT_TIME.set(value / 1000.0)
        )
        self.fade_in_time.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_FADE_IN_TIME.set(value / 1000.0)
        )

        # Algorithm-specific settings
        self.varied_range.setValue(int(settings.COYOTE_MOTION_VARIED_RANGE.get() * 100))
        self.blend_ratio.setValue(int(settings.COYOTE_MOTION_BLEND_RATIO.get() * 100))

        self.varied_range.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_VARIED_RANGE.set(value / 100.0)
        )
        self.blend_ratio.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_BLEND_RATIO.set(value / 100.0)
        )

    def _apply_tooltips(self):
        """Apply tooltip text to all controls"""
        # Frequency Options group
        self.frequency_algorithm.setToolTip(TOOLTIP_FREQUENCY_ALGORITHM)
        self.varied_range.setToolTip(TOOLTIP_VARIED_RANGE)
        self.blend_ratio.setToolTip(TOOLTIP_BLEND_RATIO)
        self.velocity_factor.setToolTip(TOOLTIP_VELOCITY_FACTOR)
        self.velocity_timeframe.setToolTip(TOOLTIP_VELOCITY_TIMEFRAME)

        # Intensity Options group
        self.throbbing_enabled.setToolTip(TOOLTIP_THROBBING_ENABLED)
        self.throbbing_intensity.setToolTip(TOOLTIP_THROBBING_INTENSITY)
        self.bottom_threshold.setToolTip(TOOLTIP_BOTTOM_THRESHOLD)
        self.upper_threshold.setToolTip(TOOLTIP_UPPER_THRESHOLD)
        self.base_amplitude.setToolTip(TOOLTIP_BASE_AMPLITUDE)
        self.extreme_boost.setToolTip(TOOLTIP_EXTREME_BOOST)

        # Dynamic Volume group
        self.dynamic_volume_enabled.setToolTip(TOOLTIP_DYNAMIC_VOLUME_ENABLED)
        self.dynamic_sensitivity.setToolTip(TOOLTIP_DYNAMIC_SENSITIVITY)
        self.window_size.setToolTip(TOOLTIP_WINDOW_SIZE)
        self.mix_ratio.setToolTip(TOOLTIP_MIX_RATIO)

        # Pause Fade group
        self.fade_out_time.setToolTip(TOOLTIP_FADE_OUT_TIME)
        self.fade_in_time.setToolTip(TOOLTIP_FADE_IN_TIME)

    def _update_algorithm_description(self):
        """Update the description label and show/hide algorithm-specific sliders"""
        selected = self.frequency_algorithm.currentText()
        description = FREQ_ALGO_DESCRIPTIONS.get(selected, "")
        self.frequency_algorithm_description.setText(description)

        # Show/hide algorithm-specific sliders
        # Range slider visible for both Varied and Blend (since Blend uses the noise component)
        self.varied_range_widget.setVisible("Varied" in selected or "Blend" in selected)
        self.blend_ratio_widget.setVisible("Blend" in selected)

    def cleanup(self):
        """Cleanup resources when closing"""
        pass