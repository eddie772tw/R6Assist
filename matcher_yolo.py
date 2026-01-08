import os
import sys
from ultralytics import YOLO
import cv2
import numpy as np

class MLOperatorMatcher:
    def __init__(self, model_path=None):
        self.model_path = self._find_model_path(model_path)
        print(f"Loading YOLO model from: {self.model_path}")
        self.model = YOLO(self.model_path)

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
            provided_path if provided_path else "best.pt",
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

    def identify_crop(self, crop_img):
        """
        直接預測截圖是誰
        """
        if crop_img is None or crop_img.size == 0:
            print("Warning: Empty image provided to identify_crop")
            return None, 0.0

        # 確保是 BGR 格式 (如果傳入的是其他格式可能需要轉換，但這裡假設是 OpenCV 讀取的)
        # YOLO 內建會處理這部分，只要是 numpy array 即可

        try:
            # YOLO 接受 numpy array (BGR)
            # verbose=False 讓它閉嘴不要印一堆 log
            results = self.model.predict(crop_img, verbose=False, imgsz=64)
            
            if not results:
                return None, 0.0
            
            # 取得最高分的類別
            probs = results[0].probs
            
            # 確保 probs 存在
            if probs is None:
                return None, 0.0

            top1_index = probs.top1
            top1_conf = probs.top1conf.item()
            class_name = results[0].names[top1_index]
            
            # 偵錯用：如果有其他接近的結果也可以印出來
            # top5_indices = probs.top5
            # for i in top5_indices[:3]:
            #     print(f"Candidate: {results[0].names[i]} ({probs.data[i]:.4f})")

            return class_name, top1_conf, probs
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            return None, 0.0, None

# 使用範例
if __name__ == "__main__":
    try:
        matcher = MLOperatorMatcher()
        
        # 嘗試尋找真實測試圖片
        base_dir = os.path.dirname(os.path.abspath(__file__))
        test_img_path = os.path.join(base_dir, "dataset", "val", "Ash", "Ash_40.jpg")
        
        if os.path.exists(test_img_path):
            print(f"Testing with real image: {test_img_path}")
            # 使用 cv2 讀取圖片以模擬真實使用情境
            img = cv2.imread(test_img_path)
            if img is not None:
                name, conf, probs = matcher.identify_crop(img)
                print(f"Test Result (Real Image) - Expected: Ash")
                print(f"Top 1 Prediction: {name} ({conf:.2%})")
                
                if probs is not None:
                    print("\nTop 5 Candidates:")
                    for i in probs.top5:
                        p_score = probs.data[i].item()
                        p_name = matcher.model.names[i]
                        print(f"  - {p_name}: {p_score:.2%}")
            else:
                print("Failed to load test image.")
        else:
            print("No real test image found, using dummy image.")
            # 測試用: 建立一個全黑圖像來測試
            dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
            name, conf, _ = matcher.identify_crop(dummy_img)
            print(f"Test Result (Dummy Image) - Name: {name}, Conf: {conf}")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An unexpected error occurred: {e}")