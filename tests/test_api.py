import sys
import os
import unittest
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from services.tank_service import get_tank
from services.sensor_service import set_sensor_mode

class TestTankAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Reset singleton state
        tank = get_tank()
        tank.current_level = 0
        tank.capacity = 200
        tank.history.clear()
        set_sensor_mode("SIMULATION")

    def test_index_page(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)

    def test_api_status(self):
        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["tank"]["water"], 0)
        self.assertEqual(data["data"]["tank"]["capacity"], 200)

    def test_api_fill_success(self):
        res = self.client.post('/api/fill', 
                               data=json.dumps({"amount": 100}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["tank"]["water"], 100)

    def test_api_fill_invalid(self):
        res = self.client.post('/api/fill', 
                               data=json.dumps({"amount": -50}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)

    def test_api_drain_success(self):
        # Fill it up first
        self.client.post('/api/fill', 
                         data=json.dumps({"amount": 100}), 
                         content_type='application/json')
        res = self.client.post('/api/drain', 
                               data=json.dumps({"amount": 40}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["tank"]["water"], 60)

    def test_api_reset(self):
        self.client.post('/api/fill', 
                         data=json.dumps({"amount": 100}), 
                         content_type='application/json')
        res = self.client.post('/api/reset')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["data"]["tank"]["water"], 0)

    def test_api_capacity_change(self):
        res = self.client.post('/api/capacity', 
                               data=json.dumps({"capacity": 600}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["data"]["tank"]["capacity"], 600)

    def test_api_search_dls(self):
        res = self.client.post('/api/search', 
                               data=json.dumps({"initial_state": 0, "target_state": 200, "depth_limit": 4}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["dls"]["target_found"])

    def test_api_intelligence(self):
        res = self.client.get('/api/intelligence')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("predictions", data["data"]["intelligence"])
        self.assertIn("anomalies", data["data"]["intelligence"])

    def test_api_sensor_reading_upload(self):
        res = self.client.post('/api/sensor-reading', 
                               data=json.dumps({"distance_cm": 45.5}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["sensor"]["raw_value"], 45.5)

    def test_mode_switch(self):
        res = self.client.post('/api/mode', 
                               data=json.dumps({"mode": "SENSOR"}), 
                               content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["data"]["tank"]["operating_mode"], "SENSOR")
        
        # In SENSOR mode, fill should be disabled and return 400
        res_fill = self.client.post('/api/fill', 
                                   data=json.dumps({"amount": 100}), 
                                   content_type='application/json')
        self.assertEqual(res_fill.status_code, 400)

if __name__ == '__main__':
    unittest.main()
