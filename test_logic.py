import unittest
from unittest.mock import patch
from core.logic import TacticalAdvisor

class TestTacticalAdvisor(unittest.TestCase):
    @patch('core.logic.TacticalAdvisor._load_db')
    def setUp(self, mock_load_db):
        # Prevent actually loading the file and printing "DB Load Failed"
        mock_load_db.return_value = {}
        self.advisor = TacticalAdvisor("dummy_path")

        # Explicitly set the mocked database for our tests
        self.advisor.db = {
            "Ash": {"name": "Ash", "role": "Breach"},
            "Recruit (ATK)": {"name": "Recruit (ATK)", "role": "Unknown"},
            "Thermite": {"name": "Thermite", "role": "Breach"}
        }

    def test_get_operator_data_exact_match(self):
        """Test looking up an operator with an exact name match."""
        data = self.advisor.get_operator_data("Ash")
        self.assertEqual(data, {"name": "Ash", "role": "Breach"})

    def test_get_operator_data_case_insensitive(self):
        """Test looking up an operator with different casing."""
        data = self.advisor.get_operator_data("ash")
        self.assertEqual(data, {"name": "Ash", "role": "Breach"})

        data2 = self.advisor.get_operator_data("THERMITE")
        self.assertEqual(data2, {"name": "Thermite", "role": "Breach"})

    def test_get_operator_data_substring_match(self):
        """Test looking up an operator using a substring (like 'Recruit')."""
        data = self.advisor.get_operator_data("Recruit")
        self.assertEqual(data, {"name": "Recruit (ATK)", "role": "Unknown"})

    def test_get_operator_data_not_found(self):
        """Test looking up an operator that does not exist."""
        data = self.advisor.get_operator_data("NonExistent")
        self.assertIsNone(data)

if __name__ == '__main__':
    unittest.main()
