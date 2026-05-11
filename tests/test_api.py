import unittest
from sre_agent.ai_agent import app

class TestAgentAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_alert_endpoint_unauthorized(self):
        response = self.client.post('/alert', json={})
        self.assertEqual(response.status_code, 401)

    def test_alert_endpoint_with_key(self):
        headers = {'X-API-KEY': 'mahesh-secure-key-2026'}
        response = self.client.post('/alert', headers=headers, json={"metric": "test"})
        self.assertIn(response.status_code, [200, 429])

if __name__ == '__main__':
    unittest.main()
