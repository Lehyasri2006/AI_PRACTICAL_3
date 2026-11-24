import sys
import os
import unittest
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.sensor_service import (
    set_sensor_mode,
    process_sensor_telemetry,
    get_sensor_service_state,
    readings_history
)
from providers.iot_sensor import IoTSensorProvider

class TestSensorService(unittest.TestCase):
    def setUp(self):
        # Clear readings history before each test
        readings_history.clear()
        set_sensor_mode("SIMULATION")

    def test_switch_operating_mode(self):
        set_sensor_mode("SENSOR")
        active_mode, _, _ = get_sensor_service_state()
        self.assertEqual(active_mode, "SENSOR")

    def test_sensor_conversion_and_rounding(self):
        # 100cm empty, 0cm full. If raw is 50.0cm on a 200L capacity tank:
        # height fraction is (100 - 50)/100 = 0.5. Estimated level = 0.5 * 200 = 100.0L.
        res = process_sensor_telemetry(50.0)
        self.assertEqual(res["sensor_status"], "NORMAL")
        self.assertEqual(res["estimated_level"], 100.0)

    def test_sensor_validation_invalid_type(self):
        res = process_sensor_telemetry("invalid_string")
        self.assertEqual(res["sensor_status"], "INVALID")
        self.assertIsNone(res["estimated_level"])

    def test_sensor_validation_out_of_bounds(self):
        # Out of bounds (>100cm or <0cm)
        res1 = process_sensor_telemetry(-5.0)
        self.assertEqual(res1["sensor_status"], "INVALID")
        
        res2 = process_sensor_telemetry(105.0)
        self.assertEqual(res2["sensor_status"], "INVALID")

    def test_rolling_average_smoothing(self):
        # Input: 50, 52, 48, 51, 49. Average should be 50.
        process_sensor_telemetry(50.0)
        process_sensor_telemetry(52.0)
        process_sensor_telemetry(48.0)
        process_sensor_telemetry(51.0)
        res = process_sensor_telemetry(49.0)
        
        self.assertEqual(res["raw_value"], 49.0)
        self.assertEqual(res["filtered_value"], 50.0)

    def test_sudden_jump_filtering(self):
        # Establish a baseline of 10.0 cm
        process_sensor_telemetry(10.0)
        process_sensor_telemetry(10.0)
        
        # Sudden jump of 60.0cm (10.0 -> 70.0)
        res = process_sensor_telemetry(70.0)
        
        self.assertEqual(res["sensor_status"], "NOISY")
        self.assertEqual(res["data_quality"], "POOR")
        self.assertIsNotNone(res["filtered_value"])

    def test_iot_sensor_stale_alert(self):
        iot = IoTSensorProvider()
        iot.update_reading(40.0)
        # Standard status should be NORMAL
        status_normal = iot.get_status()
        self.assertEqual(status_normal["sensor_status"], "NORMAL")
        
        # Override update timestamp to simulate stale reading (>10s old)
        iot.last_update = time.time() - 15.0
        status_stale = iot.get_status()
        self.assertEqual(status_stale["sensor_status"], "STALE")
        self.assertEqual(status_stale["data_quality"], "POOR")

if __name__ == '__main__':
    unittest.main()
