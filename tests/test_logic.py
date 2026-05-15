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

if __name__ == '__main__':
    unittest.main()
