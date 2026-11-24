import random
from providers.base_sensor import BaseSensorProvider

class SimulationSensorProvider(BaseSensorProvider):
    def __init__(self, tank):
        self.tank = tank
        self.noise_amplitude = 0.5 # +/- 0.5 cm noise

    def read_distance(self):
        """Maps in-memory tank water level to a simulated ultrasonic distance reading (0-100cm)."""
        capacity = self.tank.capacity
        level = self.tank.current_level
        
        fraction = level / capacity if capacity > 0 else 0
        # 100cm is empty (sensor to floor), 0cm is full
        clean_distance = (1.0 - fraction) * 100.0
        
        # Add random noise
        noisy_distance = clean_distance + random.uniform(-self.noise_amplitude, self.noise_amplitude)
        return max(0.0, min(100.0, noisy_distance))

    def get_status(self):
        return {
            "sensor_id": "SIM_ULTRASONIC_01",
            "provider_type": "SIMULATION",
            "sensor_status": "NORMAL",
            "data_quality": "GOOD",
            "warning_message": None
        }
