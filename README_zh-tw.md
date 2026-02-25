[English](README.md) | [繁體中文](README_zh-tw.md)

# R6Assist - Rainbow Six Siege Tactical Assistant

**R6Assist** 是一款專為《虹彩六號：圍攻行動》(Rainbow Six Siege) 設計的 AI 戰術助手。它利用電腦視覺技術即時監控選角畫面，辨識隊友選擇的幹員，並根據戰術邏輯推薦最佳的補位人選，協助您打造完美的團隊陣容。

## ✨ 主要功能

*   **即時畫面監控**：自動偵測遊戲選角畫面，無需手動輸入。
*   **AI 視覺辨識**：使用 YOLOv8 深度學習模型，精準辨識所有幹員圖標。
*   **網頁版戰術看板 (Web UI)**：全新的前後端分離設計，透過瀏覽器提供高品質、具備即時動畫的圖形化建議介面。
*   **高效能截圖**：支援 `dxcam` (DirectX 高速截圖) 與 `mss`，確保低延遲與低資源佔用。
*   **戰術建議引擎**：
    *   自動判斷攻/守方陣營。
    *   分析隊伍現有的職能缺口 (如：缺乏切牆、情報、補血等)。
    *   提供即時的評分與換角建議。

## 🛠️ 安裝說明

### 系統需求
*   Windows 10/11
*   Python 3.8 或以上版本
*   Node.js (用於安裝並執行 Web UI 前端)
*   建議使用 NVIDIA 顯示卡以獲得最佳 YOLO 推論效能 (需安裝 CUDA)

### 安裝步驟

1.  **複製專案**
    ```bash
    git clone https://github.com/eddie772tw/R6Assist.git
    cd R6Assist
    ```

2.  **安裝依賴套件**
    ```bash
    # 安裝 Python 後端依賴 (確保包含 flask, flask-socketio, eventlet, customtkinter 等)
    pip install -r requirements.txt
    
    # 安裝 Web UI 前端依賴
    cd r6assist-webui
    npm install
    cd ..
    ```

## 🚀 使用方法

### 1. 訓練或準備模型 (重要)
本專案需要訓練好的 YOLOv8 分類模型才能運作。
*   將訓練好的模型檔案放置於預設路徑 (通常會自動搜尋 `runs/classify/train/weights/best.pt`)。
*   如果您還沒有模型，請參考 `generate_dataset.py` 與 `train.py` 自行收集資料並訓練。

### 2. 啟動即時監控 (推薦：使用圖形化 Launcher 啟動器)

最簡單的上手方式是直接雙擊 **`R6Assist.exe`** 執行檔。它會開啟全能的圖形化啟動器，您可以在同一個視窗內管理前端看板、後端 API 以及訓練工具，並在同一個視窗內查看所有系統日誌，無需手動切換終端機。

> *或者，開發者也可以選擇直接透過 Python 手動啟動：*
```bash
python launcher.py
```

**(或者您也可以手動啟動：)**

**步驟一：啟動 API 後端**
```bash
python api.py
```

**步驟二：啟動 Web UI 前端**
(另開一個終端機)
```bash
cd r6assist-webui
npm run dev
```

開啟瀏覽器並前往終端機提示的本地網址 (例如 `http://localhost:5173/` 或 `http://localhost:5174/`)，在遊戲進入選角畫面後，網頁將自動即時顯示陣營、隊伍缺口與圖形化評分建議。

### 3. 使用傳統終端機介面 (CLI)

如果您偏好在命令列中檢視結果（不開啟瀏覽器），可直接執行：

```bash
python monitor.py
```

程式將會：
1.  自動抓取螢幕畫面。
2.  在終端機 (Terminal) 顯示目前的陣容分析與建議。
3.  按 `Ctrl+C` 可停止監控。

### 4. 單張圖片測試
如果您想測試靜態圖片的辨識效果：

```bash
python core/assistant.py
```
(請確保 `screenshot/` 資料夾內有測試圖片)

## 📁 專案結構

*   `launcher.py`: 全局圖形化啟動器，統一管理 Dashboard、CLI 監控與所有開發工具。
*   `api.py`: Backend 後端 API，負責畫面分析並透過 WebSocket 即時推播。
*   `monitor.py`: CLI 終端機介面主程式，負責純文字即時監控與互動介面。
*   `r6assist-webui/`: 前端網頁專案 (React + Vite)，提供圖形化即時戰術看板。
*   `core/`:
    *   `assistant.py`: 核心邏輯封裝與單圖測試入口。
    *   `analyzer.py`: 視覺處理模組，負責影像前處理與推論。
    *   `logic.py`: 戰術邏輯模組，負責計算隊伍分數與推薦。
    *   `matcher_yolo.py`: YOLO 模型載入與預測實作。
    *   `collector.py`: 自選畫面搜集與資料儲存模組。
*   `tools/`: 包含訓練、資料集生成、原始圖說抓取等開發輔助工具 (`generate_dataset.py`, `train.py`, `get_op_stat.py` 等)。
*   `data/op_stats.json`: 幹員資料庫，定義了每位幹員的陣營、職能與評分權重。

## ⚠️ 注意事項
*   本工具僅使用視覺辨識 (OCR/Object Detection)，**不會**注入程式碼到遊戲記憶體，理論上不違反 BattlEye 規範，但使用風險請自行承擔。
*   建議在「無邊框視窗 (Borderless Window)」模式下運行遊戲，以確保截圖工具正常運作。

## 授權
GPLv3 License
