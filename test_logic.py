import unittest
from unittest.mock import patch
from core.logic import TacticalAdvisor

class TestTacticalAdvisorAnalyzeTeamComposition(unittest.TestCase):
    def setUp(self):
        # Initialize TacticalAdvisor with a dummy path to avoid loading actual DB
        self.advisor = TacticalAdvisor(db_path="dummy_path.json")

    def test_empty_team(self):
        result = self.advisor.analyze_team_composition([])
        self.assertEqual(dict(result), {})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_single_role(self, mock_get_operator_data):
        mock_get_operator_data.return_value = {"role": ["Breach"]}
        result = self.advisor.analyze_team_composition(["Thermite"])
        self.assertEqual(dict(result), {"Breach": 1})
        mock_get_operator_data.assert_called_once_with("Thermite")

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_multiple_roles(self, mock_get_operator_data):
        mock_get_operator_data.return_value = {"role": ["Intel", "Support"]}
        result = self.advisor.analyze_team_composition(["Lion"])
        self.assertEqual(dict(result), {"Intel": 1, "Support": 1})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_role_as_string_fallback(self, mock_get_operator_data):
        # Test the fallback logic where role is a string instead of list
        mock_get_operator_data.return_value = {"role": "Anti-Entry"}
        result = self.advisor.analyze_team_composition(["Smoke"])
        self.assertEqual(dict(result), {"Anti-Entry": 1})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_missing_operator_data(self, mock_get_operator_data):
        mock_get_operator_data.return_value = None
        result = self.advisor.analyze_team_composition(["UnknownOp"])
        self.assertEqual(dict(result), {})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_empty_role_list(self, mock_get_operator_data):
        mock_get_operator_data.return_value = {"role": []}
        result = self.advisor.analyze_team_composition(["NoRoleOp"])
        self.assertEqual(dict(result), {})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_no_role_key(self, mock_get_operator_data):
        mock_get_operator_data.return_value = {"side": "atk"}
        result = self.advisor.analyze_team_composition(["Op"])
        self.assertEqual(dict(result), {})

    @patch('core.logic.TacticalAdvisor.get_operator_data')
    def test_mixed_scenarios(self, mock_get_operator_data):
        def side_effect(name):
            data = {
                "Ash": {"role": ["Front Line", "Breach"]},
                "Sledge": {"role": "Breach"},
                "Unknown": None,
                "NoRole": {"side": "atk"}
            }
            return data.get(name)

        mock_get_operator_data.side_effect = side_effect

        result = self.advisor.analyze_team_composition(["Ash", "Sledge", "Unknown", "NoRole", "Ash"])

        self.assertEqual(dict(result), {"Front Line": 2, "Breach": 3})

if __name__ == '__main__':
    unittest.main()
