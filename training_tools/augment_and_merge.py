
import cv2
import numpy as np
import os
import glob
import albumentations as A
import random
import sys
import shutil

# 將上層目錄加入 path 以便讀取專案設定 (若有需要)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 設定 ---
# 每個原始截圖要生成的變體數量 (Mass production multiplier)
# 因為真實數據很珍貴，我們可以多生成一些變體來增加數據量
VARIANTS_PER_IMAGE = 20 

# 驗證集比例 (20% 用於驗證)
VAL_RATIO = 0.2

# 圖片目標大小
TARGET_SIZE = (64, 64)

def get_augmentation_pipeline():
    """
    建立與 generate_dataset.py 類似的增強管線，
    但針對已經是截圖的圖片進行微調。
    """
    return A.Compose([
        # 1. 亮度與對比度變化
        A.RandomBrightnessContrast(brightness_limit=(-0.3, 0.3), contrast_limit=0.3, p=0.7),
        
        # 2. 顏色飽和度微調
        A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=20, val_shift_limit=10, p=0.4),
        
        # 3. 畫質模擬 (壓縮、模糊、雜訊)
        A.ImageCompression(quality_range=(50, 100), p=0.3),
        A.GaussianBlur(blur_limit=(3, 3), p=0.2),
        A.GaussNoise(std_range=(0.01, 0.05), p=0.3),
        A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.3), p=0.2),
        
        # 4. 幾何變換 (模擬裁切誤差)
        # 這裡非常重要，因為自動裁切可能不會每次都完美居中
        A.Affine(scale=(0.9, 1.1), translate_percent=(-0.1, 0.1), rotate=(-5, 5), fit_output=False, p=0.8),
    ])

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    print("=== R6Assist 資料增強與合併工具 ===")
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    source_dir = os.path.join(base_dir, 'dataset\collected_data')
    target_dir = os.path.join(base_dir, 'dataset')
    
    if not os.path.exists(source_dir):
        print(f"錯誤: 找不到來源目錄 '{source_dir}'")
        print("請先執行 crop_and_label.py 並人工驗證分類結果。")
        return

    # 初始化增強管線
    transform = get_augmentation_pipeline()

    print(f"來源: {source_dir}")
    print(f"目標: {target_dir}")
    print(f"增強倍率: 每張原始圖產生 {VARIANTS_PER_IMAGE} 張變體")
    
    confirm = input("確認開始進行增強併入庫? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("已取消。")
        return

    # 統計
    total_generated = 0
    classes_processed = 0

    # 遍歷 dataset_harvested 下的所有類別資料夾
    # source_dir/Ash, source_dir/Sledge, ...
    class_folders = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    
    if not class_folders:
        print("來源目錄中沒有任何類別資料夾！")
        return

    for class_name in class_folders:
        class_path = os.path.join(source_dir, class_name)
        
        # 略過 unknown 資料夾，不應該將未知圖片加入訓練集
        if class_name.lower() == "unknown":
            print(f"略過 'unknown' 資料夾...")
            continue
            
        print(f"正在處理類別: {class_name}...")
        
        # 讀取該類別下所有圖片
        image_files = glob.glob(os.path.join(class_path, "*.jpg")) + \
                      glob.glob(os.path.join(class_path, "*.png"))
        
        if not image_files:
            continue

        # 確保目標資料夾存在
        train_dir = os.path.join(target_dir, 'train', class_name)
        val_dir = os.path.join(target_dir, 'val', class_name)
        ensure_dir(train_dir)
        ensure_dir(val_dir)
        
        for img_path in image_files:
            # 讀取原始圖片
            try:
                # 處理中文路徑
                img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    print(f"  無法讀取: {os.path.basename(img_path)}")
                    continue
                
                # 確保圖片大小一致 (先 Resize 到略大於 64，留給 Affine 空間，或者直接 Resize 到 64)
                # 這裡直接 Resize 到 64x64，因為 Albumentations 的 Affine 會處理
                if img.shape[:2] != TARGET_SIZE:
                    img = cv2.resize(img, TARGET_SIZE, interpolation=cv2.INTER_AREA)

                # 取得檔名作為 ID 生成的基礎
                base_name = os.path.splitext(os.path.basename(img_path))[0]
                
                # 生成變體
                for i in range(VARIANTS_PER_IMAGE):
                    # 應用增強
                    augmented = transform(image=img)['image']
                    
                    # 決定是 train 還是 val
                    # 我們希望同一張原始圖的所有變體盡量在同一邊，避免 Data Leakage
                    # 但這裡我們採取簡單隨機：每張變體獨立隨機分配
                    # 或者：前 80% 變體給 train，後 20% 給 val (這樣更穩定)
                    is_val = i >= (VARIANTS_PER_IMAGE * (1 - VAL_RATIO))
                    
                    save_folder = val_dir if is_val else train_dir
                    save_name = f"harvested_{base_name}_v{i}.jpg"
                    save_path = os.path.join(save_folder, save_name)
                    
                    try:
                        cv2.imencode('.jpg', augmented)[1].tofile(save_path)
                        total_generated += 1
                    except Exception as e:
                        print(f"  存檔失敗: {e}")

            except Exception as e:
                print(f"  處理圖片發生錯誤 {img_path}: {e}")
        
        classes_processed += 1

    print("="*30)
    print(f"處理完成！")
    print(f"共處理 {classes_processed} 個類別")
    print(f"共生成 {total_generated} 張新訓練樣本")
    print(f"現在您可以執行 transfer_train.py 來訓練模型了。")

if __name__ == "__main__":
    main()
