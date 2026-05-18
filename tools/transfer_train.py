import sys
import os
import glob
import cv2
import numpy as np
import albumentations as A
from ultralytics import YOLO

# --- 增強相關設定 ---
# 每個原始截圖要生成的變體數量
VARIANTS_PER_IMAGE = 20
VAL_RATIO = 0.2
TARGET_SIZE = (64, 64)

def get_augmentation_pipeline():
    """
    建立與 generate_dataset.py 類似的增強管線，
    但針對已經是截圖的圖片進行微調。
    """
    return A.Compose([
        A.RandomBrightnessContrast(brightness_limit=(-0.3, 0.3), contrast_limit=0.3, p=0.7),
        A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=20, val_shift_limit=10, p=0.4),
        A.ImageCompression(quality_range=(50, 100), p=0.3),
        A.GaussianBlur(blur_limit=(3, 3), p=0.2),
        A.GaussNoise(std_range=(0.01, 0.05), p=0.3),
        A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.3), p=0.2),
        A.Affine(scale=(0.9, 1.1), translate_percent=(-0.1, 0.1), rotate=(-5, 5), fit_output=False, p=0.8),
    ])

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

# 將上層目錄加入 path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from core.matcher_yolo import MLOperatorMatcher
except ImportError:
    # Fallback if specific file structure changes, but try to locate
    pass

def augment_data(base_dir):
    """
    執行資料增強與合併，將 collected_data 的截圖增強後放入 dataset/train 與 val
    """
    source_dir = os.path.join(base_dir, 'dataset', 'collected_data')
    target_dir = os.path.join(base_dir, 'dataset')
    
    if not os.path.isdir(source_dir):
        print(f"提示: 找不到來源目錄 '{source_dir}'")
        print("沒有需要增強的資料，直接進入模型訓練...")
        return

    class_folders = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    
    if not class_folders:
        print("來源目錄中沒有任何類別資料夾，跳過資料增強...")
        return
        
    print("\n=== Phase 1: 資料增強與入庫 ===")
    print(f"來源: {source_dir}")
    print(f"目標: {target_dir}")
    print(f"增強倍率: 每張圖片產生 {VARIANTS_PER_IMAGE} 張變體")
    
    confirm_aug = input("是否要將 collected_data 中的截圖進行增強併入庫? (Y/n): ").strip().lower()
    if confirm_aug == 'n':
        print("跳過資料增強階段...")
        return
        
    transform = get_augmentation_pipeline()
    total_generated = 0
    classes_processed = 0

    for class_name in class_folders:
        class_path = os.path.join(source_dir, class_name)
        
        if class_name.lower() == "unknown":
            continue
            
        print(f" 正在處理類別: {class_name}...")
        
        image_files = glob.glob(os.path.join(class_path, "*.jpg")) + \
                      glob.glob(os.path.join(class_path, "*.png"))
        
        if not image_files:
            continue

        train_dir = os.path.join(target_dir, 'train', class_name)
        val_dir = os.path.join(target_dir, 'val', class_name)
        ensure_dir(train_dir)
        ensure_dir(val_dir)
        
        for img_path in image_files:
            try:
                img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    continue
                
                if img.shape[:2] != TARGET_SIZE:
                    img = cv2.resize(img, TARGET_SIZE, interpolation=cv2.INTER_AREA)

                base_name = os.path.splitext(os.path.basename(img_path))[0]
                
                for i in range(VARIANTS_PER_IMAGE):
                    augmented = transform(image=img)['image']
                    is_val = i >= (VARIANTS_PER_IMAGE * (1 - VAL_RATIO))
                    save_folder = val_dir if is_val else train_dir
                    save_name = f"harvested_{base_name}_v{i}.jpg"
                    save_path = os.path.join(save_folder, save_name)
                    
                    try:
                        cv2.imencode('.jpg', augmented)[1].tofile(save_path)
                        total_generated += 1
                    except Exception as e:
                        pass
            except Exception as e:
                pass
        
        classes_processed += 1

    print(f"Phase 1 完成！共生成 {total_generated} 張新訓練樣本。")
    
    confirm_clear = input("是否要清空 collected_data 以避免未來重複增強相同圖片導致資料失衡或過擬合? (Y/n): ").strip().lower()
    if confirm_clear != 'n':
        for class_name in class_folders:
            if class_name.lower() == "unknown":
                continue
            class_path = os.path.join(source_dir, class_name)
            for f in glob.glob(os.path.join(class_path, "*.*")):
                try:
                    os.remove(f)
                except Exception as e:
                    pass
        print("已成功清空 collected_data 內已處理的截圖。")

def main():
    print("=== R6Assist 自動化遷移學習工具 (Auto Transfer Train) ===")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # --- Phase 1: 資料增強 ---
    augment_data(base_dir)
    
    # --- Phase 2: 模型訓練 ---
    print("\n=== Phase 2: 模型訓練 ===")
    print("正在尋找最新模型...")
    model_path = None
    try:
        matcher = MLOperatorMatcher()
        model_path = matcher.model_path
        print(f"找到最新模型: {model_path}")
    except Exception as e:
        print(f"警告: 無法自動找到現有模型 ({e})")
        
    if not model_path:
        default_path = os.path.join(base_dir, 'yolov8n-cls.pt')
        print(f"將使用基礎模型由頭開始訓練: {default_path}")
        model_path = default_path

    dataset_path = os.path.join(base_dir, 'dataset')
    if not os.path.exists(dataset_path):
        print(f"錯誤: 找不到資料集資料夾 '{dataset_path}'")
        return

    print(f"使用模型: {model_path}")
    print(f"資料集: {dataset_path}")
    
    confirm = input("確認開始進行模型訓練? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("已取消訓練。")
        return

    model = YOLO(model_path)
    project_path = os.path.join(base_dir, 'runs', 'classify')
    
    print("開始訓練中... (Ctrl+C 可中斷)")
    
    results = model.train(
        data=dataset_path,
        epochs=10,
        imgsz=64,
        batch=64,
        name='r6_operator_classifier',
        project=project_path,
        exist_ok=True,
    )
    
    print("\n訓練完成！")
    print(f"新模型即相關數據已儲存於: {project_path}")

if __name__ == "__main__":
    main()
