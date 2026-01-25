import time
import numpy as np
from stim_math.axis import AbstractAxis


class MotionDynamicVolumeAxis(AbstractAxis):
    """Dynamic volume calculation based on funscript activity level"""
    
    def __init__(self, funscript_axis: AbstractAxis, window_size: float = 2.0):
        self.funscript_axis = funscript_axis
        self.window_size = window_size
        self.position_history = []
        self.last_update = time.time()
        
    def interpolate(self, timestamp):
        """Calculate dynamic volume multiplier based on recent activity"""
        # Get current position from funscript
        current_pos = self.funscript_axis.interpolate(timestamp)
        
        # Calculate recent activity level
        recent_velocity = self._calculate_recent_activity_level(timestamp)
        
        # Map activity to dynamic volume multiplier (0.5 - 1.5)
        # High activity = higher volume, Low activity = lower volume
        dynamic_multiplier = 0.5 + recent_velocity * 1.0
        
        return dynamic_multiplier
        
    def _calculate_recent_activity_level(self, current_time):
        """Calculate average velocity over time window"""
        # Sample funscript positions over last N seconds
        samples = []
        sample_interval = 0.1  # 10Hz sampling
        
        for i in range(int(self.window_size / sample_interval)):
            sample_time = current_time - i * sample_interval
            sample_pos = self.funscript_axis.interpolate(sample_time)
            samples.append(sample_pos)
            
        if len(samples) < 2:
            return 0.5
            
        # Calculate average absolute velocity
        velocities = [abs(samples[i] - samples[i-1]) for i in range(1, len(samples))]
        avg_velocity = sum(velocities) / len(velocities)
        
        # Map to 0-1 range (typical max velocity = 50 pos/s)
        return min(avg_velocity / 50.0, 1.0)
        
    def last_value(self):
        """Return last calculated value"""
        return 1.0  # Default multiplier
        
    def add(self, value, interval=0.0):
        """No-op - this axis is calculated dynamically"""
        pass