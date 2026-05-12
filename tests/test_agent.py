import unittest
from unittest.mock import patch
from ai_agent import query_prometheus, cooldown_active

class TestAgentLogic(unittest.TestCase):
    @patch('requests.get')
    def test_query_prometheus_empty(self, mock_get):
        mock_get.return_value.json.return_value = {"data": {"result": []}}
        result = query_prometheus("up")
        self.assertEqual(result, [])

    def test_cooldown_logic(self):
        self.assertFalse(cooldown_active())

if __name__ == '__main__':
    unittest.main()
