import unittest
import numpy as np
from device.coyote.motion_algorithm import CoyoteMotionAlgorithm
from stim_math.audio_gen.params import CoyoteMotionAlgorithmParams
from funscript.funscript import Funscript


class TestCoyoteMotionAlgorithm(unittest.TestCase):
    """Test cases for Motion Algorithm functionality"""
    
    def setUp(self):
        # Create test funscript data
        test_positions = [0, 50, 100, 50, 0]  # Simple stroke pattern
        test_times = [0, 1, 2, 3, 4]  # 1 second intervals
        self.test_funscript = Funscript(test_times, test_positions)
        
    def _create_test_algorithm(self):
        """Helper to create test algorithm with mock parameters"""
        from stim_math.axis import create_constant_axis
        from stim_math.audio_gen.params import (
            CoyoteMotionVolumeParams, CoyoteMotionAlgorithmParams,
            VolumeParams, ThreephasePositionParams, CoyoteChannelParams
        )
        
        motion_volume = CoyoteMotionVolumeParams(
            dynamic_enabled=create_constant_axis(True),
            dynamic_window_size=create_constant_axis(2.0),
            dynamic_sensitivity=create_constant_axis(0.5),
            base_volume=create_constant_axis(1.0),
        )
        
        algorithm = CoyoteMotionAlgorithm(
            media=None,  # Not used in these tests
            params=CoyoteMotionAlgorithmParams(
                position=ThreephasePositionParams(
                    alpha=create_constant_axis(self.test_funscript.x),
                    beta=create_constant_axis(np.zeros_like(self.test_funscript.x))
                ),
                transform=None,  # Not used in these tests
                calibrate=None,  # Not used in these tests
                volume=VolumeParams(
                    api=create_constant_axis(1.0),
                    master=create_constant_axis(1.0),
                    inactivity=create_constant_axis(1.0),
                    external=create_constant_axis(1.0),
                ),
                motion_volume=motion_volume,
                carrier_frequency=create_constant_axis(100),
                pulse_frequency=create_constant_axis(50),
                pulse_width=create_constant_axis(5),
                pulse_interval_random=create_constant_axis(10),
                pulse_rise_time=create_constant_axis(10),
                max_intensity_change_per_pulse=create_constant_axis(1.0),
                channel_a=CoyoteChannelParams(
                    minimum_frequency=create_constant_axis(70),
                    maximum_frequency=create_constant_axis(100),
                    maximum_strength=create_constant_axis(100),
                    vibration=None,
                    pulse_frequency=create_constant_axis(50)
                ),
                channel_b=CoyoteChannelParams(
                    minimum_frequency=create_constant_axis(30),
                    maximum_frequency=create_constant_axis(100),
                    maximum_strength=create_constant_axis(100),
                    vibration=None,
                    pulse_frequency=create_constant_axis(50)
                ),
                # Motion Algorithm specific parameters
                frequency_algorithm=create_constant_axis("POSITION"),
                throbbing_intensity=create_constant_axis(0.3),
                bottom_region_threshold=create_constant_axis(0.3),
                upper_region_threshold=create_constant_axis(0.7),
            ),
            safety_limits=None,  # Not used in these tests
            carrier_freq_limits=(70, 100),
            pulse_freq_limits=(30, 100),
            pulse_width_limits=(5, 20),
            pulse_rise_time_limits=(10, 50),
            skip_texture_and_residual=True,
        )
        
        # Precompute motion data
        algorithm._precompute_motion_data()
        
        return algorithm
        
    def test_motion_amplitude_calculation(self):
        """Test velocity/acceleration-based amplitude calculation"""
        algorithm = self._create_test_algorithm()
        
        # Test cases for different velocities and accelerations
        test_cases = [
            (0.0, 0.0),    # No movement
            (1.0, 0.0),    # High velocity, no acceleration
            (0.1, 0.0),    # Low velocity, no acceleration
            (0.0, 1.0),    # No velocity, high acceleration
            (0.0, 0.1),    # No velocity, low acceleration
            (1.0, 1.0),    # High velocity, high acceleration
        ]
        
        for velocity, acceleration in test_cases:
            amplitude = algorithm._calculate_motion_amplitude(velocity, acceleration)
            
            # Verify amplitude is within valid range
            self.assertGreaterEqual(amplitude, 0.0)
            self.assertLessEqual(amplitude, 1.0)
            
            # High velocity/acceleration should produce higher amplitude
            if velocity > 0.5 or acceleration > 0.5:
                self.assertGreater(amplitude, 0.5)
            else:
                self.assertLessEqual(amplitude, 0.5)
        
    def test_positional_effect_distribution(self):
        """Test positional channel distribution"""
        algorithm = self._create_test_algorithm()
        
        # Test cases for different positions
        test_cases = [
            (1.0, 0.0),  # Position 0 (bottom) - should favor channel A
            (1.0, 1.0),  # Position 1 (top) - should favor channel B
            (1.0, 0.5),  # Position 0.5 (middle) - should be balanced
        ]
        
        for amplitude, position in test_cases:
            amp_a, amp_b = algorithm._apply_positional_effect(amplitude, position)
            
            # Verify amplitudes are within valid range
            self.assertGreaterEqual(amp_a, 0.0)
            self.assertLessEqual(amp_a, 1.0)
            self.assertGreaterEqual(amp_b, 0.0)
            self.assertLessEqual(amp_b, 1.0)
            
            # Verify sqrt distribution property
            expected_sum = amplitude  # amp_a² + amp_b² should equal amplitude² for sqrt distribution
            actual_sum_squared = amp_a * amp_a + amp_b * amp_b
            self.assertAlmostEqual(actual_sum_squared, expected_sum, places=5)
            
            # Position-based expectations
            if position == 0.0:  # Bottom should favor A
                self.assertGreater(amp_a, amp_b)
            elif position == 1.0:  # Top should favor B
                self.assertGreater(amp_b, amp_a)
            else:  # Middle should be balanced
                self.assertAlmostEqual(amp_a, amp_b, places=2)
        
    def test_frequency_boundary_compliance(self):
        """Test that frequencies respect user-defined limits"""
        algorithm = self._create_test_algorithm()
        
        # Test positions and channels
        test_cases = [
            (0.1, 'A', 70, 100),  # Bottom position, channel A
            (0.9, 'B', 30, 100),  # Top position, channel B
            (0.5, 'A', 70, 100),  # Middle position, channel A
            (0.5, 'B', 30, 100),  # Middle position, channel B
        ]
        
        for position, channel, min_freq, max_freq in test_cases:
            freq = algorithm._calculate_enhanced_frequency(position, 0.0, channel)
            
            # Frequency should be within user-defined bounds
            self.assertGreaterEqual(freq, min_freq)
            self.assertLessEqual(freq, max_freq)
            
            # Test position-based frequency mapping
            if algorithm.motion_params.frequency_algorithm.interpolate(0.0) == "POSITION":
                expected_freq = min_freq + position * (max_freq - min_freq)
                self.assertAlmostEqual(freq, expected_freq, places=5)
        
    def test_precompute_motion_data(self):
        """Test motion data precomputation"""
        algorithm = self._create_test_algorithm()
        
        # Verify that precomputation was called
        self.assertTrue(hasattr(algorithm, 'position_data'))
        self.assertTrue(hasattr(algorithm, 'velocity_data'))
        self.assertTrue(hasattr(algorithm, 'acceleration_data'))
        
        # Verify data structure
        self.assertEqual(len(algorithm.position_data), len(self.test_funscript.x))
        self.assertEqual(len(algorithm.velocity_data), len(self.test_funscript.x))
        self.assertEqual(len(algorithm.acceleration_data), len(self.test_funscript.x))
        
    def test_algorithm_integration(self):
        """Test complete algorithm integration"""
        algorithm = self._create_test_algorithm()
        
        # Test that we can call the main method without errors
        try:
            pulses = algorithm.get_pulses_at_time(1.0)  # Middle of test data
            self.assertIsNotNone(pulses)
            
            # Verify pulses structure
            self.assertEqual(len(pulses.channel_a), 4)  # 4 pulses per packet
            self.assertEqual(len(pulses.channel_b), 4)
            
            # Verify pulse values are within expected ranges
            for pulse in pulses.channel_a:
                self.assertGreaterEqual(pulse.frequency, 70)   # Channel A min freq
                self.assertLessEqual(pulse.frequency, 100)    # Channel A max freq
                self.assertGreaterEqual(pulse.intensity, 0)
                self.assertLessEqual(pulse.intensity, 100)
                
            for pulse in pulses.channel_b:
                self.assertGreaterEqual(pulse.frequency, 30)   # Channel B min freq
                self.assertLessEqual(pulse.frequency, 100)    # Channel B max freq
                self.assertGreaterEqual(pulse.intensity, 0)
                self.assertLessEqual(pulse.intensity, 100)
                
        except Exception as e:
            self.fail(f"Algorithm integration test failed with exception: {e}")


if __name__ == '__main__':
    unittest.main()