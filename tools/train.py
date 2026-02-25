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

import os
import sys
from ultralytics import YOLO

def find_latest_model(base_dir):
    """
    尋找最新的訓練模型作為 Fine-tuning 的基底
    """
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
    
    return best_run_path

def main():
    # 確保可以在目前目錄找到 dataset
    # 根據之前的檔案列表，dataset 資料夾位於此 script 同層
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, 'dataset')
    
    if not os.path.exists(dataset_path):
        # 嘗試檢查是否在 data/dataset (依照原本程式碼的邏輯)
        alt_path = os.path.join(base_dir, 'data', 'dataset')
        if os.path.exists(alt_path):
            dataset_path = alt_path
        else:
            print(f"錯誤: 找不到資料集。請確認 '{os.path.join(base_dir, 'dataset')}' 存在。")
            return

    print(f"Start training with dataset at: {dataset_path}")

    # 嘗試尋找舊模型進行 Fine-tuning
    latest_model = find_latest_model(base_dir)
    if latest_model:
        print(f"🔄 偵測到先前的模型: {latest_model}")
        print("🚀 將進行 Fine-tuning (微調訓練 / 增量學習)...")
        # 這裡會自動處理類別數量的變化：
        # 如果新資料集有新角色，YOLO 會自動替換最後一層分類層，保留 Backbone 權重
        model_name = latest_model
    else:
        print("🆕 未偵測到舊模型，將使用 YOLOv8n-cls 進行全新訓練...")
        model_name = 'yolov8n-cls.pt'

    # 載入預訓練模型
    model = YOLO(model_name)

    # 開始訓練
    # epochs=20 訓練 20 輪通常就足夠收斂了
    # imgsz=64 因為我們的圖標很小，設為 64 可以飛快訓練
    results = model.train(
        data=dataset_path, 
        epochs=20, 
        imgsz=64, 
        batch=64,
        name='r6_operator_classifier',
        workers=2, # 在 Windows 上有時候太多 workers 會卡住，若有問題可設為 0 or 1
        project=os.path.join(base_dir, 'runs', 'classify') # 指定輸出路徑，避免跑到上一層
    )

if __name__ == '__main__':
    # Windows 下使用 multiprocess 需要這個保護
    main()