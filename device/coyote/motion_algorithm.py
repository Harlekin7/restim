import logging
import math
import numpy as np
from typing import Dict, List, Optional, Tuple

from device.coyote.algorithm import CoyoteAlgorithm
from device.coyote.common import clamp, normalize
from device.coyote.constants import (
    HARDWARE_MIN_FREQ_HZ, HARDWARE_MAX_FREQ_HZ,
    MIN_PULSE_DURATION_MS, MAX_PULSE_DURATION_MS
)
from device.coyote.types import CoyotePulse, CoyotePulses
from stim_math.axis import AbstractAxis, AbstractTimestampMapper, LinearInterpolator
from stim_math.audio_gen.params import CoyoteMotionAlgorithmParams
from qt_ui import settings

logger = logging.getLogger("restim.coyote.motion")


class CoyoteMotionAlgorithm(CoyoteAlgorithm):
    """Motion Algorithm with enhanced funscript conversion for Coyote devices"""

    def __init__(self, media, params: CoyoteMotionAlgorithmParams, safety_limits,
                 carrier_freq_limits, pulse_freq_limits, pulse_width_limits,
                 pulse_rise_time_limits, timestamp_mapper: AbstractTimestampMapper = None,
                 tuning=None, skip_texture_and_residual=True):

        super().__init__(media, params, safety_limits, carrier_freq_limits,
                        pulse_freq_limits, pulse_width_limits, pulse_rise_time_limits,
                        tuning, skip_texture_and_residual)

        self.motion_params = params
        self.timestamp_mapper = timestamp_mapper

        # Motion Algorithm specific state
        self.velocity_history = []
        self.acceleration_history = []
        self.time_history = []

        # Dynamic volume state - velocity and stroke tracking for section intensity
        self.dynamic_velocity_history = []  # List of (timestamp, velocity) tuples
        self.last_velocity_sign = 0  # For detecting direction changes
        self.direction_change_times = []  # Timestamps of direction changes (strokes)

        # Auto-calibrated values from funscript
        self.calibrated_max_speed = 5.0  # Default, will be updated from funscript
        self.calibrated_max_magnitude = 80.0  # Default, will be updated from funscript
        self.calibrated_max_stroke_rate = 2.0  # Max strokes per second, updated from funscript

        # Current dynamic volume (updated each pulse, used for both output and UI)
        self.current_dynamic_volume = 1.0

        # Real-time velocity tracking for accurate movement detection
        self._prev_position = None
        self._prev_position_time = None
        self._realtime_velocity = 0.0

        # Fade state for smooth transitions when movement stops/starts
        self._fade_level = 0.0  # 0 = fully faded out, 1 = fully active
        self._last_fade_time = None
        self._is_moving = False

        # Precompute velocity and acceleration for better performance
        self._precompute_motion_data()
        
    def _precompute_motion_data(self):
        """Precompute velocity and acceleration from funscript data"""
        # Get position data from alpha axis (funscript)
        alpha_axis = self.motion_params.position.alpha
        logger.info(f"Motion Algorithm: Checking alpha axis type: {type(alpha_axis).__name__}")

        if hasattr(alpha_axis, 'timeline'):
            positions = alpha_axis.timeline.y()
            times = alpha_axis.timeline.x()
            logger.info(f"Motion Algorithm: Found timeline with {len(positions)} position points")

            # Check if we have enough data to compute gradients
            if len(positions) < 2 or len(times) < 2:
                # No funscript data - use defaults
                logger.warning("Motion Algorithm: Funscript has less than 2 points, using defaults")
                self.position_data = [(0.0, 0.5)]
                self.velocity_data = [(0.0, 0.0)]
                self.acceleration_data = [(0.0, 0.0)]
                return

            # Calculate velocity using numpy gradient
            velocities = np.gradient(positions, times)

            # Calculate acceleration using gradient of velocity
            accelerations = np.gradient(velocities, times)

            # Store for quick lookup
            self.position_data = list(zip(times, positions))
            self.velocity_data = list(zip(times, velocities))
            self.acceleration_data = list(zip(times, accelerations))

            logger.info(f"Motion Algorithm: Loaded funscript with {len(self.position_data)} points, "
                       f"time range: {times[0]:.2f}s - {times[-1]:.2f}s")

            # Auto-calibrate max speed and magnitude from the funscript
            # Use 95th percentile to avoid outliers skewing the range
            speeds = np.abs(velocities)
            magnitudes = np.abs(accelerations)
            self.calibrated_max_speed = max(np.percentile(speeds, 95), 0.5)  # At least 0.5
            self.calibrated_max_magnitude = max(np.percentile(magnitudes, 95), 5.0)  # At least 5.0
            logger.info(f"Motion Algorithm: Auto-calibrated from funscript: "
                       f"max_speed={self.calibrated_max_speed:.2f}, max_magnitude={self.calibrated_max_magnitude:.2f}")

            # Calculate min/max amplitude across the entire funscript for dynamic volume normalization
            self._precompute_amplitude_range(velocities, accelerations)
        else:
            # No timeline data - use defaults
            logger.warning(f"Motion Algorithm: No funscript loaded (axis has no 'timeline' attribute). "
                          f"Load a funscript mapped to Position Alpha for motion output.")
            self.position_data = [(0.0, 0.5)]
            self.velocity_data = [(0.0, 0.0)]
            self.acceleration_data = [(0.0, 0.0)]

    def _precompute_amplitude_range(self, velocities: np.ndarray, accelerations: np.ndarray):
        """Calculate calibration values for dynamic volume normalization.

        Calculates the max average velocity by scanning windows across the funscript.
        This prevents a single fast spike from dominating the entire range.
        Uses the same timeframe setting as the velocity factor for consistency.
        """
        # Store velocities for potential recalibration later
        self._cached_velocities = velocities

        self._recalibrate_velocity_range()

        # Count direction changes for stroke rate calculation
        times = [p[0] for p in self.position_data]
        time_span = times[-1] - times[0] if len(times) > 1 else 1.0

        direction_changes = 0
        last_sign = 0
        for vel in velocities:
            current_sign = 1 if vel > 0.01 else (-1 if vel < -0.01 else 0)
            if current_sign != 0 and last_sign != 0 and current_sign != last_sign:
                direction_changes += 1
            if current_sign != 0:
                last_sign = current_sign

        avg_stroke_rate = direction_changes / time_span if time_span > 0 else 1.0
        self.calibrated_max_stroke_rate = max(avg_stroke_rate * 1.5, 1.0)

    def _recalibrate_velocity_range(self):
        """Recalibrate max velocity based on current timeframe setting.

        Called automatically when timeframe changes, or can be called manually.
        """
        if not hasattr(self, 'velocity_data') or len(self.velocity_data) < 2:
            self.calibrated_max_speed = 0.5
            self._last_calibration_timeframe = settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()
            return

        times = [p[0] for p in self.position_data]
        time_span = times[-1] - times[0] if len(times) > 1 else 1.0

        # Use the same timeframe as the user's velocity factor setting
        calibration_window = settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()
        # Ensure window isn't larger than 1/4 of total funscript length
        calibration_window = min(calibration_window, time_span / 4) if time_span > 0 else 5.0

        # Store the timeframe used for this calibration
        self._last_calibration_timeframe = settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()

        # Scan the funscript with sliding windows to find max average velocity
        window_averages = []
        step_size = calibration_window / 2  # 50% overlap

        current_time = times[0]
        while current_time <= times[-1]:
            window_start = current_time - calibration_window / 2
            window_end = current_time + calibration_window / 2

            # Get velocities in this window
            velocities_in_window = [
                abs(v) for t, v in self.velocity_data
                if window_start <= t <= window_end
            ]

            if velocities_in_window:
                window_avg = sum(velocities_in_window) / len(velocities_in_window)
                window_averages.append(window_avg)

            current_time += step_size

        # Use 95th percentile of window averages as the calibrated max
        # This represents the "most intense sections" without being skewed by single spikes
        if window_averages:
            self.calibrated_max_speed = max(np.percentile(window_averages, 95), 0.5)
        else:
            self.calibrated_max_speed = 0.5

        logger.info(f"Motion Algorithm: Recalibrated with timeframe={calibration_window:.1f}s, "
                   f"{len(window_averages)} windows, max_avg_speed={self.calibrated_max_speed:.2f}")

    def _check_recalibration_needed(self):
        """Check if timeframe changed and recalibrate if needed."""
        current_timeframe = settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()
        last_timeframe = getattr(self, '_last_calibration_timeframe', None)

        if last_timeframe is None or current_timeframe != last_timeframe:
            logger.info(f"Motion Algorithm: Timeframe changed from {last_timeframe} to {current_timeframe}, recalibrating...")
            self._recalibrate_velocity_range()

    def _get_average_velocity_in_window(self, current_time: float) -> float:
        """Get average absolute velocity within a timeframe window centered on current_time.

        This smooths out velocity over a configurable time window, providing a more
        stable velocity measurement that represents the "overall velocity" of the
        current section rather than instantaneous spikes.

        Args:
            current_time: The current system time (will be mapped to video time)

        Returns:
            Average absolute velocity within the window
        """
        # Check if timeframe changed and recalibrate if needed
        self._check_recalibration_needed()

        # Map system time to video time (same as _get_position_velocity_acceleration)
        video_time = current_time
        if self.timestamp_mapper is not None:
            try:
                mapped_time = self.timestamp_mapper.map_timestamp(current_time)
                if mapped_time is not None and mapped_time >= 0:
                    video_time = mapped_time
            except Exception as e:
                logger.debug(f"Timestamp mapping failed in velocity window: {e}")

        timeframe = settings.COYOTE_MOTION_VELOCITY_TIMEFRAME.get()
        half_window = timeframe / 2.0

        window_start = video_time - half_window
        window_end = video_time + half_window

        # Filter velocity_data to get absolute velocities within the window
        velocities_in_window = [
            abs(v) for t, v in self.velocity_data
            if window_start <= t <= window_end
        ]

        if not velocities_in_window:
            # Fallback to 0 if no data in window (edge of funscript)
            return 0.0

        avg_velocity = sum(velocities_in_window) / len(velocities_in_window)

        # Log average velocity (occasionally, to avoid spam)
        if not hasattr(self, '_last_avg_vel_log') or current_time - getattr(self, '_last_avg_vel_log', 0) > 2.0:
            self._last_avg_vel_log = current_time
            logger.info(f"  AVG VEL: window=[{window_start:.1f}s, {window_end:.1f}s], "
                       f"samples={len(velocities_in_window)}, avg={avg_velocity:.3f}, "
                       f"global_max={self.calibrated_max_speed:.3f}")

        return avg_velocity

    def _calculate_dynamic_volume(self, current_velocity: float, current_time: float) -> float:
        """Calculate dynamic volume based on velocity and stroke count over time window.

        This detects "how active/intense is this section" by combining:
        - Average velocity (fast vs slow movements)
        - Stroke count (direction changes per time window)

        Returns a value between 0 and 1 representing the section intensity.
        """
        # Get settings directly from settings module for instant updates
        window_size = settings.COYOTE_MOTION_DYNAMIC_WINDOW_SIZE.get()
        sensitivity = settings.COYOTE_MOTION_DYNAMIC_SENSITIVITY.get()
        base_volume = settings.COYOTE_MOTION_BASE_VOLUME.get()

        # Track velocity history
        self.dynamic_velocity_history.append((current_time, current_velocity))

        # Detect direction changes (stroke detection)
        current_sign = 1 if current_velocity > 0.01 else (-1 if current_velocity < -0.01 else 0)
        if current_sign != 0 and self.last_velocity_sign != 0 and current_sign != self.last_velocity_sign:
            self.direction_change_times.append(current_time)
        if current_sign != 0:
            self.last_velocity_sign = current_sign

        # Prune old entries outside the time window
        cutoff_time = current_time - window_size
        self.dynamic_velocity_history = [(t, v) for t, v in self.dynamic_velocity_history if t >= cutoff_time]
        self.direction_change_times = [t for t in self.direction_change_times if t >= cutoff_time]

        # Calculate average absolute velocity over the window
        if len(self.dynamic_velocity_history) > 0:
            avg_velocity = sum(abs(v) for _, v in self.dynamic_velocity_history) / len(self.dynamic_velocity_history)
        else:
            avg_velocity = abs(current_velocity)

        # Calculate stroke rate (direction changes per second)
        stroke_count = len(self.direction_change_times)
        stroke_rate = stroke_count / window_size if window_size > 0 else 0.0

        # Normalize both metrics against calibrated maximums
        max_speed = getattr(self, 'calibrated_max_speed', 5.0)
        max_stroke_rate = getattr(self, 'calibrated_max_stroke_rate', 2.0)

        normalized_velocity = clamp(avg_velocity / max_speed, 0.0, 1.0)
        normalized_stroke_rate = clamp(stroke_rate / max_stroke_rate, 0.0, 1.0)

        # Combine velocity and stroke rate based on user-configurable mix ratio
        # mix_ratio: 0.0 = pure stroke count, 0.5 = balanced, 1.0 = pure velocity
        mix_ratio = settings.COYOTE_MOTION_DYNAMIC_MIX_RATIO.get()
        intensity_metric = mix_ratio * normalized_velocity + (1.0 - mix_ratio) * normalized_stroke_rate

        # Calculate dynamic volume with base floor
        # intensity_metric = 0 -> dynamic_volume = base_volume
        # intensity_metric = 1 -> dynamic_volume = 1.0
        full_range_volume = base_volume + (1.0 - base_volume) * intensity_metric

        # Apply sensitivity: blends between no variation (1.0) and full variation
        # sensitivity = 0: volume stays at 1.0 (no variation)
        # sensitivity = 1: volume varies fully from base_volume to 1.0
        dynamic_volume = 1.0 - sensitivity * (1.0 - full_range_volume)

        # Log dynamic volume calculation (occasionally)
        if not hasattr(self, '_last_dyn_vol_log') or current_time - getattr(self, '_last_dyn_vol_log', 0) > 2.0:
            self._last_dyn_vol_log = current_time
            logger.info(f"  DYN VOL: avg_vel={avg_velocity:.3f}, stroke_rate={stroke_rate:.2f}/s, "
                       f"norm_vel={normalized_velocity:.2f}, norm_stroke={normalized_stroke_rate:.2f}, "
                       f"mix={mix_ratio:.0%}, intensity={intensity_metric:.2f}, dynamic_vol={dynamic_volume:.3f}")

        return dynamic_volume

    def _get_position_velocity_acceleration(self, time: float):
        """Get position, velocity, and acceleration at specific time"""
        if not hasattr(self, 'position_data'):
            self._precompute_motion_data()

        # Map system time to video time using the timestamp mapper
        # This converts current time (time.time()) to media playback position
        video_time = time
        if self.timestamp_mapper is not None:
            try:
                mapped_time = self.timestamp_mapper.map_timestamp(time)
                # Only use mapped time if it's a valid positive number
                if mapped_time is not None and mapped_time >= 0:
                    video_time = mapped_time
            except Exception as e:
                logger.debug(f"Timestamp mapping failed: {e}")

        # Linear interpolation for all three components using video time
        pos = np.interp(video_time, [p[0] for p in self.position_data],
                         [p[1] for p in self.position_data])
        vel = np.interp(video_time, [v[0] for v in self.velocity_data],
                         [v[1] for v in self.velocity_data])
        acc = np.interp(video_time, [a[0] for a in self.acceleration_data],
                         [a[1] for a in self.acceleration_data])

        # Logging (only occasionally to avoid spam) - use INFO level to ensure visibility
        if not hasattr(self, '_last_debug_log') or time - self._last_debug_log > 1.0:
            self._last_debug_log = time
            logger.info(f"Motion data: video_time={video_time:.2f}s, pos={pos:.3f}, vel={vel:.3f}, acc={acc:.3f}, "
                        f"data_points={len(self.position_data)}")

        return pos, vel, acc
    
    def _calculate_motion_amplitude(self, normalized_pos: float, velocity: float, current_time: float) -> float:
        """Calculate amplitude using position-based approach with extreme boost and fade.

        This replaces the velocity-based amplitude calculation. The new approach:
        - Uses a constant base amplitude (60%) during any movement
        - Adds boost at position extremes (0 or 1) up to 90%
        - Velocity is no longer used for amplitude (it's used for frequency instead)
        - Smooth fade-out when movement stops, fade-in when movement resumes

        Args:
            normalized_pos: Position normalized to 0-1 range
            velocity: Current velocity (used only to detect movement vs pause)
            current_time: Current time for fade calculations

        Returns:
            Amplitude in 0-1 range (typically 0.6 to 0.9 during movement, fading to 0 on pause)
        """
        # Threshold to detect actual movement vs pause
        movement_threshold = 0.01

        # Detect if there's actual movement
        is_moving = abs(velocity) > movement_threshold

        # Calculate time delta for fade
        if self._last_fade_time is None:
            time_delta = 0.0
        else:
            time_delta = current_time - self._last_fade_time
        self._last_fade_time = current_time

        # Get fade settings
        fade_out_time = settings.COYOTE_MOTION_FADE_OUT_TIME.get()
        fade_in_time = settings.COYOTE_MOTION_FADE_IN_TIME.get()

        # Update fade level based on movement state
        if is_moving:
            # Fade in when moving
            if fade_in_time > 0 and time_delta > 0:
                fade_rate = 1.0 / fade_in_time  # Full fade-in per fade_in_time seconds
                self._fade_level = min(1.0, self._fade_level + fade_rate * time_delta)
            else:
                self._fade_level = 1.0
        else:
            # Fade out when not moving
            if fade_out_time > 0 and time_delta > 0:
                fade_rate = 1.0 / fade_out_time  # Full fade-out per fade_out_time seconds
                self._fade_level = max(0.0, self._fade_level - fade_rate * time_delta)
            else:
                self._fade_level = 0.0

        self._is_moving = is_moving

        # If fully faded out, return 0
        if self._fade_level <= 0.0:
            return 0.0

        # Base amplitude - constant during any movement
        base_amp = 0.6  # 60% base ensures consistent sensation

        # Position extreme boost - higher at top (1.0) and bottom (0.0)
        # Distance from center (0.5) determines boost amount
        distance_from_center = abs(normalized_pos - 0.5) * 2  # 0 at center, 1 at extremes
        extreme_boost = distance_from_center * 0.3  # Up to 30% boost at extremes

        # Final amplitude: 0.6 to 0.9 range, multiplied by fade level
        raw_amplitude = base_amp + extreme_boost
        amplitude = raw_amplitude * self._fade_level

        # Log amplitude calculation details (occasionally)
        if not hasattr(self, '_last_amp_log_time') or (hasattr(self, '_last_amp_log_time') and
            getattr(self, '_last_amp_log_time', 0) + 1.0 < getattr(self, '_last_debug_log', 0)):
            self._last_amp_log_time = getattr(self, '_last_debug_log', 0)
            logger.info(f"  AMP CALC: pos={normalized_pos:.3f}, moving={is_moving}, fade={self._fade_level:.2f}, "
                       f"raw_amp={raw_amplitude:.3f}, final_amp={amplitude:.3f}")

        return clamp(amplitude, 0.0, 1.0)
    
    def _apply_positional_effect(self, amplitude: float, position: float) -> Tuple[float, float]:
        """Apply positional channel distribution (sqrt-based from Howl)"""
        # Get user-defined positional effect strength
        positional_strength = 1.0  # Could be made configurable

        # Calculate effective position with user strength
        effective_position = 0.5 * (1 - positional_strength) + position * positional_strength

        # Square root distribution for smooth transitions
        amplitude_a = amplitude * math.sqrt(1 - effective_position)
        amplitude_b = amplitude * math.sqrt(effective_position)

        return amplitude_a, amplitude_b

    def _positional_intensity(self, time_s: float, volume: float) -> Tuple[int, int]:
        """Calculate intensity for both channels using Motion Algorithm.

        This method is called by the base CoyoteAlgorithm's channel controllers.
        Note: When using direct pulse generation via generate_packet override,
        this method is not used.
        """
        # Get position, velocity, acceleration from funscript
        pos, vel, acc = self._get_position_velocity_acceleration(time_s)

        # Convert position from [-1,1] to [0,1] range for calculations
        normalized_pos = clamp((pos + 1.0) / 2.0, 0.0, 1.0)

        # Calculate position-based amplitude (with velocity used only for movement detection)
        motion_amplitude = self._calculate_motion_amplitude(normalized_pos, vel)

        # Apply positional channel distribution
        channel_a_amp, channel_b_amp = self._apply_positional_effect(motion_amplitude, normalized_pos)

        # Apply volume and convert to intensity (0-100)
        intensity_a = int(channel_a_amp * volume * 100.0)
        intensity_b = int(channel_b_amp * volume * 100.0)

        return clamp(intensity_a, 0, 100), clamp(intensity_b, 0, 100)

    def generate_packet(self, current_time: float) -> Optional[CoyotePulses]:
        """Override base class to use Motion Algorithm's direct pulse generation.

        This bypasses the channel controllers and pulse generators, using
        the Motion Algorithm's velocity/acceleration-based calculations directly.
        """
        # Generate pulses directly using Motion Algorithm logic
        pulses = self.get_pulses_at_time(current_time)

        # Calculate packet duration for scheduling
        duration_a = sum(p.duration for p in pulses.channel_a) if pulses.channel_a else 0
        duration_b = sum(p.duration for p in pulses.channel_b) if pulses.channel_b else 0

        # Schedule next update at 65% of shortest packet duration (same as base class)
        min_duration_ms = max(1, min(duration_a, duration_b) if min(duration_a, duration_b) > 0 else max(duration_a, duration_b, 1))
        self.next_update_time = current_time + (min_duration_ms / 1000.0) * 0.65

        # Log packet info (use INFO level to ensure visibility)
        if pulses.channel_a:
            logger.info(f"Motion packet @ {current_time:.2f}s: "
                       f"A=[{pulses.channel_a[0].intensity}% @ {pulses.channel_a[0].frequency}Hz], "
                       f"B=[{pulses.channel_b[0].intensity}% @ {pulses.channel_b[0].frequency}Hz]")

        return pulses
    
    def _calculate_enhanced_frequency(self, position: float, time: float,
                                   channel: str, velocity: float = 0.0) -> float:
        """Calculate frequency with velocity modulation within user constraints.

        Velocity now modulates frequency - faster movements = higher pulse rate.
        This provides the "speed" sensation without affecting amplitude.
        """

        # Get channel-specific bounds
        if channel == 'A':
            min_freq = self.motion_params.channel_a.minimum_frequency.interpolate(0.0)
            max_freq = self.motion_params.channel_a.maximum_frequency.interpolate(0.0)
        else:  # channel == 'B'
            min_freq = self.motion_params.channel_b.minimum_frequency.interpolate(0.0)
            max_freq = self.motion_params.channel_b.maximum_frequency.interpolate(0.0)

        # Get frequency algorithm selection directly from settings for instant updates
        freq_algorithm = settings.COYOTE_MOTION_FREQUENCY_ALGORITHM.get()

        # Calculate base frequency based on algorithm
        # Handle display names like "Position Based", "Blend (Position + Noise)", etc.
        algo_str = str(freq_algorithm).upper() if freq_algorithm else "FIXED"

        if "POSITION" in algo_str and "BLEND" not in algo_str:
            base_freq = self._position_frequency(position, min_freq, max_freq)
        elif "THROB" in algo_str:
            base_freq = self._throbbing_frequency(position, time, min_freq, max_freq)
        elif "VARIED" in algo_str or "NOISE" in algo_str:
            base_freq = self._varied_frequency(position, time, min_freq, max_freq)
        elif "BLEND" in algo_str:
            base_freq = self._blend_frequency(position, time, min_freq, max_freq)
        else:  # FIXED or unknown
            base_freq = (min_freq + max_freq) / 2.0

        # Apply velocity modulation to frequency
        # Uses average velocity over a timeframe window, normalized against global funscript max
        # At 100% velocity factor: frequency is fully controlled by velocity (min_freq to max_freq)
        # At 0% velocity factor: frequency equals base_freq (no velocity influence)
        velocity_factor_setting = settings.COYOTE_MOTION_FREQUENCY_VELOCITY_FACTOR.get()

        # Get average velocity within the timeframe window
        avg_velocity = self._get_average_velocity_in_window(time)

        # Normalize against global funscript velocity range
        # calibrated_max_speed is the 95th percentile of all velocities in the funscript
        max_speed = getattr(self, 'calibrated_max_speed', 5.0)
        normalized_speed = clamp(avg_velocity / max_speed, 0.0, 1.0)

        # Calculate velocity-based frequency (maps full range: slow=min_freq, fast=max_freq)
        velocity_based_freq = min_freq + normalized_speed * (max_freq - min_freq)

        # Blend between base_freq and velocity_based_freq based on velocity_factor_setting
        # 0% = pure base_freq, 100% = pure velocity control
        modulated_freq = base_freq * (1.0 - velocity_factor_setting) + velocity_based_freq * velocity_factor_setting

        # Log frequency calculation (occasionally)
        if channel == 'A' and (not hasattr(self, '_last_freq_log') or
            getattr(self, '_last_freq_log', 0) + 2.0 < getattr(self, '_last_debug_log', 0)):
            self._last_freq_log = getattr(self, '_last_debug_log', 0)
            logger.info(f"  FREQ: algorithm='{freq_algorithm}', base={base_freq:.1f}, vel_based={velocity_based_freq:.1f}, "
                       f"avg_vel={avg_velocity:.3f}, norm_speed={normalized_speed:.2f}, "
                       f"blend={velocity_factor_setting:.0%}, result={modulated_freq:.1f}")

        return clamp(modulated_freq, min_freq, max_freq)
    
    def _position_frequency(self, position: float, min_freq: float, max_freq: float) -> float:
        """Standard position-based frequency mapping"""
        return min_freq + position * (max_freq - min_freq)
    
    def _throbbing_frequency(self, position: float, time: float,
                          min_freq: float, max_freq: float) -> float:
        """Enhanced throbbing frequency for regional strokes"""

        # Detect if we're in upper/bottom regions - read directly from settings for instant updates
        bottom_threshold = settings.COYOTE_MOTION_BOTTOM_REGION_THRESHOLD.get()
        upper_threshold = settings.COYOTE_MOTION_UPPER_REGION_THRESHOLD.get()

        in_bottom_region = position < bottom_threshold
        in_upper_region = position > upper_threshold

        if in_bottom_region or in_upper_region:
            # Add throbbing modulation
            throbbing_freq = 2.0  # Hz - throbbing pulse rate
            throbbing_intensity = settings.COYOTE_MOTION_THROBBING_INTENSITY.get()
            
            # Sinusoidal modulation for throbbing effect
            throbbing_modulation = math.sin(2 * math.pi * throbbing_freq * time) * throbbing_intensity
            
            # Base frequency calculation
            base_freq = self._position_frequency(position, min_freq, max_freq)
            
            # Apply throbbing enhancement
            if in_bottom_region:
                # Bottom strokes get frequency boosts to feel more "alive"
                return base_freq * (1.0 + throbbing_modulation)
            else:
                # Upper strokes get variation to prevent monotony
                return base_freq * (1.0 + throbbing_modulation * 0.5)
        else:
            # Mid-range strokes use standard position mapping
            return self._position_frequency(position, min_freq, max_freq)
    
    def _varied_frequency(self, position: float, time: float, 
                        min_freq: float, max_freq: float) -> float:
        """Noise-based frequency variation"""
        # Simple noise implementation (can be enhanced later)
        noise_value = math.sin(time * 0.7) * 0.2 + math.sin(time * 1.3) * 0.1
        base_freq = self._position_frequency(position, min_freq, max_freq)
        return base_freq * (1.0 + noise_value)
    
    def _blend_frequency(self, position: float, time: float, 
                      min_freq: float, max_freq: float) -> float:
        """Blend of position and varied algorithms"""
        base_freq = self._position_frequency(position, min_freq, max_freq)
        varied_freq = self._varied_frequency(position, time, min_freq, max_freq)
        return 0.5 * base_freq + 0.5 * varied_freq
    
    def has_funscript_data(self) -> bool:
        """Check if valid funscript motion data is loaded"""
        if not hasattr(self, 'position_data') or not hasattr(self, 'velocity_data'):
            return False
        # Check if we have more than just the default single point
        return len(self.position_data) > 1 and len(self.velocity_data) > 1

    def get_pulses_at_time(self, time: float) -> CoyotePulses:
        """Generate pulses using Motion Algorithm conversion"""

        # Get position, velocity, acceleration from funscript
        pos, vel, acc = self._get_position_velocity_acceleration(time)

        # Convert position from [-1,1] to [0,1] range for calculations
        normalized_pos = clamp((pos + 1.0) / 2.0, 0.0, 1.0)

        # Calculate real-time velocity from actual position change
        # This is more accurate than interpolated pre-computed velocity for movement detection
        if self._prev_position is not None and self._prev_position_time is not None:
            time_delta = time - self._prev_position_time
            if time_delta > 0.001:  # Avoid division by near-zero
                self._realtime_velocity = (pos - self._prev_position) / time_delta
            # If time_delta is too small, keep previous realtime_velocity
        else:
            # First call - use pre-computed velocity as initial estimate
            self._realtime_velocity = vel

        # Update tracking for next call
        self._prev_position = pos
        self._prev_position_time = time

        # Use real-time velocity for movement detection (more accurate)
        # Pre-computed velocity is still used for frequency modulation and dynamic volume
        motion_amplitude = self._calculate_motion_amplitude(normalized_pos, self._realtime_velocity, time)

        # Calculate dynamic volume based on velocity and stroke rate
        # This detects section intensity and affects both output AND UI (green bar)
        dynamic_enabled = settings.COYOTE_MOTION_DYNAMIC_VOLUME_ENABLED.get()
        if dynamic_enabled:
            self.current_dynamic_volume = self._calculate_dynamic_volume(vel, time)
        else:
            self.current_dynamic_volume = 1.0

        # Update external volume axis for UI display (green bar)
        if hasattr(self.motion_params.volume.external, 'add'):
            self.motion_params.volume.external.add(self.current_dynamic_volume)

        # Apply positional channel distribution
        channel_a_amp, channel_b_amp = self._apply_positional_effect(motion_amplitude, normalized_pos)

        # Get enhanced frequencies with velocity modulation
        freq_a = self._calculate_enhanced_frequency(normalized_pos, time, 'A', vel)
        freq_b = self._calculate_enhanced_frequency(normalized_pos, time, 'B', vel)

        # Apply volume scaling (existing volume system + dynamic volume)
        volume_at_time = self._calculate_total_volume(time)

        channel_a_intensity = int(channel_a_amp * volume_at_time * 100)
        channel_b_intensity = int(channel_b_amp * volume_at_time * 100)

        # Detailed logging to trace the calculation pipeline (occasional)
        if not hasattr(self, '_last_calc_log') or time - self._last_calc_log > 1.0:
            self._last_calc_log = time
            logger.info(f"CALC TRACE: pos={pos:.3f}, precomputed_vel={vel:.3f}, realtime_vel={self._realtime_velocity:.3f}, acc={acc:.3f}")
            logger.info(f"  -> motion_amplitude={motion_amplitude:.4f}, normalized_pos={normalized_pos:.3f}")
            logger.info(f"  -> channel_amps: A={channel_a_amp:.4f}, B={channel_b_amp:.4f}")
            logger.info(f"  -> volume_at_time={volume_at_time:.4f}")
            logger.info(f"  -> FINAL intensities: A={channel_a_intensity}%, B={channel_b_intensity}%")

        # Generate pulses using existing Coyote infrastructure
        return self._generate_motion_pulses(freq_a, freq_b,
                                       channel_a_intensity, channel_b_intensity, time)
    
    def _calculate_total_volume(self, time: float) -> float:
        """Calculate total volume including dynamic volume.

        Dynamic volume is calculated from the smoothed, normalized funscript intensity
        and affects both the actual output AND the UI display.
        """
        # Get standard volume components (api * master)
        standard_volume = self._get_standard_volume_at_time(time)

        # Get dynamic volume (already calculated in get_pulses_at_time)
        dynamic_volume = getattr(self, 'current_dynamic_volume', 1.0)

        total = standard_volume * dynamic_volume

        # Log the combined volume (occasionally)
        if not hasattr(self, '_last_total_vol_log') or time - getattr(self, '_last_total_vol_log', 0) > 2.0:
            self._last_total_vol_log = time
            logger.info(f"  TOTAL VOL: standard={standard_volume:.3f} * dynamic={dynamic_volume:.3f} = {total:.3f}")

        return total
    
    def _get_standard_volume_at_time(self, time: float) -> float:
        """Get standard volume from existing volume system"""
        # For Motion Algorithm:
        # - api_volume: from tcode/funscript volume commands
        # - master_volume: the spinbox setting (user's max volume)
        # - We DON'T use external_volume here because we write motion_amplitude to it for UI display
        # - We DON'T use inactivity_volume because motion itself determines activity
        api_volume = self.motion_params.volume.api.interpolate(time)
        master_volume = self.motion_params.volume.master.interpolate(time)

        # Only use api and master - external is used for UI display, not internal calculation
        total = api_volume * master_volume

        # Log volume components (occasionally)
        if not hasattr(self, '_last_vol_log_time') or getattr(self, '_last_vol_log_time', 0) + 1.0 < getattr(self, '_last_debug_log', 0):
            self._last_vol_log_time = getattr(self, '_last_debug_log', 0)
            logger.info(f"  VOLUME: api={api_volume:.3f}, master={master_volume:.3f} -> total={total:.3f}")

        return total
    
    def _generate_motion_pulses(self, freq_a: float, freq_b: float,
                               intensity_a: int, intensity_b: int, time: float):
        """Generate pulses using existing Coyote pulse generation infrastructure"""

        # Clamp frequencies to hardware limits
        freq_a = clamp(freq_a, HARDWARE_MIN_FREQ_HZ, HARDWARE_MAX_FREQ_HZ)
        freq_b = clamp(freq_b, HARDWARE_MIN_FREQ_HZ, HARDWARE_MAX_FREQ_HZ)

        # Calculate durations from frequency and clamp to hardware limits
        duration_a = int(clamp(1000.0 / freq_a, MIN_PULSE_DURATION_MS, MAX_PULSE_DURATION_MS))
        duration_b = int(clamp(1000.0 / freq_b, MIN_PULSE_DURATION_MS, MAX_PULSE_DURATION_MS))

        # Clamp intensities to valid range
        intensity_a = int(clamp(intensity_a, 0, 100))
        intensity_b = int(clamp(intensity_b, 0, 100))

        channel_a_pulses = []
        channel_b_pulses = []

        for i in range(4):  # Generate 4 pulses per packet (Coyote standard)
            pulse_a = CoyotePulse(
                frequency=int(freq_a),
                intensity=intensity_a,
                duration=duration_a
            )
            pulse_b = CoyotePulse(
                frequency=int(freq_b),
                intensity=intensity_b,
                duration=duration_b
            )

            channel_a_pulses.append(pulse_a)
            channel_b_pulses.append(pulse_b)

        return CoyotePulses(channel_a=channel_a_pulses, channel_b=channel_b_pulses)