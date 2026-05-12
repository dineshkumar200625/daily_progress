import unittest
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../ai-agent')))

from ai_agent import app

class TestAgentAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        os.environ['X_API_KEY'] = 'test-secret-key-2026'
        
    def tearDown(self):
        os.environ.pop('X_API_KEY', None)

    def test_alert_endpoint_unauthorized(self):
        """No API key → 401 Unauthorized"""
        response = self.client.post('/alert', json={})
        self.assertEqual(response.status_code, 401)

    def test_alert_endpoint_with_key(self):
        """Valid API key → 202 Accepted"""
        headers = {'X-API-KEY': os.environ['X_API_KEY']}
        response = self.client.post('/alert', headers=headers, json={"metric": "test"})
        self.assertIn(response.status_code, [202, 429])

    def test_health_endpoint(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('status', data)

    def test_slack_command_endpoint(self):
        response = self.client.post('/slack/command', data={'command': '/sre-status'})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
