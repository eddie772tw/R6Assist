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
import numpy as np
import time
from ultralytics import YOLO

# 1. 引入我們之前寫好的 ROI 設定 (確保邏輯一致)
class ROIConfig:
    def __init__(self, screen_width, screen_height):
        self.w = screen_width
        self.h = screen_height

    def get_rois(self, mode="NORMAL"):
        rois = []
        if mode == "NORMAL":
            # 你的 2K 基準數據
            anchor_x_ratio = 0.3957 
            y_ratio = 0.0111         
            w_ratio = 0.01875        
            h_ratio = 0.0326         
            stride_ratio = 0.0250    
        elif mode == "REPICK":
            # 進攻方重選
            anchor_x_ratio = 0.3590  
            y_ratio = 0.0056         
            w_ratio = 0.0262         
            h_ratio = 0.0465         
            stride_ratio = 0.0621    
        
        # 計算像素
        base_w = int(self.w * w_ratio)
        base_h = int(self.h * h_ratio)
        base_y = int(self.h * y_ratio)
        start_x = int(self.w * anchor_x_ratio)
        step_x = int(self.w * stride_ratio)

        for i in range(5):
            current_x = start_x - (i * step_x)
            rois.append((current_x, base_y, base_w, base_h))
        return rois

# 2. 核心分析器
class TeamAnalyzer:
    def __init__(self, model_path=None):
        self.model_path = self._find_model_path(model_path)
        print(f"正在載入模型: {self.model_path} ...")
        self.model = YOLO(self.model_path)
        print("模型載入完成！")

    def _find_model_path(self, provided_path):
        """
        嘗試在多個位置尋找模型檔案，優先尋找最新訓練的模型
        """
        # 1. 檢查使用者提供的路徑
        if provided_path and os.path.exists(provided_path):
            return provided_path

        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 尋找最新的訓練結果資料夾 (e.g. r6_operator_classifier, r6_operator_classifier2, ...)
        runs_dir = os.path.join(base_dir, "runs", "classify")
        best_run_path = None
        max_run_num = -1
        
        if os.path.exists(runs_dir):
            for dirname in os.listdir(runs_dir):
                if dirname.startswith("r6_operator_classifier"):
                    # 解析版本號
                    suffix = dirname.replace("r6_operator_classifier", "")
                    if suffix == "":
                        run_num = 1
                    elif suffix.isdigit():
                        run_num = int(suffix)
                    else:
                        continue
                    
                    # 檢查該資料夾內是否有 best.pt
                    candidate_weights = os.path.join(runs_dir, dirname, "weights", "best.pt")
                    if os.path.exists(candidate_weights):
                        if run_num > max_run_num:
                            max_run_num = run_num
                            best_run_path = candidate_weights

        candidates = []
        if best_run_path:
            candidates.append(best_run_path)

        candidates.extend([
            # 1. 預設名稱在當前目錄
            "best.pt",
            os.path.join(base_dir, "best.pt"),
            # 2. 舊的備份路徑 (上一層目錄)
            os.path.join(base_dir, "..", "runs", "classify", "r6_operator_classifier", "weights", "best.pt"),
        ])

        for path in candidates:
            if path and os.path.exists(path):
                return path
        
        # 如果都找不到，拋出清楚的錯誤
        raise FileNotFoundError(
            f"找不到模型檔案 (best.pt)。請確認已執行訓練 (train.py) 或將模型檔案放置於正確位置。\n"
            f"搜尋路徑: {candidates}"
        )

    def _predict_rois(self, img, mode):
        """
        輔助函式：針對特定模式進行 ROI 裁切與預測
        回傳: (team_composition, confidences, avg_confidence)
        """
        h, w = img.shape[:2]
        roi_config = ROIConfig(w, h)
        rois = roi_config.get_rois(mode=mode)
        
        team_composition = []
        confidences = []

        # 準備批量推論的圖片列表
        crop_images = []
        
        for (x, y, rw, rh) in rois:
            # 邊界檢查
            if x < 0 or y < 0 or x+rw > w or y+rh > h:
                # 若 ROI 超出邊界，塞入一個全黑圖片避免 crash，或直接跳過
                # 這裡選擇塞黑圖保持 list 長度一致 (5人)
                crop_images.append(np.zeros((64, 64, 3), dtype=np.uint8))
                continue
                
            crop = img[y:y+rh, x:x+rw]
            if crop.size == 0: 
                crop_images.append(np.zeros((64, 64, 3), dtype=np.uint8))
                continue
            
            crop_images.append(crop)

        if not crop_images:
            return [], [], 0.0

        # === 批量預測 ===
        results = self.model.predict(crop_images, verbose=False, imgsz=64)

        for result in results:
            probs = result.probs
            top1_index = probs.top1
            top1_conf = probs.top1conf.item()
            class_name = result.names[top1_index]
            
            if top1_conf > 0.8:
                if "recruit" in class_name.lower():
                    clean_name = "Recruit"
                else:
                    clean_name = class_name
                team_composition.append(clean_name)
                confidences.append(top1_conf)
            else:
                team_composition.append("Unknown")
                confidences.append(top1_conf)

        # 計算平均信心度 (作為該模式的可信度指標)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return team_composition, confidences, avg_conf, crop_images

    def analyze_screenshot(self, img):
        """
        輸入一張遊戲截圖，自動判斷是 NORMAL 還是 REPICK 模式，並回傳最佳結果
        Return: (team_names, confidences, crop_images)
        """
        # 1. 先嘗試 NORMAL 模式
        team_norm, confs_norm, avg_norm, crops_norm = self._predict_rois(img, "NORMAL")

        # 如果信心度夠高 (>= 90%)，直接採用，不用浪費時間測別的
        if avg_norm >= 0.90:
            return team_norm, confs_norm, crops_norm
            
        # 2. 如果信心度不足，嘗試 REPICK 模式
        # print(f"NORMAL 模式信心度 ({avg_norm:.1%}) 低於 90%，嘗試 REPICK 模式...")
        team_repick, confs_repick, avg_repick, crops_repick = self._predict_rois(img, "REPICK")

        # 3. 比較兩種模式的信心度
        if avg_repick > avg_norm:
            # print(f"判定為 REPICK 模式 (信心度: {avg_repick:.1%})")
            return team_repick, confs_repick, crops_repick
        else:
            # print(f"維持 NORMAL 模式 (信心度: {avg_norm:.1%})")
            return team_norm, confs_norm, crops_norm

# --- 測試區塊 ---
if __name__ == "__main__":
    import os
    import glob

    try:
        # 自動偵測最佳模型
        analyzer = TeamAnalyzer()

        # 讀取你的測試截圖 (screenshot 資料夾)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        test_folder = os.path.join(base_dir, "screenshot")
        images = glob.glob(os.path.join(test_folder, "*.jpg")) + glob.glob(os.path.join(test_folder, "*.png"))

        if not images:
            print(f"找不到測試圖片 (路徑: {test_folder})，請確認 screenshot 資料夾內有截圖")
        else:
            print(f"\n=== 開始批量測試 ({len(images)} 張圖片) ===")
            for img_path in images:
                # 讀取圖片 (處理中文路徑)
                img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None: continue

                print(f"\n測試圖片: {os.path.basename(img_path)}")
                start_time = time.time()
                
                # 執行分析
                team, confs, _ = analyzer.analyze_screenshot(img)
                
                end_time = time.time()
                process_time = (end_time - start_time) * 1000 #轉毫秒

                # 顯示結果
                print(f"耗時: {process_time:.2f} ms")
                print(f"偵測陣容: {team}")
                
                # 簡單驗證信心度
                avg_conf = sum(confs)/len(confs) if confs else 0
                print(f"平均信心度: {avg_conf:.1%}")
                print("-" * 30)

    except Exception as e:
        print(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc()