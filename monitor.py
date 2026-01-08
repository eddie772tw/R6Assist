import time
import os
import cv2
import numpy as np
import sys
try:
    import dxcam
    HAS_DXCAM = True
except ImportError:
    HAS_DXCAM = False
    import mss

# 引入核心模組
from main import R6TacticalAssistant

class GameMonitor:
    def __init__(self, target_fps=2):
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps
        
        print("正在初始化 R6 戰術監控系統...")
        # 初始化我們之前寫好的助手 (自動載入模型與資料庫)
        # 注意：這裡會呼叫 R6TacticalAssistant 的 init，確保 analyzer 和 advisor 都就緒
        self.assistant = R6TacticalAssistant(None)
        
        # 狀態快取 (State Cache)
        self.last_team_str = ""  # 用字串來比對陣容是否變化
        self.last_side = None
        
        # 設定截圖工具
        self.use_dxcam = False
        if HAS_DXCAM:
            try:
                # 嘗試初始化 DXCam (高效能 Desktop Duplication API)
                self.camera = dxcam.create(output_idx=0, output_color="BGR")
                self.use_dxcam = True
                self.res_w, self.res_h = self.camera.width, self.camera.height
                print("🚀 已啟用 DXCam 高速截圖引擎")
            except Exception as e:
                print(f"⚠️ DXCam 初始化異常: {e}，將降級為 MSS")
        
        if not self.use_dxcam:
            if 'mss' not in sys.modules:
                import mss
            self.sct = mss.mss()
            self.monitor = self.sct.monitors[1] 
            self.res_w = self.monitor['width']
            self.res_h = self.monitor['height']
            if not HAS_DXCAM:
                print("ℹ️  提示: 未檢測到 dxcam，建議執行 `pip install dxcam` 以提升效能") 

    def clear_console(self):
        """
        不再使用 cls，而是把游標移動到左上角 (ANSI Escape Code)
        這樣可以避免畫面閃爍
        """
        sys.stdout.write("\033[H") 
        sys.stdout.flush()

    def print_line(self, text, clear_end=True):
        """
        印出一行文字，並視需要清除該行剩餘空間
        """
        # \033[K 是清除從游標到行尾的 ANSI Code
        clear_code = "\033[K" if clear_end else ""
        sys.stdout.write(f"{text}{clear_code}\n")

    def process_logic(self, team_names):
        """
        執行戰術邏輯並印出報告 (使用 sys.stdout.write 優化顯示)
        """
        # 1. 區分自己與隊友
        if not team_names:
            self.print_line("等待選角畫面...", clear_end=True)
            return

        user_pick = team_names[0]
        teammates = team_names[1:]

        # 2. 判斷陣營
        side = self.assistant.determine_side(team_names)
        if side is None:
            self.print_line(f"等待有效陣容... (偵測: {','.join(team_names)})")
            return

        side_text = "⚔️ 進攻 (ATK)" if side == "atk" else "🛡️ 防守 (DEF)"
        
        # 3. 執行推薦運算
        result = self.assistant.advisor.evaluate_and_recommend(user_pick, teammates, side=side)
        curr = result['current_pick']
        recs = result['recommendations']

        # --- 繪製儀表板 ---
        # 每次繪製前先把游標移回家，不要 cls
        self.clear_console()
        
        self.print_line(f"{'='*40}")
        self.print_line(f"🔴 R6 TACTICAL MONITOR | FPS: {self.target_fps}")
        self.print_line(f"{'='*40}")
        self.print_line(f"ℹ️  當前局勢: {side_text}")
        self.print_line(f"👤 你的選擇: {user_pick:<15}")
        self.print_line(f"👥 隊友陣容: {', '.join(teammates)}")
        
        # 顯示缺口
        missing = self.assistant.advisor.get_missing_roles(teammates, side)
        if missing:
            self.print_line(f"⚠️  隊伍缺乏: {', '.join(missing)}")
        else:
            self.print_line(f"✅ 隊伍職能完整")

        self.print_line("-" * 40)
        
        # 顯示當前評分
        if curr['name'] != "Unknown":
            score_bar = "█" * int(curr['score'])
            self.print_line(f"📊 你的評分: {curr['score']:<4} {score_bar}")
            
            suggestion = ""
            if curr['score'] < 5 and recs:
                top_score = recs[0]['score']
                diff = top_score - curr['score']
                
                # 只有當分數差距夠大才建議
                if diff > 1.5:
                    # 找出所有同為最高分的幹員
                    top_ops = [r['name'] for r in recs if r['score'] == top_score]
                    
                    # 格式化顯示 (如果太多個，用逗號分隔)
                    top_ops_str = ", ".join(top_ops[:3]) # 最多顯示 3 個避免太長
                    if len(top_ops) > 3:
                        top_ops_str += "..."
                        
                    suggestion = f"⚠️  建議換角 -> {top_ops_str} (+{diff:.1f})"
            
            # 如果有建議就印出，沒有就印空行 (清除舊紀錄)
            self.print_line(f"   {suggestion}")
        else:
            self.print_line("   (請選擇有效幹員以查看評分)")

        self.print_line("\n💡 最佳補位建議:")
        for i in range(5):
            if i < len(recs):
                r = recs[i]
                highlight = ">>" if i == 0 else "  "
                self.print_line(f"{highlight} #{i+1} {r['name']:<10} {r['score']:<5} {', '.join(r['roles'])}")
            else:
                self.print_line("") # 清除多餘行

        self.print_line(f"\n{'='*40}")
        self.print_line("按 Ctrl+C 停止監控...                   ")
        
        sys.stdout.flush()

    def run(self):
        # 先清空一次畫面
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"監控開始！目標解析度: {self.res_w}x{self.res_h}")
        print("請切換回遊戲畫面...")
        
        try:
            while True:
                start_time = time.time()

                # 1. 截圖 (DXCam 或 MSS)
                if self.use_dxcam:
                    img = self.camera.grab()
                    if img is None:
                        continue
                else:
                    screenshot = self.sct.grab(self.monitor)
                    img = np.array(screenshot)
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # 2. 智慧畫面偵測 (減少不必要的運算)
                # 計算與上一禎的差異，只有畫面變動時才重新分析
                if hasattr(self, 'last_frame') and self.last_frame is not None:
                    # 縮小圖片以快速比較 (降低比較成本)
                    small_curr = cv2.resize(img, (64, 64))
                    small_last = cv2.resize(self.last_frame, (64, 64))
                    diff = cv2.absdiff(small_curr, small_last)
                    non_zero_count = np.count_nonzero(diff)
                    
                    # 如果差異太小 (畫面靜止)，跳過本次分析 (節省 CPU)
                    if non_zero_count < 100:  # 閾值可依需求調整
                        self._wait_for_next_frame(start_time)
                        continue

                self.last_frame = img.copy()

                # 3. 視覺辨識
                team_names, _ = self.assistant.analyzer.analyze_screenshot(img)
                
                # 3. 永遠直接刷新畫面，不判斷是否變化 (因為是用原地刷新，成本很低)
                # 這樣可以確保留下的文字不會卡住，且感覺更流暢
                # 但為了效能，我們還是可以在這裡做一點小優化：如果完全沒變且已經畫過一次，可以跳過 Logic 計算
                
                current_team_str = ",".join(team_names)
                
                # 這裡我們選擇每次都重繪，因為原地刷新 (ANSI) 的速度極快
                # 而且這樣可以確保倒數計時或動畫效果 (如果有) 正常運作
                valid_count = sum(1 for n in team_names if n != "Unknown")
                
                if valid_count > 0:
                     self.process_logic(team_names)
                     self.last_team_str = current_team_str
                else:
                    # 選角畫面還沒出來，或過場中
                    # 可以顯示一個簡單的 Waiting 動畫
                    pass
                
                self._wait_for_next_frame(start_time)

        except KeyboardInterrupt:
            print("\n🛑 監控已停止。")

    def _wait_for_next_frame(self, start_time):
        elapsed = time.time() - start_time
        wait_time = self.frame_time - elapsed
        if wait_time > 0:
            time.sleep(wait_time)

if __name__ == "__main__":
    # 啟用 Windows 的 ANSI 支援 (Python 3.6+ 在 Win10 通常自動支援，但保險起見)
    os.system("") 
    monitor = GameMonitor(target_fps=2)
    monitor.run()