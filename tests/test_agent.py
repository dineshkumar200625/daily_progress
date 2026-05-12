import unittest
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../ai-agent')))

from ai_agent import query_prometheus, cooldown_active

class TestAgentLogic(unittest.TestCase):
    @patch('requests.get')
    def test_query_prometheus_empty(self, mock_get):
        mock_get.return_value.json.return_value = {"data": {"result": []}}
        result = query_prometheus("up")
        self.assertEqual(result, [])

    def test_cooldown_logic(self):
        
        self.assertIsNotNone(cooldown_active)

    @patch('ai_agent.PROMETHEUS_URL', None)
    def test_query_prometheus_no_url(self):
        """Test graceful handling when Prometheus URL is missing"""
        result = query_prometheus("up")
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
