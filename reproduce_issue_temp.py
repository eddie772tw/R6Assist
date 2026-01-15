
import sys
import os

# Adjust path to import modules
sys.path.append(r"c:\Users\eddie\Desktop\Utility\R6Assist")

from logic import TacticalAdvisor

def test_missing_roles():
    advisor = TacticalAdvisor()
    
    # User: Zero (Intel, Anti-Gadget)
    # Teammates: Ram (Breach, Anti-Gadget), Fuze (Anti-Gadget), Amaru (Front Line, Map Control), Rauora (Support, Map Control)
    
    user = "Zero"
    teammates = ["Ram", "Fuze", "Amaru", "Rauora"]
    full_team = [user] + teammates
    side = "atk"
    
    print(f"User: {user}")
    print(f"Teammates: {teammates}")
    print(f"Full Team: {full_team}")
    
    # Current behavior in monitor.py (checking only teammates)
    missing_teammates_only = advisor.get_missing_roles(teammates, side)
    print(f"\n[Current] Missing roles (Teammates only): {missing_teammates_only}")
    
    # Expected behavior (checking full team)
    missing_full_team = advisor.get_missing_roles(full_team, side)
    print(f"\n[Proposed] Missing roles (Full Team): {missing_full_team}")
    
    if "Intel" in missing_teammates_only and "Intel" not in missing_full_team:
        print("\n=> Issue Reproduced: Intel is missing when excluding user, but present when including user.")
    else:
        print("\n=> Issue NOT Reproduced exactly as expected.")

if __name__ == "__main__":
    test_missing_roles()
