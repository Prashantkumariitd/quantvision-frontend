import cv2
import easyocr
import json
import numpy as np
import re
from datetime import datetime, timezone

# Initialize OCR once
reader = easyocr.Reader(['en'], gpu=False)


def safe_crop(frame, x1, y1, x2, y2):
    h, w = frame.shape[:2]
    x1 = max(0, min(w, int(x1)))
    x2 = max(0, min(w, int(x2)))
    y1 = max(0, min(h, int(y1)))
    y2 = max(0, min(h, int(y2)))

    roi = frame[y1:y2, x1:x2]
    return roi if roi.size else None


def preprocess(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th


def extract_float(text):
    if not text:
        return None
    text = text.replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return float(text)
    except:
        return None


def extract_symbol_and_timeframe(text):
    if not text:
        return None, None

    tokens = text.split()
    symbol = []
    timeframe = None

    for t in tokens:
        if any(u in t.lower() for u in ["m", "h", "d", "wk"]):
            timeframe = t
        else:
            symbol.append(t)

    return " ".join(symbol) if symbol else None, timeframe


def parse_frame_to_snapshot(frame: np.ndarray):
    with open("vision_service/calibration.json") as f:
        cal = json.load(f)

    H, W = frame.shape[:2]

    def cx(px): return cal["left"] + px * cal["width"]
    def cy(py): return cal["top"] + py * cal["height"]

    # --- SYMBOL + TIMEFRAME ---
    symbol_roi = safe_crop(frame, cx(0.02), cy(0.02), cx(0.45), cy(0.15))
    symbol_text = None
    symbol = None
    timeframe = None

    if symbol_roi is not None:
        text = reader.readtext(preprocess(symbol_roi), detail=0)
        symbol_text = " ".join(text)
        symbol, timeframe = extract_symbol_and_timeframe(symbol_text)

    # --- LAST PRICE ---
    price_roi = safe_crop(frame, cx(0.80), cy(0.30), cx(0.98), cy(0.65))
    last_price = None
    if price_roi is not None:
        text = reader.readtext(preprocess(price_roi), detail=0)
        last_price = extract_float(" ".join(text))

    # --- PnL ---
    pnl_roi = safe_crop(frame, cx(0.70), cy(0.75), cx(0.98), cy(0.98))
    pnl = None
    if pnl_roi is not None:
        text = reader.readtext(preprocess(pnl_roi), detail=0)
        pnl = extract_float(" ".join(text))

    snapshot = {
        "source": "screen_capture",
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "last_price": last_price,
        "pnl": pnl,
        "position_size": None,
        "extra": {
            "raw_symbol_text": symbol_text
        }
    }

    return snapshot