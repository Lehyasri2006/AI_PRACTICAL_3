import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.tank import Tank

class TestTankModel(unittest.TestCase):
    def test_initial_state(self):
        tank = Tank(capacity=200)
        self.assertEqual(tank.capacity, 200)
        self.assertEqual(tank.current_level, 0)
        self.assertEqual(len(tank.history), 0)

    def test_fill_valid(self):
        tank = Tank(capacity=400)
        tank.fill(150)
        self.assertEqual(tank.current_level, 150)
        self.assertEqual(tank.history[-1]["event_type"], "FILL")
        self.assertEqual(tank.history[-1]["amount"], 150)

    def test_fill_overflow_clamping(self):
        tank = Tank(capacity=200)
        tank.fill(300)
        self.assertEqual(tank.current_level, 200)
        self.assertEqual(tank.history[-1]["amount"], 200) # actual change is 200

    def test_fill_invalid(self):
        tank = Tank(200)
        with self.assertRaises(ValueError):
            tank.fill(-50)
        with self.assertRaises(ValueError):
            tank.fill("string")

    def test_drain_valid(self):
        tank = Tank(capacity=400)
        tank.fill(300)
        tank.drain(100)
        self.assertEqual(tank.current_level, 200)
        self.assertEqual(tank.history[-1]["event_type"], "DRAIN")
        self.assertEqual(tank.history[-1]["amount"], -100)

    def test_drain_underflow_clamping(self):
        tank = Tank(capacity=200)
        tank.fill(100)
        tank.drain(150)
        self.assertEqual(tank.current_level, 0)
        self.assertEqual(tank.history[-1]["amount"], -100) # actual change is -100

    def test_drain_invalid(self):
        tank = Tank(200)
        with self.assertRaises(ValueError):
            tank.drain(-50)

    def test_reset(self):
        tank = Tank(200)
        tank.fill(100)
        tank.reset()
        self.assertEqual(tank.current_level, 0)
        self.assertEqual(tank.history[-1]["event_type"], "RESET")

    def test_update_capacity_success(self):
        tank = Tank(200)
        tank.fill(150)
        tank.update_capacity(400)
        self.assertEqual(tank.capacity, 400)
        self.assertEqual(tank.current_level, 150)

    def test_update_capacity_shrink_clamp(self):
        tank = Tank(400)
        tank.fill(350)
        # Shrink capacity to 200L. Level should be clamped to 200L.
        tank.update_capacity(200)
        self.assertEqual(tank.capacity, 200)
        self.assertEqual(tank.current_level, 200)

    def test_update_capacity_invalid(self):
        tank = Tank(200)
        with self.assertRaises(ValueError):
            tank.update_capacity(300)
            
if __name__ == '__main__':
    unittest.main()
