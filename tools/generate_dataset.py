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
import albumentations as A
import random
import sys
import io

# 設定輸出編碼以避免 Windows CP950 錯誤
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 設定 ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_folder = os.path.join(base_dir, "raw_icons")  # 你的原始圖標資料夾 (包含 atk/def)
output_folder = os.path.join(base_dir, "dataset")   # 輸出給 YOLO 訓練用的資料夾
images_per_class = 50       # 每個幹員生成多少張「變體」圖 (建議 50-100)

# --- 定義增強管線 (Augmentation Pipeline) ---
# 這就是 AI 的「特訓課程」，讓它看盡各種惡劣環境
transform = A.Compose([
    # 1. 亮度與對比度變化 (模擬死亡變暗、選中變亮)
    # 稍微縮小變暗的範圍，避免過黑丟失特徵
    A.RandomBrightnessContrast(brightness_limit=(-0.4, 0.2), contrast_limit=0.2, p=0.7),
    
    # 2. 顏色飽和度變化 (模擬不同螢幕色彩)
    A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=20, val_shift_limit=10, p=0.3),
    
    # 3. 模糊、雜訊與壓縮 (模擬解析度縮放與串流失真)
    # 新版 Albumentations API: ImageCompression 使用 quality_range (60-100)
    A.ImageCompression(quality_range=(60, 100), p=0.3),
    # 降低模糊強度，只用 3x3 kernel
    A.GaussianBlur(blur_limit=(3, 3), p=0.2),
    # 新版 Albumentations API: GaussNoise 使用 std_range (需為 0.0 ~ 1.0)
    # 之前嘗試用 (2.2, 4.5) 導致錯誤，因為這是 pixel 值
    # 轉換為 normalized: 2.2/255 ~ 0.008, 4.5/255 ~ 0.017
    # 設定為 (0.01, 0.03) 以產生輕微雜訊
    A.GaussNoise(std_range=(0.01, 0.03), p=0.3),
    # 模擬相機感光元件雜訊
    A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.3), p=0.2),
    
    # 4. 輕微縮放與旋轉 (模擬 ROI 切得不夠準的時候)
    # ShiftScaleRotate 已被棄用，改用 Affine
    # scale=(0.95, 1.05) 對應 scale_limit=0.05
    # translate_percent=(-0.05, 0.05) 對應 shift_limit=0.05
    # rotate=(-3, 3) 對應 rotate_limit=3
    A.Affine(scale=(0.95, 1.05), translate_percent=(-0.05, 0.05), rotate=(-3, 3), p=0.5),
])

def create_bg(h, w):
    """產生一個類似 R6S HUD 的深色背景"""
    # 隨機產生深灰到黑色的背景
    color = random.randint(20, 50)
    bg = np.full((h, w, 3), color, dtype=np.uint8)
    return bg

def overlay_transparent(background, overlay, x, y):
    """將帶透明度的圖標疊加到背景上"""
    bg_h, bg_w, _ = background.shape
    fg_h, fg_w, _ = overlay.shape

    if x + fg_w > bg_w or y + fg_h > bg_h:
        return background

    alpha = overlay[:, :, 3] / 255.0
    for c in range(3):
        background[y:y+fg_h, x:x+fg_w, c] = (1 - alpha) * background[y:y+fg_h, x:x+fg_w, c] + alpha * overlay[:, :, c]

    return background

# --- 主程式 ---
sides = ['atk', 'def', 'recruit']
# 準備 YOLO 分類資料夾結構: dataset/train/Ash, dataset/val/Ash
subsets = ['train', 'val'] 

print("開始生成訓練數據...")

for side in sides:
    source_path = os.path.join(input_folder, side)
    if not os.path.exists(source_path): continue
    
    files = glob.glob(os.path.join(source_path, "*.png"))
    
    for file_path in files:
        # 讀取原始圖標 (保持 Alpha 通道)
        # 使用 cv2.IMREAD_UNCHANGED 讀取透明度
        raw_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if raw_img is None: continue
        
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 為每個幹員建立資料夾
        for subset in subsets:
            save_dir = os.path.join(output_folder, subset, class_name)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

        # 開始生成變體
        # 80% 放 train, 20% 放 val
        count = 0
        for i in range(images_per_class):
            # 1. 準備背景 (64x64)
            bg = create_bg(64, 64)
            
            # 2. 縮放原始圖標以適應背景 (隨機大小)
            scale = random.uniform(0.8, 0.95)
            new_h, new_w = int(64*scale), int(64*scale)
            resized_icon = cv2.resize(raw_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # 3. 計算居中位置 (隨機微調)
            offset_x = (64 - new_w) // 2 + random.randint(-2, 2)
            offset_y = (64 - new_h) // 2 + random.randint(-2, 2)
            
            # 4. 疊加
            final_img = overlay_transparent(bg, resized_icon, offset_x, offset_y)
            
            # 5. 應用增強 (變暗、變色、雜訊)
            augmented = transform(image=final_img)['image']
            
            # 6. 存檔
            subset = 'train' if i < (images_per_class * 0.8) else 'val'
            save_name = f"{class_name}_{i}.jpg"
            save_path = os.path.join(output_folder, subset, class_name, save_name)
            
            # cv2.imwrite(save_path, augmented) # cv2.imwrite 不支援中文路徑
            try:
                cv2.imencode('.jpg', augmented)[1].tofile(save_path)
            except Exception as e:
                print(f"Error saving {save_path}: {e}")
            count += 1
            
        print(f"已生成 {count} 張訓練樣本: {class_name}")

print("數據生成完畢！請查看 dataset 資料夾。")