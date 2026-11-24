import time
from providers.base_sensor import BaseSensorProvider

class IoTSensorProvider(BaseSensorProvider):
    def __init__(self):
        self.latest_reading = None
        self.last_update = 0
        self.is_connected = True

    def read_distance(self):
        """Returns the last posted IoT distance reading in cm."""
        if not self.is_connected:
            raise IOError("IoT Sensor connection error. Node offline.")
        if self.latest_reading is None:
            # Default to empty tank distance (100cm)
            return 100.0
        return self.latest_reading

    def update_reading(self, distance_cm):
        """Ingests new raw distance data from external network nodes."""
        self.latest_reading = distance_cm
        self.last_update = time.time()

    def get_status(self):
        """Evaluates connection quality, stale timestamps, and connection status."""
        if not self.is_connected:
            return {
                "sensor_id": "IOT_ULTRASONIC_NODE",
                "provider_type": "IOT_HARDWARE",
                "sensor_status": "DISCONNECTED",
                "data_quality": "BAD",
                "warning_message": "Hardware node offline. Check network connections."
            }
            
        # Check if telemetry is stale (longer than 10 seconds since last update)
        if self.latest_reading is not None and (time.time() - self.last_update) > 10.0:
            return {
                "sensor_id": "IOT_ULTRASONIC_NODE",
                "provider_type": "IOT_HARDWARE",
                "sensor_status": "STALE",
                "data_quality": "POOR",
                "warning_message": "Telemetry stream is stale. No updates received in >10 seconds."
            }
            
        status = "NORMAL" if self.latest_reading is not None else "AWAITING_DATA"
        quality = "GOOD" if self.latest_reading is not None else "NORMAL"
        
        return {
            "sensor_id": "IOT_ULTRASONIC_NODE",
            "provider_type": "IOT_HARDWARE",
            "sensor_status": status,
            "data_quality": quality,
            "warning_message": None
        }
