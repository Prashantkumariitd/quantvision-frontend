import json
import os
BACKEND_URL = "http://127.0.0.1:8000"
CAPTURE_INTERVAL = 1.0  # seconds
CALIBRATION_PATH = "vision_service/calibration.json"

if os.path.exists(CALIBRATION_PATH):
    with open(CALIBRATION_PATH) as f:
        CAPTURE_REGION = json.load(f)
else:
    CAPTURE_REGION = {
        "left": 200,
        "top": 100,
        "width": 1200,
        "height": 700
    }
