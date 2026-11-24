import sys
import os
import unittest
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.tank import Tank
from services.prediction_service import calculate_predictions

class TestPredictionService(unittest.TestCase):
    def test_insufficient_data(self):
        tank = Tank(200)
        res = calculate_predictions(tank)
        self.assertEqual(res["data_sufficiency"], "INSUFFICIENT_DATA")
        self.assertEqual(res["trend"], "STABLE")

    def test_rising_trend_and_overflow_risk(self):
        tank = Tank(200)
        
        # Build 3 fill events sequentially to establish a RISING trend
        # We manually record events with slightly staggered timestamps
        t = time.time()
        tank.history = [
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 0, "new_level": 50, "amount": 50, "source": "USER"},
            {"timestamp": t - 2.0, "event_type": "FILL", "previous_level": 50, "new_level": 100, "amount": 50, "source": "USER"},
            {"timestamp": t, "event_type": "FILL", "previous_level": 100, "new_level": 150, "amount": 50, "source": "USER"}
        ]
        tank.current_level = 150
        
        res = calculate_predictions(tank)
        self.assertEqual(res["data_sufficiency"], "SUFFICIENT")
        self.assertEqual(res["trend"], "RISING")
        self.assertIn("seconds", res["estimated_time_until_full"])
        self.assertNotEqual(res["overflow_risk"]["level"], "LOW")
        self.assertTrue(res["overflow_risk"]["score"] > 0.0)

    def test_falling_trend(self):
        tank = Tank(200)
        tank.current_level = 50
        
        t = time.time()
        tank.history = [
            {"timestamp": t - 4.0, "event_type": "DRAIN", "previous_level": 150, "new_level": 110, "amount": -40, "source": "USER"},
            {"timestamp": t - 2.0, "event_type": "DRAIN", "previous_level": 110, "new_level": 80, "amount": -30, "source": "USER"},
            {"timestamp": t, "event_type": "DRAIN", "previous_level": 80, "new_level": 50, "amount": -30, "source": "USER"}
        ]
        
        res = calculate_predictions(tank)
        self.assertEqual(res["data_sufficiency"], "SUFFICIENT")
        self.assertEqual(res["trend"], "FALLING")
        self.assertIn("seconds", res["estimated_time_until_empty"])
        self.assertEqual(res["overflow_risk"]["level"], "LOW")
        self.assertEqual(res["overflow_risk"]["score"], 0.0)

    def test_stable_trend(self):
        tank = Tank(200)
        tank.current_level = 100
        
        t = time.time()
        tank.history = [
            {"timestamp": t - 4.0, "event_type": "FILL", "previous_level": 100, "new_level": 100, "amount": 0, "source": "USER"},
            {"timestamp": t - 2.0, "event_type": "DRAIN", "previous_level": 100, "new_level": 100, "amount": 0, "source": "USER"},
            {"timestamp": t, "event_type": "FILL", "previous_level": 100, "new_level": 100, "amount": 0, "source": "USER"}
        ]
        
        res = calculate_predictions(tank)
        self.assertEqual(res["data_sufficiency"], "SUFFICIENT")
        self.assertEqual(res["trend"], "STABLE")
        self.assertEqual(res["estimated_time_until_full"], "N/A")
        self.assertEqual(res["estimated_time_until_empty"], "N/A")

if __name__ == '__main__':
    unittest.main()
