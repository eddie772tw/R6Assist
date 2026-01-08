
import sys
import os
import cv2
import numpy as np
import time
import glob

# 將上層目錄加入 path 以便匯入專案模組
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from verify_roi import ROIConfig
    from matcher_yolo import MLOperatorMatcher
except ImportError as e:
    print(f"Import Error: {e}")
    print("請確保此腳本位於 R6Assist/training_tools/ 目錄下，且專案結構完整。")
    sys.exit(1)

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    print("=== R6Assist 自動截圖裁切與標註工具 ===")
    
    # 1. 初始化路徑
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    screenshot_dir = os.path.join(base_dir, 'screenshot')
    output_base_dir = os.path.join(base_dir, 'dataset_harvested') # 輸出到獨立資料夾以供人工驗證
    
    print(f"截圖來源: {screenshot_dir}")
    print(f"輸出目錄: {output_base_dir}")
    print("正在載入模型以進行自動標註...")
    
    # 2. 載入模型
    try:
        matcher = MLOperatorMatcher()
    except Exception as e:
        print(f"無法載入模型，將無法進行自動分類: {e}")
        print("請先執行 train.py 訓練初始模型，或確保有 weights/best.pt")
        return

    # 3. 搜尋圖片
    exts = ['*.jpg', '*.png', '*.jpeg']
    image_paths = []
    for ext in exts:
        image_paths.extend(glob.glob(os.path.join(screenshot_dir, ext)))
    
    if not image_paths:
        print("找不到截圖！請將遊戲截圖放入 R6Assist/screenshot 資料夾")
        return

    print(f"找到 {len(image_paths)} 張截圖，開始處理...")
    
    count_processed = 0
    count_cropped = 0
    
    for img_path in image_paths:
        print(f"處理: {os.path.basename(img_path)}...")
        
        # 讀取圖片 (處理中文路徑)
        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("  無法讀取，跳過。")
            continue
            
        h, w = img.shape[:2]
        
        # 取得 ROI
        roi_config = ROIConfig(w, h)
        # 我們假設截圖主要包含一般模式 (Normal) 的圖標
        # 若需要重選模式 (Repick) 可再擴充
        rois = roi_config.get_rois("NORMAL")
        
        for i, (rx, ry, rw, rh) in enumerate(rois):
            # 邊界檢查
            if rx < 0 or ry < 0 or rx+rw > w or ry+rh > h:
                continue
                
            crop = img[ry:ry+rh, rx:rx+rw]
            
            # 使用模型預測
            name, conf, _ = matcher.identify_crop(crop)
            
            if name and conf > 0.5: # 信心度門檻
                save_label = name
            else:
                save_label = "unknown"
                
            # 建立分類資料夾
            # 我們將其存為 dataset_harvested/name/filename_roi_index.jpg
            save_dir = os.path.join(output_base_dir, save_label)
            ensure_dir(save_dir)
            
            filename = os.path.splitext(os.path.basename(img_path))[0]
            save_name = f"{filename}_roi{i}.jpg"
            save_path = os.path.join(save_dir, save_name)
            
            # 存檔
            try:
                cv2.imencode('.jpg', crop)[1].tofile(save_path)
                count_cropped += 1
            except Exception as e:
                print(f"  存檔失敗: {e}")
                
        count_processed += 1
        
    print("="*30)
    print(f"處理完成！")
    print(f"共掃描 {count_processed} 張截圖")
    print(f"共裁切並分類 {count_cropped} 個圖標")
    print(f"結果已儲存至: {output_base_dir}")
    print("重要：請務必人工檢查這些分類是否正確，再將其移動到 dataset/train 對應資料夾中進行遷移訓練。")

if __name__ == "__main__":
    main()
