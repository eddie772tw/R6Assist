import unittest
from unittest.mock import patch, mock_open
import os
import json
from core.logic import TacticalAdvisor

class TestTacticalAdvisor(unittest.TestCase):

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_db_success(self, mock_json_load, mock_file, mock_exists):
        mock_exists.return_value = True
        test_data = {"Ash": {"side": "atk", "role": ["Front Line", "Breach"]}}
        mock_json_load.return_value = test_data

        advisor = TacticalAdvisor("fake_path.json")

        self.assertEqual(advisor.db, test_data)
        mock_file.assert_called_with("fake_path.json", 'r', encoding='utf-8')

    @patch('os.path.exists')
    def test_load_db_file_not_found(self, mock_exists):
        # Case where path does not exist and fallback path also does not exist
        mock_exists.return_value = False

        # open will raise FileNotFoundError when it tries to open the non-existent fallback path
        with patch('builtins.open', side_effect=FileNotFoundError()):
            advisor = TacticalAdvisor("non_existent.json")
            self.assertEqual(advisor.db, {})

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    @patch('json.load')
    def test_load_db_invalid_json(self, mock_json_load, mock_file, mock_exists):
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Expecting value", "", 0)

        advisor = TacticalAdvisor("invalid.json")
        self.assertEqual(advisor.db, {})

    @patch('core.logic.TacticalAdvisor._load_db')
    def test_get_operator_data_exact_match(self, mock_load_db):
        """Test looking up an operator with an exact name match."""
        mock_load_db.return_value = {}
        advisor = TacticalAdvisor("dummy_path")
        advisor.db = {
            "Ash": {"name": "Ash", "role": "Breach"},
            "Recruit (ATK)": {"name": "Recruit (ATK)", "role": "Unknown"},
            "Thermite": {"name": "Thermite", "role": "Breach"}
        }
        advisor._name_map = {k.lower(): k for k in advisor.db.keys()}
        data = advisor.get_operator_data("Ash")
        self.assertEqual(data, {"name": "Ash", "role": "Breach"})

    @patch('core.logic.TacticalAdvisor._load_db')
    def test_get_operator_data_case_insensitive(self, mock_load_db):
        """Test looking up an operator with different casing."""
        mock_load_db.return_value = {}
        advisor = TacticalAdvisor("dummy_path")
        advisor.db = {
            "Ash": {"name": "Ash", "role": "Breach"},
            "Recruit (ATK)": {"name": "Recruit (ATK)", "role": "Unknown"},
            "Thermite": {"name": "Thermite", "role": "Breach"}
        }
        advisor._name_map = {k.lower(): k for k in advisor.db.keys()}
        data = advisor.get_operator_data("ash")
        self.assertEqual(data, {"name": "Ash", "role": "Breach"})

        data2 = advisor.get_operator_data("THERMITE")
        self.assertEqual(data2, {"name": "Thermite", "role": "Breach"})

    @patch('core.logic.TacticalAdvisor._load_db')
    def test_get_operator_data_substring_match(self, mock_load_db):
        """Test looking up an operator using a substring (like 'Recruit')."""
        mock_load_db.return_value = {}
        advisor = TacticalAdvisor("dummy_path")
        advisor.db = {
            "Ash": {"name": "Ash", "role": "Breach"},
            "Recruit (ATK)": {"name": "Recruit (ATK)", "role": "Unknown"},
            "Thermite": {"name": "Thermite", "role": "Breach"}
        }
        advisor._name_map = {k.lower(): k for k in advisor.db.keys()}
        data = advisor.get_operator_data("Recruit")
        self.assertEqual(data, {"name": "Recruit (ATK)", "role": "Unknown"})

    @patch('core.logic.TacticalAdvisor._load_db')
    def test_get_operator_data_not_found(self, mock_load_db):
        """Test looking up an operator that does not exist."""
        mock_load_db.return_value = {}
        advisor = TacticalAdvisor("dummy_path")
        advisor.db = {
            "Ash": {"name": "Ash", "role": "Breach"},
            "Recruit (ATK)": {"name": "Recruit (ATK)", "role": "Unknown"},
            "Thermite": {"name": "Thermite", "role": "Breach"}
        }
        advisor._name_map = {k.lower(): k for k in advisor.db.keys()}
        data = advisor.get_operator_data("NonExistent")
        self.assertIsNone(data)

if __name__ == '__main__':
    unittest.main()
