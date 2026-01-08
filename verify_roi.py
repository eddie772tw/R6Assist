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
import numpy as np
import os
import glob

class ROIConfig:
    def __init__(self, screen_width, screen_height):
        self.w = screen_width
        self.h = screen_height
        # 這裡使用我們剛剛根據 2K 解析度算出來的黃金比例常數
        # 錨點是「最右邊 (靠近計時器)」的那個隊友圖標

    def get_rois(self, mode="NORMAL"):
        """
        根據模式回傳 5 個隊友圖標的 (x, y, w, h) 列表
        順序：從最右邊(錨點) 到 最左邊
        """
        rois = []
        
        if mode == "NORMAL":
            # 一般狀態 (小圖標，緊密排列)
            # 基準數據來源: 2560x1440 截圖
            anchor_x_ratio = 0.3957  # 1013 / 2560
            y_ratio = 0.0111         # 16 / 1440
            w_ratio = 0.01875        # 48 / 2560
            h_ratio = 0.0326         # 47 / 1440
            stride_ratio = 0.0250    # 64 / 2560 (間距)
            
        elif mode == "REPICK":
            # 進攻方重選狀態 (大圖標，寬鬆排列)
            # 基準數據來源: 2560x1440 截圖
            anchor_x_ratio = 0.3590  # 919 / 2560
            y_ratio = 0.0056         # 8 / 1440
            w_ratio = 0.0262         # 67 / 2560
            h_ratio = 0.0465         # 67 / 1440
            stride_ratio = 0.0621    # 159 / 2560 (間距很大)
        else:
            return []

        # 將比例轉換為當前解析度的具體像素
        base_w = int(self.w * w_ratio)
        base_h = int(self.h * h_ratio)
        base_y = int(self.h * y_ratio)
        start_x = int(self.w * anchor_x_ratio)
        step_x = int(self.w * stride_ratio)

        # 產生 5 個框 (從右向左推算：錨點減去間距)
        for i in range(5):
            current_x = start_x - (i * step_x)
            rois.append((current_x, base_y, base_w, base_h))
            
        return rois

def draw_rois(image, rois, color, label_prefix):
    """在地圖上畫框並標上序號的輔助函式"""
    for i, (x, y, w, h) in enumerate(rois):
        # OpenCV 畫矩形是 (x, y) 到 (x+w, y+h)
        cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
        # 標上序號 (例如 N1, N2 或 R1, R2)，方便確認順序
        label = f"{label_prefix}{i+1}"
        cv2.putText(image, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

# --- 主程式開始 ---

# 1. 設定你要測試的圖片目錄
input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshot")
# 支援的副檔名
extensions = ["*.png", "*.jpg", "*.jpeg"]
image_paths = []
for ext in extensions:
    image_paths.extend(glob.glob(os.path.join(input_folder, ext)))

if not image_paths:
    print(f"在目錄 '{input_folder}' 中找不到任何圖片。")
else:
    # 建立結果輸出目錄
    output_folder = os.path.join(input_folder, "results")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"建立輸出目錄: {output_folder}")

    print(f"共找到 {len(image_paths)} 張圖片，開始進行 ROI 驗證...")

    for image_path in image_paths:
        print(f"\n正在讀取: {image_path}")
        # 2. 讀取圖片 (修正 OpenCV 無法處理中文路徑的問題)
        try:
            # 使用 np.fromfile 讀取成 byte array，再用 cv2.imdecode 解碼
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"讀取錯誤: {e}")
            img = None

        if img is None:
            print(f"錯誤：無法讀取圖片 {image_path}")
            continue

        # 為了不破壞原圖，我們複製一份來畫畫
        display_img = img.copy()
        h, w = img.shape[:2]
        print(f"圖片解析度: {w}x{h}")

        # 3. 初始化 ROI 設定計算機
        config = ROIConfig(w, h)

        # 4. 取得並繪製「一般模式 (Normal)」的框線 -> 綠色 (BGR: 0, 255, 0)
        normal_rois = config.get_rois("NORMAL")
        draw_rois(display_img, normal_rois, (0, 255, 0), "N")

        # 5. 取得並繪製「重選模式 (Repick)」的框線 -> 黃色 (BGR: 0, 255, 255) 比較顯眼
        repick_rois = config.get_rois("REPICK")
        draw_rois(display_img, repick_rois, (0, 255, 255), "R")

        # 6. 在畫面左下角加上圖例與檔名 (y 座標從底部向上算)
        padding = 30
        line_height = 30
        cv2.putText(display_img, f"File: {os.path.basename(image_path)}", (20, h - padding - line_height * 3), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_img, "Green: Normal Mode ROI", (20, h - padding - line_height * 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_img, "Yellow: Repick Mode ROI", (20, h - padding - line_height * 1), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(display_img, "Press ANY key for next, ESC to exit", (20, h - padding), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 7. 儲存標註結果 (儲存原始解析度的標註圖)
        result_name = f"verify_{os.path.basename(image_path)}"
        result_path = os.path.join(output_folder, result_name)
        try:
            # 使用 imencode 搭配 tofile 以支援中文路徑
            _, im_buf_arr = cv2.imencode(".jpg", display_img)
            im_buf_arr.tofile(result_path)
            print(f"結果已儲存至: {result_path}")
        except Exception as e:
            print(f"儲存失敗: {e}")

        # 8. 顯示結果視窗 (縮放後顯示)
        if w > 1920:
            scale_percent = 70 # 縮小到 70%
            new_width = int(display_img.shape[1] * scale_percent / 100)
            new_height = int(display_img.shape[0] * scale_percent / 100)
            display_img = cv2.resize(display_img, (new_width, new_height))

        # cv2.imshow("ROI Verification Check", display_img)
        
        # key = cv2.waitKey(0) & 0xFF
        # if key == 27:  # ESC 鍵
        #     print("使用者按下 ESC，退出程序。")
        #     break

    cv2.destroyAllWindows()
    print("\n所有圖片處理完成。")