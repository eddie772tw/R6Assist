import time
import re
import os
import cv2
import numpy as np
import sys
import threading
import base64
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

# Load configuration
API_PORT = 5000
WEB_PORT = 5173
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        API_PORT = config_data.get('api_port', 5000)
        WEB_PORT = config_data.get('web_port', 5173)
except Exception as e:
    print(f"⚠️ Could not load config.json (using defaults): {e}")

app = Flask(__name__)

# 🛡️ Sentinel: Allow CORS for local network devices to enable cross-device experience (e.g. tablet/phone on same Wi-Fi)
# Regex matches localhost, 127.0.0.1, and private IPv4 address ranges (10.x.x.x, 172.16.x.x-172.31.x.x, 192.168.x.x)
cors_regex = re.compile(r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+)(:\d+)?$")

CORS(app, origins=cors_regex)
socketio = SocketIO(app, cors_allowed_origins='*')

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
    small_last_frame = None
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
        small_curr = None
        if last_frame is not None:
            small_curr = cv2.resize(img, (64, 64))
            small_last = cv2.resize(last_frame, (64, 64))
            diff = cv2.absdiff(small_curr, small_last)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            _, diff_thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
            if cv2.countNonZero(diff_thresh) < 100:
                frame_changed = False
                
        # 3. Analyze Frame & Build Payload
        if frame_changed:
            last_frame = img.copy()
            if small_curr is None:
                small_curr = cv2.resize(img, (64, 64))
            small_last_frame = small_curr.copy()
            team_names, confidences, crop_images = assistant.analyzer.analyze_screenshot(img)
            
            # Cache the latest scan data for manual archiving
            latest_scan_data = (team_names, confidences, crop_images)
            
            # --- Emit live frame to WebUI ---
            try:
                # Find the bounding box of all ROIs
                min_x = min(r[0] for r in used_rois)
                min_y = min(r[1] for r in used_rois)
                max_x = max(r[0] + r[2] for r in used_rois)
                max_y = max(r[1] + r[3] for r in used_rois)

                # Add some padding (10% of width/height)
                pad_w = int((max_x - min_x) * 0.1)
                pad_h = int((max_y - min_y) * 2.5) # More vertical padding for context
                
                h, w = img.shape[:2]
                y1 = max(0, min_y - int(pad_h * 0.5))
                y2 = min(h, max_y + int(pad_h * 0.5))
                x1 = max(0, min_x - pad_w)
                x2 = min(w, max_x + pad_w)
                
                # Crop
                small_frame = img[y1:y2, x1:x2].copy()
                
                # Draw boxes on the crop
                for i, (rx, ry, rw, rh) in enumerate(used_rois):
                    # Adjust coordinates for the crop
                    bx = rx - x1
                    by = ry - y1
                    
                    # Choose color based on recognition status
                    color = (0, 255, 0) if team_names[i] != "Unknown" else (0, 165, 255) # Green vs Orange
                    cv2.rectangle(small_frame, (bx, by), (bx + rw, by + rh), color, 2)
                    
                    # Optional: Add label
                    if team_names[i] != "Unknown":
                        cv2.putText(small_frame, team_names[i], (bx, by - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

                # Resize for performance (width 640px)
                height, width = small_frame.shape[:2]
                new_width = 640
                new_height = int(height * (new_width / width))
                small_frame = cv2.resize(small_frame, (new_width, new_height))
                
                # Encode as JPEG
                _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('live_frame', {'image': f'data:image/jpeg;base64,{jpg_as_text}'})
            except Exception as e:
                print(f"⚠️ Failed to emit live frame: {e}")

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
    # 🛡️ Sentinel: Bind to 0.0.0.0 to allow cross-device access on the local network
    print(f"Starting Flask-SocketIO Server on 0.0.0.0:{API_PORT} (Local Network Access Enabled)...")
    socketio.run(app, host='0.0.0.0', port=API_PORT, debug=False, log_output=False)

