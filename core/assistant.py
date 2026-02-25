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

import cv2
import os
import sys
import numpy as np
from collections import Counter

# Add root directory to path to allow running directly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.analyzer import TeamAnalyzer
from core.logic import TacticalAdvisor

class R6TacticalAssistant:
    def __init__(self, model_path, db_path="data/op_stats.json"):
        print("正在初始化戰術助理...")
        
        # 1. 初始化視覺神經 (Analyzer)
        # 這裡會自動尋找最新的模型，若找不到請手動指定路徑
        try:
            self.analyzer = TeamAnalyzer(model_path)
        except Exception as e:
            print(f"❌ 視覺模組初始化失敗: {e}")
            sys.exit(1)
            
        # 2. 初始化戰術大腦 (Logic)
        try:
            self.advisor = TacticalAdvisor(db_path)
        except Exception as e:
            print(f"❌ 戰術邏輯初始化失敗: {e}")
            sys.exit(1)
            
        print("✅ 系統就緒！")

    def determine_side(self, current_team):
        """
        根據目前的隊友名單，自動判斷是進攻方 (atk) 還是防守方 (def)
        """
        sides = []
        for name in current_team:
            if name == "Unknown" or name == "Recruit": 
                continue
                
            # 查表看這個人是哪一邊的
            op_data = self.advisor.get_operator_data(name)
            if op_data:
                side = op_data.get("side")
                if side in ["atk", "def"]:
                    sides.append(side)
        
        if not sides:
            return None # 無法判斷 (可能都沒選或辨識失敗)
            
        # 統計出現最多次的陣營 (多數決)
        most_common_side = Counter(sides).most_common(1)[0][0]
        return most_common_side

    def run_on_image(self, image_path):
        """
        核心流程：輸入圖片路徑 -> 輸出建議
        調整策略：
        1. 識別出所有 5 名幹員
        2. 排除最右邊的那一位 (假設為使用者)
        3. 用剩下的 4 位隊友來分析陣容缺口
        4. 給出建議，並評估使用者目前的選擇是否合適
        """
        if not os.path.exists(image_path):
            print(f"錯誤：找不到圖片 {image_path}")
            return

        print(f"\n{'='*40}")
        print(f"正在分析戰況: {os.path.basename(image_path)}")
        
        # 1. 讀取圖片
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("圖片讀取失敗")
            return

        # 2. 視覺辨識 (The Eyes)
        team_names, confidences = self.analyzer.analyze_screenshot(img)
        
        # 過濾掉 Unknown，讓顯示乾淨點
        print(f"👁️  視覺偵測完整結果: {team_names}")
        
        # 3. 陣營判斷 (Context Awareness) - 使用全體判斷比較準
        side = self.determine_side(team_names)
        
        if side is None:
            print("⚠️  無法判斷陣營 (隊伍名單資訊不足)，略過推薦。")
            return
            
        side_text = "⚔️ 進攻方 (Attacker)" if side == "atk" else "🛡️ 防守方 (Defender)"
        print(f"ℹ️  當前陣營: {side_text}")
        
        # === 新增邏輯：區分「使用者」與「隊友」 ===
        # 根據 analyzer.py 的 ROI 邏輯 (start_x - i*step)，
        # Index 0 是最右邊 (Start)，Index 4 是最左邊。
        # 因此 team_names[0] 是最右邊的幹員 (使用者)
        
        if len(team_names) >= 1:
            user_pick = team_names[0]
            # 轉換為視覺橫向順序 (由左至右)，即反轉原本由右至左的偵測順序
            teammates = team_names[1:][::-1]
        else:
            user_pick = "Unknown"
            teammates = []

        print(f"👤 使用者目前選擇 (最右): {user_pick}")
        print(f"👥 隊友陣容 (由左至右): {teammates}")
        
        # 分析隊伍缺口
        missing_roles = self.advisor.get_missing_roles(teammates, side)
        if missing_roles:
            print(f"⚠️  隊友陣容缺乏: {', '.join(missing_roles)}")
        else:
            print(f"✅ 隊友陣容職能相當完整！")

        # 4. 戰術推薦 (The Brain)
        # 用「隊友」去跑推薦，看看完美的第 5 人該是誰
        # 這裡我們請求大量的推薦名單 (top_n=99)，方便我們找 user_pick 的排名
        recommendations = self.advisor.recommend(teammates, side=side, top_n=99)
        
        print("\n🧠 戰術建議分析:")
        
        if not recommendations:
            print("沒有特別的推薦人選 (可能資料庫不完整)")
            print(f"{'='*40}\n")
            return

        # 顯示前 5 名建議
        print(f"{'排名':<6} {'幹員':<12} {'推薦指數':<10} {'補足職能'}")
        print("-" * 50)
        
        for i, rec in enumerate(recommendations[:5]):
            name = rec['name']
            score = rec['score']
            reasons = ", ".join(rec['roles'])
            print(f"#{i+1:<5} {name:<12} {score:<10} {reasons}")
            
        print("-" * 50)
        
        # 5. 比較與建議 (Review)
        # 找找看使用者的選擇在推薦名單的第幾名
        top_pick = recommendations[0]
        user_rank = -1
        user_score = 0
        user_rec_info = None
        
        for i, rec in enumerate(recommendations):
            if rec['name'] == user_pick:
                user_rank = i + 1
                user_score = rec['score']
                user_rec_info = rec
                break
        
        print("\n⚖️  選擇評估:")
        if user_pick in ["Unknown", "Recruit"]:
            print(f"👉 你尚未選擇有效幹員 ({user_pick})")
            print(f"💡 強烈建議選擇: {top_pick['name']} (分數: {top_pick['score']})")
            
        elif user_rank == -1:
            # 沒在推薦名單內 (可能是陣營錯誤，或是資料庫沒有，或是已被隊友選走-雖然這裡是扣除隊友後的)
            print(f"👉 你的選擇: {user_pick}")
            print(f"❌ 此選擇不在推薦名單中 (可能是資料庫缺失或不符合當前陣營戰術需求)")
            print(f"💡 建議改選: {top_pick['name']}")
            
        else:
            print(f"👉 你的選擇: {user_pick} (評分: {user_score}, 排名: #{user_rank})")
            
            # 判斷是否需要換角
            # 簡單邏輯：如果分數差距 > 1.0 且 排名 > 3，建議換角
            score_diff = top_pick['score'] - user_score
            
            if user_rank == 1:
                print(f"✅ 完美！這是目前的最佳選擇。")
            elif score_diff < 1.0 and user_rank <= 3:
                print(f"✅ 這是一個不錯的選擇 (與第一名 {top_pick['name']} 差距 {score_diff:.1f})。")
            else:
                print(f"⚠️  建議換角！")
                print(f"   {top_pick['name']} 會是更好的選擇 (分數高出 {score_diff:.1f})")
                print(f"   主要原因: 隊伍極需 {', '.join(top_pick['roles'])}")
            
        print(f"{'='*40}\n")

# --- 程式入口點 ---
if __name__ == "__main__":
    
    # 取得專案根目錄路徑
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 設定模型路徑 (請確認這指向你的 best.pt)
    # 如果你在 analyzer.py 裡寫過自動搜尋邏輯，這裡傳入 None 也可以
    MODEL_PATH = None 
    
    # 確保 op_stats.json 也能正確被找到
    DB_PATH = os.path.join(BASE_DIR, "data", "op_stats.json")
    
    app = R6TacticalAssistant(MODEL_PATH, db_path=DB_PATH)

    # 指定要測試的圖片 (自動組合絕對路徑)
    screenshot_dir = os.path.join(BASE_DIR, "screenshot")
    
    # 檢查目標資料夾是否存在
    if not os.path.exists(screenshot_dir):
        print(f"警告：找不到 screenshot 資料夾: {screenshot_dir}")
        TEST_IMAGES = []
    else:
        # Load all images from the screenshot directory
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
        TEST_IMAGES = [
            os.path.join(screenshot_dir, f) 
            for f in os.listdir(screenshot_dir) 
            if f.lower().endswith(valid_extensions)
        ]

    for img_path in TEST_IMAGES:
        app.run_on_image(img_path)