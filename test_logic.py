import unittest
from unittest.mock import patch
from collections import defaultdict

from core.logic import TacticalAdvisor

class TestGetMissingRoles(unittest.TestCase):
    def setUp(self):
        # TacticalAdvisor initialization loads op_stats.json.
        # We can just instantiate it.
        self.advisor = TacticalAdvisor()

    @patch('core.logic.TacticalAdvisor.analyze_team_composition')
    def test_get_missing_roles_atk_partial(self, mock_analyze):
        """Test with partial attacker roles fulfilled."""
        # Set up mock to return some filled roles
        mock_composition = defaultdict(int, {
            "Breach": 1,
            "Intel": 1,
            "Anti-Gadget": 0,
            "Support": 0,
            "Front Line": 0,
            "Map Control": 0
        })
        mock_analyze.return_value = mock_composition

        missing = self.advisor.get_missing_roles(["Ash", "Lion"], "atk")

        # Core roles for atk: ["Breach", "Anti-Gadget", "Intel", "Support", "Front Line", "Map Control"]
        # Expected missing: Anti-Gadget(7), Support(3), Front Line(4), Map Control(3)
        # Expected sorted order: Anti-Gadget, Front Line, Support, Map Control
        self.assertEqual(missing, ["Anti-Gadget", "Front Line", "Support", "Map Control"])
        mock_analyze.assert_called_once_with(["Ash", "Lion"])

    @patch('core.logic.TacticalAdvisor.analyze_team_composition')
    def test_get_missing_roles_def_partial(self, mock_analyze):
        """Test with partial defender roles fulfilled."""
        # Set up mock to return some filled roles
        mock_composition = defaultdict(int, {
            "Anti-Entry": 1,
            "Crowd Control": 1,
            "Trapper": 0,
            "Intel": 0,
            "Support": 0,
            "Anti-Gadget": 0
        })
        mock_analyze.return_value = mock_composition

        missing = self.advisor.get_missing_roles(["Mute", "Echo"], "def")

        # Core roles for def: ["Anti-Entry", "Trapper", "Crowd Control", "Intel", "Support", "Anti-Gadget"]
        # Expected missing: Trapper(6), Intel(6), Support(3), Anti-Gadget(7)
        # Weights: Anti-Gadget(7), Trapper(6), Intel(6), Support(3)
        # Since Trapper is before Intel in core_roles, stable sort preserves Trapper before Intel
        self.assertEqual(missing, ["Anti-Gadget", "Trapper", "Intel", "Support"])
        mock_analyze.assert_called_once_with(["Mute", "Echo"])

    @patch('core.logic.TacticalAdvisor.analyze_team_composition')
    def test_get_missing_roles_all_present(self, mock_analyze):
        """Test when all core roles are fulfilled."""
        # Setup for atk side where all core roles are present
        mock_composition = defaultdict(int, {
            "Breach": 1,
            "Anti-Gadget": 1,
            "Intel": 2,
            "Support": 1,
            "Front Line": 1,
            "Map Control": 1
        })
        mock_analyze.return_value = mock_composition

        missing = self.advisor.get_missing_roles(["Ash", "Thermite", "Thatcher", "Lion", "Gridlock"], "atk")
        self.assertEqual(missing, [])

    @patch('core.logic.TacticalAdvisor.analyze_team_composition')
    def test_get_missing_roles_none_present(self, mock_analyze):
        """Test when none of the core roles are fulfilled."""
        # Mock composition with 0 for everything
        mock_composition = defaultdict(int)
        mock_analyze.return_value = mock_composition

        missing = self.advisor.get_missing_roles(["Recruit"], "atk")

        # Expected all atk core roles ordered by weights
        # Breach(8), Anti-Gadget(7), Intel(6), Front Line(4), Support(3), Map Control(3)
        self.assertEqual(missing, ["Breach", "Anti-Gadget", "Intel", "Front Line", "Support", "Map Control"])

if __name__ == '__main__':
    unittest.main()
