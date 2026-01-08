
import sys
import os
from ultralytics import YOLO

# 將上層目錄加入 path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from matcher_yolo import MLOperatorMatcher
except ImportError:
    # Fallback if specific file structure changes, but try to locate
    pass

def main():
    print("=== R6Assist 遷移學習工具 (Transfer Learning) ===")
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    # 1. 尋找最佳模型路徑
    print("正在尋找最新模型...")
    model_path = None
    try:
        # 重用 matcher_yolo 的邏輯來找最新模型
        matcher = MLOperatorMatcher()
        model_path = matcher.model_path
        print(f"找到最新模型: {model_path}")
    except Exception as e:
        print(f"警告: 無法自動找到現有模型 ({e})")
        
    # 如果找不到，詢問使用者或使用預設
    if not model_path:
        default_path = os.path.join(base_dir, 'yolov8n-cls.pt')
        print(f"將使用基礎模型由頭開始訓練: {default_path}")
        model_path = default_path

    # 2. 設定資料集路徑
    dataset_path = os.path.join(base_dir, 'dataset')
    if not os.path.exists(dataset_path):
        print(f"錯誤: 找不到資料集資料夾 '{dataset_path}'")
        print("請確保您已生成資料集 (generate_dataset.py) 或將裁切好的圖片放入該處。")
        return

    print(f"使用模型: {model_path}")
    print(f"資料集: {dataset_path}")
    
    confirm = input("確認開始訓練? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("已取消。")
        return

    # 3. 載入模型
    model = YOLO(model_path)

    # 4. 開始訓練
    # 注意: 對於遷移學習，我們載入權重後直接再次呼叫 train
    # 這裡參數可以稍微調整，例如降低 learning rate (lr0) 以避免破壞既有特徵，
    # 但 YOLOv8 預設參數通常已足夠聰明。
    project_path = os.path.join(base_dir, 'runs', 'classify')
    
    print("開始訓練中... (Ctrl+C 可中斷)")
    
    results = model.train(
        data=dataset_path,
        epochs=10,          # 遷移訓練通常不需要太多輪，10-20 輪即可
        imgsz=64,           # 配合圖標大小
        batch=64,
        name='r6_operator_finetune', # 使用新名稱區分
        project=project_path,
        exist_ok=True,       # 允許寫入同名資料夾 (如果不希望一直產生新資料夾)
        # pretrained=True,   # YOLO 預設即為 True
        # lr0=0.001,         # 若需要微調可降低學習率
    )
    
    print("訓練完成！")
    print(f"新模型即相關數據已儲存於: {project_path}")

if __name__ == "__main__":
    main()
