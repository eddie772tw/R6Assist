import os
import cv2
import numpy as np
import time
import sys
import io

# 設定輸出編碼以避免 Windows CP950 錯誤
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 將上層目錄加入 path 以便 import core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.phase_detector import PhaseDetector

def run_benchmark():
    print("=== PhaseDetector Performance Benchmark ===")
    
    # 建立專案目錄結構常數
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 確保有模板檔案，如果沒有則建立 dummy 模板，以供測試
    screenshot_dir = os.path.join(base_dir, "screenshot")
    if not os.path.exists(screenshot_dir):
        os.makedirs(screenshot_dir)
        
    temp_atk_path = os.path.join(screenshot_dir, "temp_atk.png")
    temp_def_path = os.path.join(screenshot_dir, "temp_def.png")
    
    # 製造一個容易匹配的實體圖案（例如帶黑色外框的白色十字架）
    pattern = np.zeros((40, 40), dtype=np.uint8)
    cv2.rectangle(pattern, (5, 5), (34, 34), 255, -1)
    cv2.line(pattern, (20, 5), (20, 34), 0, 4)
    cv2.line(pattern, (5, 20), (34, 20), 0, 4)
    
    # 支援 Windows 中文路徑的寫入 (強迫覆寫以確保與模擬畫面中的 pattern 100% 一致)
    try:
        _, buf = cv2.imencode(".png", pattern)
        buf.tofile(temp_atk_path)
        print("Created dummy temp_atk.png using imencode (Unicode safe)")
    except Exception as e:
        print(f"Error creating temp_atk.png: {e}")
        
    # 製造一個與 atk 完全不同的 def pattern (例如實心圓形)，避免 detect_phase 因兩模板相同而判斷平手死鎖
    def_pattern = np.zeros((40, 40), dtype=np.uint8)
    cv2.circle(def_pattern, (20, 20), 15, 255, -1)
    
    try:
        _, buf = cv2.imencode(".png", def_pattern)
        buf.tofile(temp_def_path)
        print("Created dummy temp_def.png using imencode (Unicode safe)")
    except Exception as e:
        print(f"Error creating temp_def.png: {e}")

    # 載入 PhaseDetector (必須在模板檔案建立後才加載，以確保 load_template 成功)
    detector = PhaseDetector(base_dir)
    
    # 1. 建立模擬 1080p 遊戲畫面 (1920x1080)
    # R6 頂部計分板背景為深色
    frame = np.full((1080, 1920, 3), 30, dtype=np.uint8)
    
    # 將階段圖標放在頂部中間稍微偏左的位置 (模擬計分板實況)
    icon_x = 1920 // 2 - 150
    icon_y = 15
    
    # 將三通道彩色版 pattern 貼進模擬畫面中
    color_pattern = cv2.cvtColor(pattern, cv2.COLOR_GRAY2BGR)
    th, tw = color_pattern.shape[:2]
    frame[icon_y:icon_y+th, icon_x:icon_x+tw] = color_pattern
    
    # 偵錯資訊印出
    print(f"[Debug] tmpl_atk is None: {detector.tmpl_atk is None}")
    if detector.tmpl_atk is not None:
        print(f"[Debug] tmpl_atk shape: {detector.tmpl_atk.shape}")
    
    # 模擬 detect_phase 中的 search_region 處理
    search_h = int(frame.shape[0] * 0.15)
    search_region = frame[0:search_h, 0:frame.shape[1]]
    search_region = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
    print(f"[Debug] search_region shape: {search_region.shape}")
    
    if detector.tmpl_atk is not None:
        res = cv2.matchTemplate(search_region, detector.tmpl_atk, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        print(f"[Debug] Direct Match Score (Scale 1.0): {max_val:.4f} at {max_loc}")
        
    # 先做一次匹配以確保一切正常運作，並寫入初始快取
    detector.detect_phase(frame)
    if detector.cached_x is None:
        print("[!] Warning: 階段匹配未能成功定位！請檢查模板載入狀態。")
        return
        
    print(f"  - 初始偵測成功: {detector.cached_team} at ({detector.cached_x}, {detector.cached_y}) with scale={detector.cached_scale}")
    
    print("\n--- 測試場景 1：全域多尺度匹配 (無快取 / 首次匹配) ---")
    start_time = time.perf_counter()
    iters = 15
    for _ in range(iters):
        # 每次匹配前手動清除快取以模擬首次全域搜索
        detector.cached_scale = None
        detector.cached_team = None
        detector.cached_x = None
        detector.cached_y = None
        detector.detect_phase(frame)
    global_time = (time.perf_counter() - start_time) / iters * 1000  # 毫秒
    print(f"首次全域匹配 (1080p 頂部 15% 窄帶) 平均耗時: {global_time:.3f} ms")
    
    print("\n--- 測試場景 2：智慧局部快取追蹤 (連續影格快取命中) ---")
    
    # 重新觸發一次全域匹配，重新寫入快取座標
    detector.detect_phase(frame)
    
    start_time = time.perf_counter()
    cache_iters = 300
    for _ in range(cache_iters):
        detector.detect_phase(frame)
    cache_time = (time.perf_counter() - start_time) / cache_iters * 1000  # 毫秒
    print(f"快取追蹤平均耗時: {cache_time:.4f} ms")
    
    # 計算效能提升比率
    if cache_time > 0:
        speedup = global_time / cache_time
        print(f"\n[*] 效能優化結果：")
        print(f"  - 智慧局部快取追蹤相較於全域匹配加速了 {speedup:.1f} 倍！")
        print(f"  - 在快取命中時，單影格 CPU 開銷減少了 {global_time - cache_time:.3f} ms")
    else:
        print("\n[*] 快取追蹤耗時趨近於 0 ms，加速比無限大！")
    print("===========================================")

if __name__ == "__main__":
    run_benchmark()
