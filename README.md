# Restim

Restim is a realtime e-stim signal generator for multi-electrode setups.

Refer to the [wiki](https://github.com/diglet48/restim/wiki) for help.

## Supported hardware

* Stereostim (three-phase only) and other audio-based devices (Mk312, 2B, ...)
* FOC-Stim
* NeoDK (coming soon)
* **DG-LAB Coyote 3.0** (new!)

## Main features

* Control e-stim signals with funscript or user interface.
* Synchronize e-stim with video or games.
* Calibrate signal for your preferred electrode configuration.

---

## DG-LAB Coyote 3.0 Integration

This fork adds full support for the DG-LAB Coyote 3.0 e-stim device via Bluetooth Low Energy (BLE).

### Two Operating Modes

The Coyote integration offers two distinct algorithms, selectable during device setup:

**Simulated Three-Phase Mode**
- Uses a power-law exponential scaling approach
- Maps the alpha axis (left-right position) to channel intensity balance
- Best for users who want a familiar three-phase-like experience on the two-channel Coyote hardware
- Visualization uses a simplified 1D horizontal slider showing A/B balance

**Two-Channel Mode**
- Uses barycentric weighting across the full 2D position space
- Takes advantage of both alpha and beta axes for more nuanced control
- Better suited for content that uses the complete position range
- Visualization uses the full 2D three-phase diagram

### Features

- **Real-time pulse visualization** - See exactly what pulses are being sent to each channel with color-coded frequency display (green = low frequency, red = high frequency)
- **Per-channel configuration** - Set independent frequency ranges and strength limits for channels A and B
- **Battery level monitoring** - View device battery status directly in the UI
- **Connection resilience** - Automatic retry logic and keep-alive packets maintain stable connections
- **Reset Connection button** - Quickly recover from connection issues without restarting
- **Pattern generator support** - All built-in motion patterns work with the Coyote device
- **Funscript synchronization** - Full support for funscript-driven control
- **Calibration controls** - Fine-tune the balance between channels and overall intensity scaling

### Credits & Sources

This integration combines work from multiple community forks of Restim:

| Feature | Source | Reason |
|---------|--------|--------|
| Dual algorithm architecture | breadfan69 (master) | Clean object-oriented design with separate classes for each mode |
| Adaptive packet timing | voltmouse69 | Smoother transitions by timing packets based on pulse duration |
| Device communication | breadfan69 (master) | Robust BLE handling with safety reset, pause support, and retry logic |
| Pulse generator | voltmouse69 | More complete implementation |
| Reset Connection button | breadfan69 (main) | User-requested feature for easier recovery |
| UI cleanup handling | breadfan69 (main) | Proper resource cleanup when switching devices |

The original Restim by diglet48 did not include Coyote support. Both voltmouse69 and breadfan69 independently developed Coyote integrations, and this fork merges the best aspects of both approaches.

---

## Installation

**Windows**: download the latest release package: https://github.com/Harlekin7/restim/releases

**Linux/mac**: make sure python 3.10 or newer is installed on your system.
Download the Restim source code, and execute `run.sh`

**Developers**: install PyCharm and python 3.10 or newer.
Open Settings, python interpreter, and configure a new venv.
Navigate to requirements.txt and install the dependencies. Then run restim.py.

### Additional Requirements for Coyote Support

The Coyote integration requires the `bleak` library for Bluetooth Low Energy communication. This is included in the updated requirements.txt.
