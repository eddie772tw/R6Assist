import unittest
from unittest.mock import patch, MagicMock

# Import the target class
from core.assistant import R6TacticalAssistant

class TestR6TacticalAssistantDetermineSide(unittest.TestCase):

    @patch('core.assistant.TeamAnalyzer')
    @patch('core.assistant.TacticalAdvisor')
    def setUp(self, mock_advisor_class, mock_analyzer_class):
        # Setup mock for TacticalAdvisor and TeamAnalyzer
        self.mock_analyzer_instance = mock_analyzer_class.return_value
        self.mock_advisor_instance = mock_advisor_class.return_value

        # Define some mock operator data
        # Let's say:
        # Ash, Thatcher are atk
        # Rook, Doc are def
        def mock_get_operator_data(name):
            data = {
                "Ash": {"side": "atk"},
                "Thatcher": {"side": "atk"},
                "Sledge": {"side": "atk"},
                "Rook": {"side": "def"},
                "Doc": {"side": "def"},
                "Bandit": {"side": "def"},
                "WeirdOp": {"side": "unknown"}, # Invalid side
            }
            return data.get(name, None)

        self.mock_advisor_instance.get_operator_data.side_effect = mock_get_operator_data

        # Initialize the assistant
        # We pass None for model_path and db_path since they are mocked
        self.assistant = R6TacticalAssistant(model_path=None, db_path=None)

    def test_determine_side_all_attackers(self):
        team = ["Ash", "Thatcher", "Sledge"]
        result = self.assistant.determine_side(team)
        self.assertEqual(result, "atk")

    def test_determine_side_all_defenders(self):
        team = ["Rook", "Doc", "Bandit"]
        result = self.assistant.determine_side(team)
        self.assertEqual(result, "def")

    def test_determine_side_mixed_majority_attackers(self):
        # 3 atk, 2 def -> atk
        team = ["Ash", "Thatcher", "Sledge", "Rook", "Doc"]
        result = self.assistant.determine_side(team)
        self.assertEqual(result, "atk")

    def test_determine_side_mixed_majority_defenders(self):
        # 2 atk, 3 def -> def
        team = ["Ash", "Thatcher", "Rook", "Doc", "Bandit"]
        result = self.assistant.determine_side(team)
        self.assertEqual(result, "def")

    def test_determine_side_ignores_unknown_and_recruit(self):
        # Should ignore Unknown, Recruit, and count the rest
        team = ["Unknown", "Recruit", "Ash", "Thatcher"]
        result = self.assistant.determine_side(team)
        self.assertEqual(result, "atk")

        team_def = ["Unknown", "Rook", "Recruit", "Doc"]
        result = self.assistant.determine_side(team_def)
        self.assertEqual(result, "def")

    def test_determine_side_empty_valid_operators(self):
        # Only Unknown/Recruit -> None
        team = ["Unknown", "Recruit"]
        result = self.assistant.determine_side(team)
        self.assertIsNone(result)

    def test_determine_side_unrecognized_operators(self):
        # Operators not in DB -> None
        team = ["Op1", "Op2"]
        result = self.assistant.determine_side(team)
        self.assertIsNone(result)

    def test_determine_side_invalid_side(self):
        # Operator with valid name but invalid side string -> None
        team = ["WeirdOp"]
        result = self.assistant.determine_side(team)
        self.assertIsNone(result)

    def test_determine_side_empty_list(self):
        # Empty list -> None
        team = []
        result = self.assistant.determine_side(team)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
