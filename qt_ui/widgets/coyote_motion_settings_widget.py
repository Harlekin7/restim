from typing import Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QSlider, QCheckBox, QSpinBox,
                             QComboBox)
from PySide6.QtCore import Qt
from qt_ui import settings


class CoyoteMotionSettingsWidget(QWidget):
    """UI settings for Coyote Motion Algorithm enhancement"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.bind_to_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        
        # Frequency Algorithm Selection
        freq_group = QGroupBox("Frequency Algorithm")
        freq_layout = QVBoxLayout(freq_group)
        
        self.frequency_algorithm = QComboBox()
        self.frequency_algorithm.addItems([
            "Position (Standard)",
            "Varied (Noise-based)", 
            "Blend (Position + Noise)",
            "Throbbing (Regional Enhancement)",
            "Fixed (Constant)"
        ])
        freq_layout.addWidget(QLabel("Algorithm:"))
        freq_layout.addWidget(self.frequency_algorithm)
        
        # Throbbing Controls
        self.throbbing_group = QGroupBox("Regional Throbbing")
        throbbing_layout = QVBoxLayout(self.throbbing_group)
        
        # Throbbing Intensity
        intensity_layout = QHBoxLayout()
        intensity_layout.addWidget(QLabel("Intensity:"))
        self.throbbing_intensity = QSlider(Qt.Horizontal)
        self.throbbing_intensity.setRange(0, 100)
        self.throbbing_intensity.setValue(30)
        intensity_layout.addWidget(self.throbbing_intensity)
        self.throbbing_intensity_label = QLabel("0.3")
        intensity_layout.addWidget(self.throbbing_intensity_label)
        throbbing_layout.addLayout(intensity_layout)
        
        # Region Thresholds
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(QLabel("Bottom Region:"))
        self.bottom_threshold = QSlider(Qt.Horizontal)
        self.bottom_threshold.setRange(10, 50)
        self.bottom_threshold.setValue(30)
        bottom_layout.addWidget(self.bottom_threshold)
        self.bottom_threshold_label = QLabel("30%")
        bottom_layout.addWidget(self.bottom_threshold_label)
        throbbing_layout.addLayout(bottom_layout)
        
        upper_layout = QHBoxLayout()
        upper_layout.addWidget(QLabel("Upper Region:"))
        self.upper_threshold = QSlider(Qt.Horizontal)
        self.upper_threshold.setRange(50, 90)
        self.upper_threshold.setValue(70)
        upper_layout.addWidget(self.upper_threshold)
        self.upper_threshold_label = QLabel("70%")
        upper_layout.addWidget(self.upper_threshold_label)
        throbbing_layout.addLayout(upper_layout)
        
        # Velocity-to-Frequency Settings
        vel_freq_group = QGroupBox("Velocity → Frequency")
        vel_freq_layout = QVBoxLayout(vel_freq_group)

        vel_factor_layout = QHBoxLayout()
        vel_factor_layout.addWidget(QLabel("Velocity Factor:"))
        self.velocity_factor = QSlider(Qt.Horizontal)
        self.velocity_factor.setRange(0, 100)  # 0% to 100%
        self.velocity_factor.setValue(50)
        vel_factor_layout.addWidget(self.velocity_factor)
        self.velocity_factor_label = QLabel("50%")
        vel_factor_layout.addWidget(self.velocity_factor_label)
        vel_freq_layout.addLayout(vel_factor_layout)

        # Velocity timeframe setting
        timeframe_layout = QHBoxLayout()
        timeframe_layout.addWidget(QLabel("Timeframe:"))
        self.velocity_timeframe = QSpinBox()
        self.velocity_timeframe.setRange(1, 60)  # 1 to 60 seconds
        self.velocity_timeframe.setValue(5)
        self.velocity_timeframe.setSuffix(" sec")
        timeframe_layout.addWidget(self.velocity_timeframe)
        timeframe_layout.addStretch()
        vel_freq_layout.addLayout(timeframe_layout)

        vel_freq_layout.addWidget(QLabel("(Faster movement = higher pulse frequency)"))

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
        mix_layout.addWidget(QLabel("Strokes"))
        self.mix_ratio = QSlider(Qt.Horizontal)
        self.mix_ratio.setRange(0, 100)
        self.mix_ratio.setValue(50)
        mix_layout.addWidget(self.mix_ratio)
        mix_layout.addWidget(QLabel("Velocity"))
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
        layout.addWidget(self.throbbing_group)
        layout.addWidget(vel_freq_group)
        layout.addWidget(self.volume_group)
        layout.addWidget(fade_group)
        layout.addStretch()

        # Connect signals
        self.frequency_algorithm.currentTextChanged.connect(self.on_algorithm_changed)
        self.throbbing_intensity.valueChanged.connect(self.update_throbbing_labels)
        self.bottom_threshold.valueChanged.connect(self.update_region_labels)
        self.upper_threshold.valueChanged.connect(self.update_region_labels)
        self.dynamic_sensitivity.valueChanged.connect(self.update_sensitivity_label)
        self.velocity_factor.valueChanged.connect(self.update_velocity_factor_label)
        
    def on_algorithm_changed(self, algorithm):
        """Show/hide throbbing controls based on selection"""
        show_throbbing = "Throbbing" in algorithm
        self.throbbing_group.setVisible(show_throbbing)
        
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

        # Fade settings (stored in seconds, displayed as milliseconds)
        self.fade_out_time.setValue(int(settings.COYOTE_MOTION_FADE_OUT_TIME.get() * 1000))
        self.fade_in_time.setValue(int(settings.COYOTE_MOTION_FADE_IN_TIME.get() * 1000))

        self.fade_out_time.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_FADE_OUT_TIME.set(value / 1000.0)
        )
        self.fade_in_time.valueChanged.connect(
            lambda value: settings.COYOTE_MOTION_FADE_IN_TIME.set(value / 1000.0)
        )

    def cleanup(self):
        """Cleanup resources when closing"""
        pass