# Coyote 3.0 Implementation Decisions

## Source Repositories
- **diglet48-restim-original/** - Original Restim by diglet48 (v1.52, 277 commits) - NO COYOTE SUPPORT
- **voltmouse69-restim/** (master branch) - Simpler, single-algorithm approach (307 commits)
- **breadfan69-restim/** (master branch) - Dual-algorithm with robust connection handling (375 commits)
- **breadfan69-restim-main/** (main branch) - Runtime mode switching, UI improvements

## Original vs Forks

The original diglet48/restim does **NOT** have Coyote 3.0 support. It only includes:
- `device/audio/` - Audio output devices
- `device/focstim/` - FocStim device support
- `device/neostim/` - NeoStim device support

Both voltmouse69 and breadfan69 independently added the `device/coyote/` directory with full Coyote 3.0 BLE support.

**Base for merging:** To create a PR for diglet48's original, the entire `device/coyote/` directory and related UI changes need to be added.

---

## DECISION SUMMARY

### Algorithm Layer: USE breadfan69 (master)
**File:** `device/coyote/algorithm.py`

**Reasoning:**
- Clean OOP design with abstract base class and two concrete implementations
- Proper separation: `CoyoteThreePhaseAlgorithm` (exponential) and `CoyoteTwoChannelAlgorithm` (barycentric)
- Follows single-responsibility principle
- Easy to extend with new algorithms

**Key code to preserve:**
```python
class CoyoteAlgorithm:
    def _positional_intensity(self, time_s: float, volume: float) -> Tuple[int, int]:
        """Override in subclasses to provide algorithm-specific intensity calculation."""
        raise NotImplementedError("Subclasses must implement _positional_intensity")

class CoyoteThreePhaseAlgorithm(CoyoteAlgorithm):
    """Simulated three-phase mode using power-law exponential scaling."""
    # Uses: p ** exponent mapping with balance calibration

class CoyoteTwoChannelAlgorithm(CoyoteAlgorithm):
    """Two-channel mode using barycentric weighted algorithm."""
    # Uses: w_left, w_right, w_neutral barycentric weights
```

---

### Device Layer: USE breadfan69 (master) WITH modifications from (main)
**File:** `device/coyote/device.py`

**From breadfan69 (master) - KEEP:**
1. **State flags:**
   ```python
   self._had_successful_connection = False
   self._shutdown = False
   self._force_disconnect = False
   self._paused = False  # IMPORTANT: Keep pause support
   ```

2. **Safety reset on connection:**
   ```python
   async def _send_reset_command(self):
       """Send B0 command with both channels set to 0 power for safety"""
       command = bytes([CMD_B0, 0x00, 0, 0] + [0] * B0_NO_PULSES_PAD_BYTES)
       await self.client.write_gatt_char(WRITE_CHAR_UUID, command)
   ```

3. **Keep-alive with valid frequencies (prevents device timeout):**
   ```python
   # No pulses: use valid minimum values to maintain connection
   command.extend([10, 10, 10, 10])  # Channel A frequencies (valid: 10-240)
   command.extend([0, 0, 0, 0])      # Channel A intensities (0 = no output)
   command.extend([10, 10, 10, 10])  # Channel B frequencies
   command.extend([0, 0, 0, 0])      # Channel B intensities
   ```

4. **Update loop tracking:**
   ```python
   self._update_loop_running = True
   # Prevents multiple update loops from being scheduled
   ```

5. **BLE retry logic:**
   ```python
   max_retries = 3
   retry_delay = 0.05  # 50ms
   for attempt in range(max_retries):
       try:
           await self.client.write_gatt_char(WRITE_CHAR_UUID, command)
           return True
       except Exception:
           await asyncio.sleep(retry_delay)
   ```

6. **Pause/resume support:**
   ```python
   def stop_updates(self):
       """Pause updates but maintain connection and algorithm"""
       self._paused = True
       # Keep running=True and algorithm to maintain connection
   ```

**From breadfan69 (main) - MERGE IN:**
1. **Reset Connection button support** (add to device.py if not present):
   ```python
   def reset_connection(self):
       """Trigger a connection reset from UI"""
       self._force_disconnect = True
   ```

---

### UI Layer: COMBINE breadfan69 (master) + (main)
**File:** `qt_ui/coyote_settings_widget.py`

**From breadfan69 (main) - ADD:**
1. **Reset Connection button:**
   ```python
   self.button_reset_connection = QPushButton("Reset Connection")
   self.button_reset_connection.setMaximumWidth(120)
   self.button_reset_connection.clicked.connect(self.on_reset_connection_clicked)

   def on_reset_connection_clicked(self):
       if self.device:
           self.device.reset_connection()
   ```

2. **Cleanup method:**
   ```python
   def cleanup(self):
       """Clean up widget resources when device is being switched"""
       if self.device:
           self.device.connection_status_changed.disconnect(self.on_connection_status_changed)
           self.device.battery_level_changed.disconnect(self.on_battery_level_changed)
           self.device.parameters_changed.disconnect(self.on_parameters_changed)
           self.device.power_levels_changed.disconnect(self.on_power_levels_changed)
           self.device.pulse_sent.disconnect(self.on_pulse_sent)
           self.device = None
   ```

**From breadfan69 (master) - KEEP:**
- Strength control disabled from UI (let algorithm control)
- Comment explains why:
  ```python
  def update_channel_strength(self, control, value):
      # Don't send strength commands from UI - let the algorithm control output
      # Every Coyote packet must have both intensity AND pulse frequency, or it's rejected
      pass
  ```

---

### Packet Timing: USE voltmouse69 adaptive approach
**File:** `device/coyote/algorithm.py`

**Reasoning:** Adaptive timing may provide smoother transitions than fixed 100ms

**From voltmouse69:**
```python
# In generate_packet():
durations = [duration for duration in duration_map.values() if duration > 0]
if not durations:
    durations = [1]
min_duration_ms = max(1, min(durations))
self.next_update_time = current_time + (min_duration_ms / 1000.0) * self.tuning.packet_margin

# In _schedule_from_remaining():
remaining = min(channel.state.remaining_ms() for channel in self._channels)
self.next_update_time = current_time + (remaining / 1000.0) * self.tuning.packet_margin
```

**Instead of breadfan69's fixed:**
```python
self.next_update_time = current_time + 0.1  # Always 100ms
```

---

### Supporting Files: USE voltmouse69 versions
These files are nearly identical across all versions, voltmouse69 is slightly cleaner:

- `device/coyote/channel_controller.py` - voltmouse69 (153 lines vs 135)
- `device/coyote/channel_state.py` - Any (identical)
- `device/coyote/common.py` - Any (identical)
- `device/coyote/config.py` - Any (identical)
- `device/coyote/constants.py` - Any (identical)
- `device/coyote/pulse_generator.py` - voltmouse69 (205 lines, more complete)
- `device/coyote/types.py` - Any (identical)

---

### Algorithm Factory: USE breadfan69 (master)
**File:** `qt_ui/algorithm_factory.py`

**Reasoning:** Must support dual algorithm classes

**Key code:**
```python
def create_coyote(self, ...):
    if device_type == DeviceType.COYOTE_THREE_PHASE:
        return CoyoteThreePhaseAlgorithm(...)
    else:  # COYOTE_TWO_CHANNEL
        return CoyoteTwoChannelAlgorithm(...)
```

---

## FINAL FILE MAPPING

| Component | Source | File |
|-----------|--------|------|
| algorithm.py | breadfan69 (master) | Keep dual-class design |
| device.py | breadfan69 (master) + (main) | Merge reset button support |
| coyote_settings_widget.py | breadfan69 (master) + (main) | Add reset button, cleanup |
| algorithm_factory.py | breadfan69 (master) | Support dual algorithms |
| channel_controller.py | voltmouse69 | Slightly more complete |
| pulse_generator.py | voltmouse69 | More complete (205 vs 180 lines) |
| Other coyote/*.py | Any | Identical across versions |

---

## ISSUES TO FIX

### breadfan69 (main) - Dead code
**File:** `algorithm.py` lines 152-154
```python
return intensity_a, intensity_b
# Lines below are unreachable:
self._last_update_time: Optional[float] = None
self.next_update_time: float = 0.0
self._start_time: Optional[float] = None
```
**Fix:** Remove dead code, these are duplicated from __init__

---

## IMPLEMENTATION CHECKLIST

When implementing the final version:

1. [ ] Start with breadfan69 (master) as base
2. [ ] Replace packet timing with voltmouse69 adaptive approach
3. [ ] Add Reset Connection button from breadfan69 (main)
4. [ ] Add cleanup() method from breadfan69 (main)
5. [ ] Use voltmouse69's pulse_generator.py and channel_controller.py
6. [ ] Test both algorithm modes (3-phase and 2-channel)
7. [ ] Test connection stability (disconnect/reconnect)
8. [ ] Test pause/resume functionality
9. [ ] Verify keep-alive packets work correctly

---

## QUICK REFERENCE: Key Differences

| Aspect | voltmouse69 | breadfan69 (master) | breadfan69 (main) |
|--------|-------------|---------------------|-------------------|
| Algorithm classes | 1 | 2 | 1 (with conditionals) |
| Packet timing | Adaptive | Fixed 100ms | Fixed 100ms |
| Safety reset | No | Yes | No |
| Pause support | No | Yes | No |
| Keep-alive | No | Valid freq+0 intensity | Zero padding |
| Reset button | No | No | Yes |
| Cleanup method | No | No | Yes |
| BLE retries | No | Yes | Yes |

**Best combination:** breadfan69 (master) architecture + voltmouse69 timing + breadfan69 (main) UI features

---

## FILES TO ADD TO ORIGINAL RESTIM (diglet48)

To integrate Coyote 3.0 support into diglet48's original restim, these files/changes are needed:

### New Files (entire directory)
```
device/coyote/
├── __init__.py          (if needed)
├── algorithm.py         ← from breadfan69 (master) + voltmouse69 timing
├── channel_controller.py ← from voltmouse69
├── channel_state.py     ← any version
├── common.py            ← any version
├── config.py            ← any version
├── constants.py         ← any version
├── device.py            ← from breadfan69 (master) + (main) UI hooks
├── pulse_generator.py   ← from voltmouse69
└── types.py             ← any version
```

### New UI Files
```
qt_ui/coyote_settings_widget.py    ← combined breadfan69 (master) + (main)
qt_ui/device_wizard/coyote_waveform_select.py
```

### Modified Files (need careful merging)
```
qt_ui/mainwindow.py          ← Add Coyote device initialization, tab visibility
qt_ui/algorithm_factory.py   ← Add create_coyote() method
qt_ui/settings.py            ← Add Coyote settings (channel limits, freq ranges, etc.)
qt_ui/device_wizard/type_select.py  ← Add COYOTE_THREE_PHASE, COYOTE_TWO_CHANNEL options
stim_math/audio_gen/params.py       ← Add CoyoteAlgorithmParams, CoyoteChannelParams
requirements.txt             ← Add 'bleak' for BLE support
```

### Dependencies to Add
```
bleak          # Bluetooth Low Energy library
numpy          # Already in original, but verify version
```
