from dataclasses import dataclass
from enum import Enum
from qt_ui import settings


class DeviceType(Enum):
    NONE = 0
    AUDIO_THREE_PHASE = 1
    # AUDIO_FOUR_PHASE = 2
    # AUDIO_FIVE_PHASE = 3
    # MODIFY_EXISTING_THREEPHASE_AUDIO = 4
    FOCSTIM_THREE_PHASE = 5
    NEOSTIM_THREE_PHASE = 6
    FOCSTIM_FOUR_PHASE = 7
    COYOTE_THREE_PHASE = 8
    COYOTE_TWO_CHANNEL = 9
    COYOTE_MOTION_ALGORITHM = 10


class WaveformType(Enum):
    CONTINUOUS = 1
    PULSE_BASED = 2
    A_B_TESTING = 3


@dataclass
class DeviceConfiguration:
    device_type: DeviceType
    waveform_type: WaveformType
    min_frequency: float
    max_frequency: float
    waveform_amplitude_amps: float

    def save(self):
        settings.device_config_device_type.set(self.device_type.value)
        if self.device_type in (DeviceType.AUDIO_THREE_PHASE, DeviceType.FOCSTIM_THREE_PHASE,
                                DeviceType.COYOTE_THREE_PHASE, DeviceType.COYOTE_TWO_CHANNEL,
                                DeviceType.COYOTE_MOTION_ALGORITHM):
            settings.device_config_waveform_type.set(self.waveform_type.value)
            settings.device_config_min_freq.set(float(self.min_frequency))
            settings.device_config_max_freq.set(float(self.max_frequency))
            settings.device_config_waveform_amplitude_amps.set(float(self.waveform_amplitude_amps))

    @staticmethod
    def from_settings():
        return DeviceConfiguration(
            DeviceType(settings.device_config_device_type.get()),
            WaveformType(settings.device_config_waveform_type.get()),
            float(settings.device_config_min_freq.get()),
            float(settings.device_config_max_freq.get()),
            float(settings.device_config_waveform_amplitude_amps.get()),
        )