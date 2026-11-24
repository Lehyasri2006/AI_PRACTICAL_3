import sys
import os
import unittest

# Ensure root path is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from algorithms.dls import run_dls
from models.tank import Tank
from services.anomaly_service import detect_anomalies

class TestDLSRegressions(unittest.TestCase):
    
    def test_regression_1_0_to_800(self):
        # Initial = 0, Target = 800, Depth Limit = 5
        res = run_dls(0, 800, 5, 800)
        self.assertTrue(res["target_found"])
        self.assertEqual(res["initial_state"], 0)
        self.assertEqual(res["target_state"], 800)
        self.assertTrue(res["target_depth"] <= 5)
        self.assertEqual(res["path"][0], 0)
        self.assertEqual(res["path"][-1], 800)

    def test_regression_2_200_to_800(self):
        # Initial = 200, Target = 800, Depth Limit = 5
        res = run_dls(200, 800, 5, 800)
        self.assertTrue(res["target_found"])
        self.assertEqual(res["path"][0], 200)
        self.assertEqual(res["path"][-1], 800)
        self.assertTrue(res["target_depth"] > 0)

    def test_regression_3_800_to_800(self):
        # Initial = 800, Target = 800
        res = run_dls(800, 800, 5, 800)
        self.assertTrue(res["target_found"])
        self.assertEqual(res["target_depth"], 0)
        self.assertEqual(res["path"], [800])

    def test_regression_4_depth_correctness(self):
        # Verify that for every generated node with a parent, child.depth == parent.depth + 1
        res = run_dls(0, 400, 5, 800)
        nodes = {n["node_id"]: n for n in res["nodes"]}
        for node in nodes.values():
            if node["parent_id"] is not None:
                parent = nodes[node["parent_id"]]
                self.assertEqual(node["depth"], parent["depth"] + 1)

    def test_regression_5_tank_level_unmutated(self):
        # Verify actual tank level before search == actual tank level after search
        tank = Tank(capacity=800)
        tank.fill(200)
        
        initial_level = tank.current_level
        self.assertEqual(initial_level, 200)
        
        # Perform search
        res = run_dls(tank.current_level, 800, 5, tank.capacity)
        self.assertTrue(res["target_found"])
        
        # Verify tank level remains completely unchanged
        self.assertEqual(tank.current_level, initial_level)

    def test_regression_6_event_history_unmutated(self):
        # Verify event history count does not change when running search
        tank = Tank(capacity=800)
        tank.fill(200)
        
        history_count_before = len(tank.history)
        
        # Perform search
        res = run_dls(tank.current_level, 800, 5, tank.capacity)
        self.assertTrue(res["target_found"])
        
        # Verify no history events were logged
        self.assertEqual(len(tank.history), history_count_before)

    def test_regression_7_no_false_anomalies(self):
        # Verify no anomaly is created solely because of hypothetical search states
        tank = Tank(capacity=800)
        tank.fill(200) # Event 1: user action
        
        # Perform search
        res = run_dls(tank.current_level, 800, 5, tank.capacity)
        self.assertTrue(res["target_found"])
        
        # Run anomaly detection
        anomalies = detect_anomalies(tank)
        # Should not flag a sensor jump or leakage due to the DLS path
        self.assertFalse(anomalies["anomaly_detected"])
        self.assertEqual(anomalies["anomaly_type"], "NONE")

if __name__ == '__main__':
    unittest.main()
