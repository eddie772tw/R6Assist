import time
import os
import cv2
import numpy as np
import sys
import threading
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

try:
    import dxcam
    HAS_DXCAM = True
except ImportError:
    HAS_DXCAM = False
    import mss

# Import core logic from R6Assist
from core.assistant import R6TacticalAssistant
from core.collector import DataCollector

from flask_cors import CORS
import json

app = Flask(__name__)
# Enable CORS for the Vite dev server (usually runs on port 5173 or localhost)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load configuration
API_PORT = 5000
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        API_PORT = config_data.get('api_port', 5000)
except Exception as e:
    print(f"⚠️ Could not load config.json (using default port 5000): {e}")

# Create a global state to keep track of the monitoring thread
monitoring_thread = None
is_monitoring = False
latest_scan_data = None # Store (team_names, confidences, crop_images)

# Initialize Assistant
try:
    assistant = R6TacticalAssistant(None) # Auto find model
    collector = DataCollector() # Initialize DataCollector for archiving
    print("✅ R6Assist Core Engine Loaded")
except Exception as e:
    print(f"❌ Failed to load R6Assist Core: {e}")
    sys.exit(1)


def monitoring_loop():
    """Background task to monitor screen and emit WebSocket events"""
    global is_monitoring, latest_scan_data
    target_fps = 2
    frame_time = 1.0 / target_fps
    
    use_dxcam = False
    camera = None
    sct = None
    monitor_area = None
    
    # Initialize Screen Capture
    if HAS_DXCAM:
        try:
            camera = dxcam.create(output_idx=0, output_color="BGR")
            if camera and hasattr(camera, 'is_capturing'):
                use_dxcam = True
                print("🚀 DXCam initialized for API")
            else:
                print("⚠️ DXCam created but invalid, falling back to MSS")
        except Exception as e:
            print(f"⚠️ DXCam init failed: {e}")
            
    if not use_dxcam:
        import mss
        sct = mss.mss()
        monitor_area = sct.monitors[1]
        print("ℹ️ MSS initialized for API")

    last_frame = None
    last_update_payload = None
    
    while is_monitoring:
        start_time = time.time()
        
        # 1. Grab Frame
        img = None
        if use_dxcam:
            img = camera.grab()
        else:
            screenshot = sct.grab(monitor_area)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
        if img is None:
            time.sleep(0.1)
            continue
            
        # 2. Check for frame change
        frame_changed = True
        if last_frame is not None:
            small_curr = cv2.resize(img, (64, 64))
            small_last = cv2.resize(last_frame, (64, 64))
            diff = cv2.absdiff(small_curr, small_last)
            if np.count_nonzero(diff) < 100:
                frame_changed = False
                
        # 3. Analyze Frame & Build Payload
        if frame_changed:
            last_frame = img.copy()
            team_names, confidences, crop_images = assistant.analyzer.analyze_screenshot(img)
            
            # Cache the latest scan data for manual archiving
            latest_scan_data = (team_names, confidences, crop_images)
            
            # Use valid count to decide if we are in character selection
            valid_count = sum(1 for n in team_names if n != "Unknown")
            
            if valid_count > 0:
                # Same logic as monitor.py
                user_pick = team_names[0]
                teammates = team_names[1:][::-1]
                
                side = assistant.determine_side(team_names)
                
                if side:
                    missing_roles = assistant.advisor.get_missing_roles(team_names, side)
                    result = assistant.advisor.evaluate_and_recommend(user_pick, teammates, side=side)
                    
                    payload = {
                        "status": "active",
                        "side": side,
                        "user_pick": user_pick,
                        "user_score": result['current_pick']['score'],
                        "teammates": teammates,
                        "missing_roles": missing_roles,
                        "recommendations": result['recommendations'][:5]
                    }
                else:
                    payload = {"status": "waiting", "message": "Analyzing team composition..."}
            else:
                payload = {"status": "waiting", "message": "Waiting for character selection..."}
                
            # Only emit if payload changed to save bandwidth
            if str(payload) != str(last_update_payload):
                socketio.emit('gameState', payload)
                last_update_payload = payload
                
        # Sleep to maintain FPS
        elapsed = time.time() - start_time
        if frame_time > elapsed:
            socketio.sleep(frame_time - elapsed)
        else:
            socketio.sleep(0.01) # Yield execution
            
    # Cleanup capture devices
    if use_dxcam and camera:
        try:
            if hasattr(camera, 'is_capturing'):
                camera.stop()
        except AttributeError:
            pass # DXCam internal bug in some versions
        del camera
    elif sct:
        sct.close()

@app.route('/')
def index():
    return jsonify({"status": "R6Assist API is running", "monitoring": is_monitoring})

@socketio.on('connect')
def test_connect():
    print('Web UI Client connected')
    socketio.emit('connection_established', {'data': 'Connected to R6Assist Backend'})
    
    # Send initial status
    global is_monitoring
    if not is_monitoring:
        socketio.emit('gameState', {"status": "idle", "message": "Monitoring is currently paused."})

@socketio.on('disconnect')
def test_disconnect():
    print('Web UI Client disconnected')

@socketio.on('start_monitoring')
def start_mon():
    global is_monitoring, monitoring_thread
    if not is_monitoring:
        is_monitoring = True
        monitoring_thread = socketio.start_background_task(monitoring_loop)
        print("Started monitoring loop")
        socketio.emit('gameState', {"status": "starting", "message": "Initializing capture engine..."})

@socketio.on('stop_monitoring')
def stop_mon():
    global is_monitoring
    is_monitoring = False
    print("Stopped monitoring loop")
    socketio.emit('gameState', {"status": "idle", "message": "Monitoring stopped."})

@socketio.on('archive_capture')
def archive_capture():
    """Manually archive the latest scan data"""
    global latest_scan_data
    if latest_scan_data:
        team_names, confidences, crop_images = latest_scan_data
        collector.process_batch(crop_images, team_names, confidences)
        print(f"✅ Manual archive complete: {len(team_names)} samples saved.")
        socketio.emit('archive_success', {"message": "Data archived successfully!"})
    else:
        print("⚠️ No data to archive.")
        socketio.emit('archive_error', {"message": "No active scan data to archive."})

if __name__ == '__main__':
    print(f"Starting Flask-SocketIO Server on port {API_PORT}...")
    socketio.run(app, host='0.0.0.0', port=API_PORT, debug=False, log_output=False)

