import sys
import os
import unittest
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.tank import Tank
from services.anomaly_service import detect_anomalies

class TestAnomalyService(unittest.TestCase):
    def test_insufficient_data(self):
        tank = Tank(200)
        res = detect_anomalies(tank)
        self.assertFalse(res["anomaly_detected"])
        self.assertEqual(res["anomaly_type"], "NONE")

    def test_normal_behavior(self):
        tank = Tank(200)
        t = time.time()
        # Normal filling steps: ~25L/sec
        tank.history = [
            {"timestamp": t - 8.0, "event_type": "FILL", "previous_level": 0, "new_level": 50, "amount": 50, "source": "USER"},
            {"timestamp": t - 6.0, "event_type": "FILL", "previous_level": 50, "new_level": 100, "amount": 50, "source": "USER"},
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 100, "new_level": 150, "amount": 50, "source": "USER"},
            {"timestamp": t - 2.0, "event_type": "FILL", "previous_level": 150, "new_level": 200, "amount": 50, "source": "USER"}
        ]
        res = detect_anomalies(tank)
        self.assertFalse(res["anomaly_detected"])
        self.assertEqual(res["anomaly_type"], "NONE")

    def test_sensor_jump_anomaly(self):
        tank = Tank(800)
        t = time.time()
        
        # Build base history
        tank.history = [
            {"timestamp": t - 8.0, "event_type": "FILL", "previous_level": 0, "new_level": 50, "amount": 50, "source": "USER"},
            {"timestamp": t - 6.0, "event_type": "FILL", "previous_level": 50, "new_level": 100, "amount": 50, "source": "USER"},
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 100, "new_level": 150, "amount": 50, "source": "USER"},
            # Sudden giant jump of 300L
            {"timestamp": t - 2.0, "event_type": "FILL", "previous_level": 150, "new_level": 450, "amount": 300, "source": "USER"}
        ]
        
        res = detect_anomalies(tank)
        self.assertTrue(res["anomaly_detected"])
        self.assertEqual(res["anomaly_type"], "SENSOR_JUMP")
        self.assertEqual(res["severity"], "HIGH")

    def test_possible_leak_anomaly(self):
        tank = Tank(400)
        t = time.time()
        
        # Normal slow changes (approx 10L/sec)
        # Then a sudden massive drop of 120L in 1 second (120L/sec) without user request
        tank.history = [
            {"timestamp": t - 8.0, "event_type": "FILL", "previous_level": 200, "new_level": 220, "amount": 20, "source": "USER"},
            {"timestamp": t - 6.0, "event_type": "FILL", "previous_level": 220, "new_level": 240, "amount": 20, "source": "USER"},
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 240, "new_level": 260, "amount": 20, "source": "USER"},
            {"timestamp": t - 3.0, "event_type": "DRAIN", "previous_level": 260, "new_level": 140, "amount": -120, "source": "SENSOR"}
        ]
        
        res = detect_anomalies(tank)
        self.assertTrue(res["anomaly_detected"])
        self.assertEqual(res["anomaly_type"], "POSSIBLE_LEAK")
        self.assertEqual(res["severity"], "HIGH")

    def test_impossible_change_boundaries(self):
        tank = Tank(200)
        t = time.time()
        
        # Event level exceeds capacity
        tank.history = [
            {"timestamp": t - 8.0, "event_type": "FILL", "previous_level": 0, "new_level": 50, "amount": 50, "source": "USER"},
            {"timestamp": t - 6.0, "event_type": "FILL", "previous_level": 50, "new_level": 100, "amount": 50, "source": "USER"},
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 100, "new_level": 150, "amount": 50, "source": "USER"},
            {"timestamp": t - 2.0, "event_type": "FILL", "previous_level": 150, "new_level": 250, "amount": 100, "source": "USER"}
        ]
        
        res = detect_anomalies(tank)
        self.assertTrue(res["anomaly_detected"])
        self.assertEqual(res["anomaly_type"], "IMPOSSIBLE_CHANGE")
        self.assertEqual(res["severity"], "CRITICAL")

if __name__ == '__main__':
    unittest.main()
