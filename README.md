# R6Assist - Rainbow Six Siege Tactical Assistant

**R6Assist** 是一款專為《虹彩六號：圍攻行動》(Rainbow Six Siege) 設計的 AI 戰術助手。它利用電腦視覺技術即時監控選角畫面，辨識隊友選擇的幹員，並根據戰術邏輯推薦最佳的補位人選，協助您打造完美的團隊陣容。

## ✨ 主要功能

*   **即時畫面監控**：自動偵測遊戲選角畫面，無需手動輸入。
*   **AI 視覺辨識**：使用 YOLOv8 深度學習模型，精準辨識所有幹員圖標。
*   **高效能截圖**：支援 `dxcam` (DirectX 高速截圖) 與 `mss`，確保低延遲與低資源佔用。
*   **戰術建議引擎**：
    *   自動判斷攻/守方陣營。
    *   分析隊伍現有的職能缺口 (如：缺乏切牆、情報、補血等)。
    *   提供即時的評分與換角建議。

## 🛠️ 安裝說明

### 系統需求
*   Windows 10/11
*   Python 3.8 或以上版本
*   建議使用 NVIDIA 顯示卡以獲得最佳 YOLO 推論效能 (需安裝 CUDA)

### 安裝步驟

1.  **複製專案**
    ```bash
    git clone https://github.com/yourusername/R6Assist.git
    cd R6Assist
    ```

2.  **安裝依賴套件**
    ```bash
    pip install -r requirements.txt
    ```

## 🚀 使用方法

### 1. 訓練或準備模型 (重要)
本專案需要訓練好的 YOLOv8 分類模型才能運作。
*   將訓練好的模型檔案放置於預設路徑 (通常會自動搜尋 `runs/classify/train/weights/best.pt`)。
*   如果您還沒有模型，請參考 `generate_dataset.py` 與 `train.py` 自行收集資料並訓練。

### 2. 啟動即時監控
在遊戲運行並進入選角畫面時，執行以下指令：

```bash
python monitor.py
```

程式將會：
1.  自動抓取螢幕畫面。
2.  在終端機 (Terminal) 顯示目前的陣容分析與建議。
3.  按 `Ctrl+C` 可停止監控。

### 3. 單張圖片測試
如果您想測試靜態圖片的辨識效果：

```bash
python main.py
```
(請確保 `screenshot/` 資料夾內有測試圖片)

## 📁 專案結構

*   `monitor.py`: 主程式，負責即時監控與互動介面。
*   `main.py`: 核心邏輯封裝與單圖測試。
*   `analyzer.py`: 視覺處理模組，負責影像前處理與 YOLO 推論。
*   `logic.py`: 戰術邏輯模組，負責計算隊伍分數與推薦。
*   `matcher_yolo.py`: YOLO 模型載入與預測實作。
*   `op_stats.json`: 幹員資料庫，定義了每位幹員的陣營、職能與評分權重。

## ⚠️ 注意事項
*   本工具僅使用視覺辨識 (OCR/Object Detection)，**不會**注入程式碼到遊戲記憶體，理論上不違反 BattlEye 規範，但使用風險請自行承擔。
*   建議在「無邊框視窗 (Borderless Window)」模式下運行遊戲，以確保截圖工具正常運作。

## 授權
MIT License
