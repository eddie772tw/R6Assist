[English](README.md) | [繁體中文](README_zh-tw.md)

# R6Assist - Rainbow Six Siege Tactical Assistant

**R6Assist** is an AI tactical assistant designed specifically for *Rainbow Six Siege*. It uses computer vision technology to monitor the operator selection screen in real-time, recognizes the operators chosen by your teammates, and recommends the best picks based on tactical logic to help you build the perfect team composition.

## ✨ Key Features

*   **Real-Time Monitoring**: Automatically detects the game selection screen without manual input.
*   **AI Vision Recognition**: Uses the YOLOv8 deep learning model to accurately identify all operator icons.
*   **Web-Based Tactical Dashboard (Web UI)**: A brand-new decoupled architecture providing a high-quality, graphical recommendation interface with real-time animations via the browser.
*   **High-Performance Screen Capture**: Supports `dxcam` (DirectX high-speed capture) and `mss`, ensuring low latency and low resource consumption.
*   **Tactical Recommendation Engine**:
    *   Automatically determines the attack/defense phase.
    *   Analyzes the team's missing roles (e.g., Hard Breach, Intel, Healing, etc.).
    *   Provides real-time scoring and operator swap recommendations.

## 🛠️ Installation

### System Requirements
*   Windows 10/11
*   Python 3.8 or above
*   Node.js (for installing and running the Web UI frontend)
*   NVIDIA Graphics Card recommended for optimal YOLO inference performance (CUDA installation required)

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/eddie772tw/R6Assist.git
    cd R6Assist
    ```

2.  **Install Dependencies**
    ```bash
    # Install Python backend dependencies (ensure flask, flask-socketio, eventlet, customtkinter are included)
    pip install -r requirements.txt
    
    # Install Web UI frontend dependencies
    cd r6assist-webui
    npm install
    cd ..
    ```

## 🚀 Usage

### 1. Train or Prepare the Model (Important)
This project requires a trained YOLOv8 classification model to function.
*   Place the trained model file in the default path (usually automatically searched at `runs/classify/train/weights/best.pt`).
*   If you don't have a model yet, refer to `generate_dataset.py` and `train.py` to collect data and train it yourself.

### 2. Start Real-Time Monitoring (Recommended: Use the GUI Launcher)

The easiest way to start the system is by double-clicking the **`R6Assist.exe`** executable file. This will open the graphical launcher where you can manage the frontend dashboard, backend API, and training tools entirely within a single window, and view all system logs without manually switching terminals.

> *Alternatively, for developers, you can run the python script directly:*
```bash
python launcher.py
```

**(Or start it manually:)**

**Step 1: Start the API Backend**
```bash
python api.py
```

**Step 2: Start the Web UI Frontend**
(Open a new terminal)
```bash
cd r6assist-webui
npm run dev
```

Open your browser and navigate to the local URL provided in the terminal (e.g., `http://localhost:5173/` or `http://localhost:5174/`). Once the game enters the operator selection screen, the webpage will automatically display the phase, team gaps, and graphical scoring recommendations in real-time.

### 3. Use the Traditional Command-Line Interface (CLI)

If you prefer viewing results in the command line (without opening a browser), you can run:

```bash
python monitor.py
```

The program will:
1.  Automatically capture the screen.
2.  Display the current composition analysis and recommendations in the Terminal.
3.  Press `Ctrl+C` to stop monitoring.

### 4. Single Image Testing
If you want to test the recognition performance on static images:

```bash
python core/assistant.py
```
(Ensure there are test images inside the `screenshot/` folder)

## 📁 Project Structure

*   `launcher.py`: Global graphical launcher for unified management of the Dashboard, CLI monitoring, and all development tools.
*   `api.py`: Backend API responsible for screen analysis and real-time broadcasting via WebSockets.
*   `monitor.py`: Main CLI script for text-based real-time monitoring and interaction.
*   `r6assist-webui/`: Web frontend project (React + Vite) providing a graphical real-time tactical dashboard.
*   `core/`:
    *   `assistant.py`: Core logic encapsulation and single-image testing entry point.
    *   `analyzer.py`: Vision processing module for image preprocessing and inference.
    *   `logic.py`: Tactical logic module for calculating team scores and recommendations.
    *   `matcher_yolo.py`: YOLO model loading and prediction implementation.
    *   `collector.py`: Module for custom screen collection and data storage.
*   `tools/`: Development auxiliary tools including training, dataset generation, and raw icon scraping (`generate_dataset.py`, `train.py`, `get_op_stat.py`, etc.).
*   `data/op_stats.json`: Operator database defining the faction, role, and scoring weight of each operator.

## ⚠️ Disclaimer
*   This tool solely uses computer vision (OCR/Object Detection) and **does not** inject code into the game's memory. Theoretically, it does not violate BattlEye rules, but use it at your own risk.
*   It is recommended to run the game in "Borderless Window" mode to ensure screen capture tools function properly.

## License
GPLv3 License
