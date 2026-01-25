from PySide6.QtWidgets import QWizardPage

from qt_ui.device_wizard.coyote_waveform_select_ui import Ui_WizardPageCoyote


# Description text for each mode
THREE_PHASE_DESCRIPTION = """<b>Supported funscripts:</b>
<table>
<tr><td>L0 (volume)</td><td>Yes</td></tr>
<tr><td>L1 (alpha)</td><td>Yes - channel balance</td></tr>
<tr><td>L2 (beta)</td><td><i>Ignored</i></td></tr>
<tr><td>Pulse Frequency</td><td>Yes</td></tr>
<tr><td>Pulse Width</td><td>Yes</td></tr>
</table>"""

TWO_CHANNEL_DESCRIPTION = """<b>Supported funscripts:</b>
<table>
<tr><td>L0 (volume)</td><td>Yes</td></tr>
<tr><td>L1 (alpha)</td><td>Yes</td></tr>
<tr><td>L2 (beta)</td><td>Yes - channel balance</td></tr>
<tr><td>Pulse Frequency</td><td>Yes</td></tr>
<tr><td>Pulse Width</td><td>Yes</td></tr>
</table>"""

MOTION_ALGORITHM_DESCRIPTION = """<b>Motion Algorithm - Enhanced Funscript Conversion</b>
<br><br>
Position-based amplitude with channel distribution for realistic stroke sensation.
<br><br>
<b>Features:</b>
<ul>
<li>Position-based amplitude (60-90% during movement)</li>
<li>Positional channel distribution (sqrt-based A↔B crossfade)</li>
<li>Velocity → Frequency modulation (faster = higher pulse rate)</li>
<li>5 frequency algorithms including regional throbbing</li>
<li>Dynamic volume based on section intensity</li>
</ul>
<b>Supported funscripts:</b>
<table>
<tr><td>V0 (volume)</td><td>Yes - final volume multiplier</td></tr>
<tr><td>L0 (alpha/stroke)</td><td>Yes - primary input (drives everything)</td></tr>
</table>"""


class WizardPageCoyoteWaveformSelect(QWizardPage, Ui_WizardPageCoyote):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.three_phase_radio.toggled.connect(self.completeChanged)
        self.two_channel_radio.toggled.connect(self.completeChanged)
        self.motion_algorithm_radio.toggled.connect(self.completeChanged)
        self.three_phase_radio.toggled.connect(self._update_description)
        self.two_channel_radio.toggled.connect(self._update_description)
        self.motion_algorithm_radio.toggled.connect(self._update_description)

        # Set initial description
        self._update_description()

    def _update_description(self):
        """Update the description label based on selected mode."""
        if self.three_phase_radio.isChecked():
            self.label.setText(THREE_PHASE_DESCRIPTION)
        elif self.two_channel_radio.isChecked():
            self.label.setText(TWO_CHANNEL_DESCRIPTION)
        elif self.motion_algorithm_radio.isChecked():
            self.label.setText(MOTION_ALGORITHM_DESCRIPTION)
        else:
            self.label.setText("Select a mode to see its description.")

    def isComplete(self) -> bool:
        return any([
            self.three_phase_radio.isChecked() and self.three_phase_radio.isEnabled(),
            self.two_channel_radio.isChecked() and self.two_channel_radio.isEnabled(),
            self.motion_algorithm_radio.isChecked() and self.motion_algorithm_radio.isEnabled(),
        ])

    def is_three_phase(self) -> bool:
        """Check if Simulated Three-Phase mode is selected"""
        return self.three_phase_radio.isChecked()

    def is_two_channel(self) -> bool:
        """Check if 2-Channel mode is selected"""
        return self.two_channel_radio.isChecked()

    def is_motion_algorithm(self) -> bool:
        """Check if Motion Algorithm mode is selected"""
        return self.motion_algorithm_radio.isChecked()
