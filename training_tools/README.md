# R6Assist 遷移學習工具組 (Training Tools)

這兩個腳本旨在協助您從真實遊戲截圖中建立資料集，並微調 (Fine-tune) 模型以提高辨識準確度。

## 1. 截圖裁切與自動標註 (`crop_and_label.py`)

此工具會掃描 `R6Assist/screenshot/` 資料夾中的所有截圖，根據一般模式 (Normal Mode) 的 ROI 自動裁切圖標，並使用目前的 AI 模型進行初步分類。

**使用步驟:**
1.  將遊戲截圖 (1080p, 1440p 等) 放入 `R6Assist/screenshot` 資料夾。
2.  執行指令:
    ```bash
    python crop_and_label.py
    ```
3.  程式會將裁切下來的圖標存放在 `R6Assist/dataset_harvested/`，並依照預測的幹員名稱分類。
4.  **重要**: 請人工檢查 `dataset_harvested` 中的圖片。
    *   如果有分類錯誤的圖片，請將其移動到正確的資料夾。
    *   如果有 "unknown" 的圖片，請將其移動到正確的幹員資料夾。
5.  檢查完畢後，將 `dataset_harvested` 中的資料夾 **合併** 到 `dataset/train` 或 `dataset/val` 中。

## 2. 資料增強與合併 (`augment_and_merge.py`)

此工具將 `dataset_harvested` 中經過您人工驗證的真實圖片，依照 `generate_dataset.py` 的邏輯進行「量產」(Data Augmentation)，並合併至主資料集 `dataset/` 中。

**使用步驟:**
1.  確保 `dataset_harvested` 中的圖片都已分類正確 (不可有 `unknown` 資料夾或錯誤分類)。
2.  執行指令:
    ```bash
    python augment_and_merge.py
    ```
3.  程式會讀取每張真實截圖，生成多張 (預設 20 張) 經過亮度、雜訊、位移變換的變體。
4.  這些變體會被自動分配到 `dataset/train` 和 `dataset/val` 中。

## 3. 遷移訓練 (`transfer_train.py`)

此工具會載入最新的模型 (若無則使用預設)，並使用您在 `dataset/` 中擴充的新資料進行訓練。

**使用步驟:**
1.  確保 `dataset/` 資料夾中已經包含您想訓練的新圖片。
2.  執行指令:
    ```bash
    python transfer_train.py
    ```
3.  程式會自動載入效果最好的模型權重 (`best.pt`) 並開始訓練。
4.  訓練完成後，新模型會儲存在 `R6Assist/runs/classify/r6_operator_finetune/` 中。

## 注意事項
*   請確保安裝了 `ultralytics`, `opencv-python`, `numpy` 等套件。
*   預設 ROI 針對 16:9 螢幕設計，若截圖比例不同可能需要調整 `verify_roi.py` 中的參數。
