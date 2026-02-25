# Copyright (C) 2026 R6Assist Developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import os
from collections import defaultdict

class TacticalAdvisor:
    def __init__(self, db_path="data/op_stats.json"):
        self.db = self._load_db(db_path)
        
        # === 權重設定 (可隨時微調) ===
        # 分數越高代表該職能越核心/不可或缺
        self.role_weights = {
            # 進攻方權重
            "Breach": 8,       # 切牆/破壞地形 (進攻核心)
            "Anti-Gadget": 7,  # 清除電網/干擾器 (輔助切牆)
            "Intel": 6,        # 情資 (無人機/掃描)
            "Support": 3,      # 輔助 (煙霧/補血/護盾)
            "Front Line": 4,   # 槍線/突破手 (通常大家都會搶著選，所以權重放低)
            "Map Control": 3,  # 區域控制
            
            # 防守方權重
            "Anti-Entry": 7,   # 阻滯進攻 (防止 Rush)
            "Trapper": 6,      # 陷阱 (削減血量/情資)
            "Crowd Control": 5,# 群體控制 (Echo/Melusi)
            # 防守方的 Intel/Anti-Gadget/Support 沿用上方設定
        }

        # 防守方特定職能權重覆寫 (若需要與進攻方不同)
        self.def_role_overrides = {
            "Anti-Gadget": 6,
        }

        # === 邊際效益遞減設定 ===
        # 當隊伍中已經有 N 個人擁有該職能時，該職能的加分會打折
        # 邏輯：第一個切牆角最有價值(100%)，第二個就沒那麼急迫了(40%)
        self.diminishing_returns = [1.0, 0.4, 0.1, 0.0, 0.0] 

    def _load_db(self, path):
        """載入並處理 JSON 資料庫"""
        if not os.path.exists(path):
            # 嘗試在當前目錄尋找
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, path)
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"Tactical Advisor Ready (Loaded {len(data)} operators)")
            return data
        except Exception as e:
            print(f"DB Load Failed: {e}")
            return {}

    def analyze_team_composition(self, current_team_names):
        """
        分析目前隊伍的職能分佈
        :param current_team_names: list of strings, e.g. ["Ash", "Sledge"]
        :return: dict, {role: count}
        """
        composition = defaultdict(int)
        
        for name in current_team_names:
            # 處理名稱對應 (例如 "Recruit" 可能對應 "Recruit (ATK)")
            # 這裡做簡單的模糊搜尋
            op_data = self.get_operator_data(name)
            
            if op_data:
                roles = op_data.get("role", [])
                if isinstance(roles, str): roles = [roles] # 防呆
                
                for role in roles:
                    composition[role] += 1
                    
        return composition

    def get_operator_data(self, name):
        """從 DB 獲取幹員資料，處理名稱不一致問題"""
        # 直接命中
        if name in self.db:
            return self.db[name]
        
        # 處理 "Recruit" 這種特殊情況
        # 如果輸入 "Recruit"，我們會回傳 Unknown，因為無法確定攻守
        # 實戰中 analyzer 應該要判斷 side 傳入 Recruit (ATK) 或 (DEF)
        # 這裡做一個簡單的 fallback
        for key in self.db.keys():
            if name.lower() == key.lower():
                return self.db[key]
            if name in key: # e.g. "Recruit" in "Recruit (ATK)"
                return self.db[key]
        return None

    def recommend(self, current_team, side="atk", top_n=5):
        """
        核心演算法：根據缺少的職能推薦幹員
        :param current_team: 目前隊友名單 (list)
        :param side: "atk" 或 "def"
        :return: 推薦名單 (list of tuples) -> [(Name, Score, Reasons), ...]
        """
        # 1. 分析現況：目前隊伍有哪些職能？
        current_roles = self.analyze_team_composition(current_team)
        
        scores = []

        # 2. 遍歷所有可用幹員
        for op_name, data in self.db.items():
            # 2.1 過濾：陣營不符、已經被選走、或是不完整的資料
            if data.get("side") != side: continue
            if op_name in current_team: continue
            if "Recruit" in op_name: continue # 不推薦選新進人員
            
            op_roles = data.get("role", [])
            if not op_roles or "Unknown" in op_roles: continue

            # 2.2 計算分數
            total_score = 0
            reasons = []

            for role in op_roles:
                # 取得該職能的基礎權重 (預設 1 分)
                base_weight = self.role_weights.get(role, 2)
                
                # 防守方權重覆寫
                if side == "def" and role in self.def_role_overrides:
                    base_weight = self.def_role_overrides[role]
                
                # 檢查隊伍目前有幾個人已經有這個職能了
                existing_count = current_roles[role]
                
                # 計算衰減係數
                decay = self.diminishing_returns[min(existing_count, len(self.diminishing_returns)-1)]
                
                # 該職能得分 = 權重 * 稀缺係數
                role_score = base_weight * decay
                
                if role_score > 0:
                    total_score += role_score
                    # 記錄加分原因 (例如: "Breach +8.0")
                    reasons.append(f"{role}")

            # 2.3 額外加分 (Tier/Meta 加分項)
            # 這部分可以手動在 op_stats.json 裡加一個 "meta_rank" 欄位來控制
            # 目前先留空
            
            if total_score > 0:
                scores.append({
                    "name": op_name,
                    "score": round(total_score, 2),
                    "roles": reasons
                })

        # 3. 排序：分數高 -> 低
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        return scores[:top_n]

    def get_missing_roles(self, current_team, side):
        """取得目前隊伍缺少的職能 (數量為 0 者)"""
        composition = self.analyze_team_composition(current_team)
        
        # 定義各陣營的核心職能
        if side == "atk":
            core_roles = ["Breach", "Anti-Gadget", "Intel", "Support", "Front Line", "Map Control"]
        else:
            # 防守方
            core_roles = ["Anti-Entry", "Trapper", "Crowd Control", "Intel", "Support", "Anti-Gadget"]
            
        missing = []
        for role in core_roles:
            if composition[role] == 0:
                missing.append(role)
                
        # 根據權重排序 (越重要的缺口排越前面)
        missing.sort(key=lambda r: self.role_weights.get(r, 0), reverse=True)
        
        return missing

    def evaluate_and_recommend(self, user_pick, teammates, side="atk"):
        """
        綜合評估：回傳 (1) 使用者目前的評分 (2) 最佳推薦名單
        這主要是為了 monitor.py 設計的，一次呼叫拿回所有 UI 需要的數據
        """
        # 1. 取得給「隊友」的最佳建議 (排除已選的)
        recommendations = self.recommend(teammates, side=side, top_n=10)
        
        # 2. 計算使用者目前的得分
        current_score = 0
        if user_pick and user_pick != "Unknown" and user_pick not in ["Recruit", "Recruit (ATK)", "Recruit (DEF)"]:
            # 為了計算分數，我們要把 user_pick「暫時」當作建議對象跑一次邏輯
            # 或是直接從 recommend 的結果裡找 (如果他在前10名)
            # 但如果他選得很爛排在第 50 名，上面的 recommendations 找不到
            # 所以還是單獨算一次最準
            
            # 使用跟 recommend 一樣的邏輯來算分
            # 先取得這個角色的資料
            op_data = self.get_operator_data(user_pick)
            if op_data and op_data.get("side") == side:
                current_roles_count = self.analyze_team_composition(teammates)
                op_roles = op_data.get("role", [])
                
                temp_total = 0
                for role in op_roles:
                    base = self.role_weights.get(role, 2)
                    if side == "def" and role in self.def_role_overrides:
                        base = self.def_role_overrides[role]

                    exist = current_roles_count[role]
                    decay = self.diminishing_returns[min(exist, len(self.diminishing_returns)-1)]
                    temp_total += base * decay
                current_score = round(temp_total, 2)
                
        return {
            "current_pick": {"name": user_pick, "score": current_score},
            "recommendations": recommendations
        }

    # --- 測試區塊 ---
if __name__ == "__main__":
    advisor = TacticalAdvisor()
    
    # 模擬情境：進攻方，隊友已經選了 Ash (Front Line/Breach) 和 Kali (Sniper/Anti-Gadget)
    # 註：Kali 在你的 JSON 裡是 Anti-Gadget + Support
    print("\n--- 模擬進攻方 (Attacker) ---")
    current_team = ["Ash", "Zofia", "Iana", "Twitch"]
    print(f"目前陣容: {current_team}")
    
    recs = advisor.recommend(current_team, side="atk")
    
    print(f"\n{'幹員名稱':<12} {'推薦分數':<10} {'主要職能'}")
    print("-" * 40)
    for rec in recs:
        print(f"{rec['name']:<12} {rec['score']:<10} {', '.join(rec['roles'])}")
        
    # 模擬情境：防守方，隊友選了 Vigil (Roamer)
    print("\n\n--- 模擬防守方 (Defender) ---")
    current_team_def = ["Vigil", "Azami", "Kapkan", "Tachanka"]
    print(f"目前陣容: {current_team_def}")
    
    recs_def = advisor.recommend(current_team_def, side="def")
    
    print(f"\n{'幹員名稱':<12} {'推薦分數':<10} {'主要職能'}")
    print("-" * 40)
    for rec in recs_def:
        print(f"{rec['name']:<12} {rec['score']:<10} {', '.join(rec['roles'])}")