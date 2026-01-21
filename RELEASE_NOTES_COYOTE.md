# Release Notes: Coyote 3.0 Support (Beta)

## New Feature: DG-LAB Coyote 3.0 Support

This release adds support for the DG-LAB Coyote 3.0 e-stim device via Bluetooth Low Energy (BLE).

### Key Features

- **Two independent output channels (A and B)**
- **Two algorithm modes:**
  - **Simulated Three-Phase** - familiar three-phase experience mapped to two channels
  - **Two-Channel** - full 2D position control using alpha and beta axes
- Real-time pulse visualization with frequency-based color coding
- Per-channel configuration: frequency range, strength limits, and balance parameters
- Funscript integration for both channels
- Texture modulation and pulse jitter for varied sensations
- Battery level monitoring
- Automatic reconnection on connection loss

### Requirements

- Windows with Bluetooth Low Energy support
- DG-LAB Coyote 3.0 device

---

## Test Questions

Please provide feedback on the following areas:

### Connection & Setup

1. Does the device appear in the device selection wizard?
2. Does Bluetooth scanning find your Coyote device?
3. Does the connection process complete successfully?
4. Is the battery level displayed correctly after connection?
5. Does the "Reset Connection" button work?
6. Does the device reconnect automatically if Bluetooth is briefly interrupted?

### Algorithm Modes

7. Does "Simulated Three-Phase" mode feel similar to traditional three-phase setups?
8. In "Two-Channel" mode, can you feel both channels responding independently?
9. When switching between modes, does the device stay connected?

### Channel Controls

10. Do the volume sliders for Channel A and B work correctly?
11. Does changing frequency range affect the sensation as expected?
12. Does "Max Strength" properly limit the output intensity?

### Funscript & Media Integration

13. Does funscript playback control the device correctly?
14. Do both channels respond appropriately to position changes?
15. Does pausing playback stop the output without disconnecting?

### Sensation Quality

16. How would you rate the overall sensation quality (1-5)?
17. Are the default frequency ranges good starting points?
18. Is intensity smoothing appropriate, or are transitions too abrupt/slow?

### Issues & Stability

19. Did you experience any unexpected disconnections?
20. Did the application crash or freeze at any point?
21. Does the device shut down safely when closing the application?

### General Feedback

22. What features are missing that you'd like to see?
23. Any other comments or suggestions?

---

Please report any issues or feedback!
