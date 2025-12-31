import time
import asyncio
import json
from datetime import datetime
import requests

from .config import BACKEND_URL, CAPTURE_INTERVAL
from .capture import grab_chart_frame
from .ocr_pipeline import parse_frame_to_snapshot


def send_snapshot(snapshot: dict):
    url = f"{BACKEND_URL}/ingest/market_snapshot"
    requests.post(url, json=snapshot, timeout=1)

    try:
        asyncio.run(send_ws(snapshot))
    except:
        pass
async def send_ws(snapshot):
    import websockets, json
    async with websockets.connect("ws://127.0.0.1:8000/ws/vision") as ws:
        await ws.send(json.dumps(snapshot))



def main_loop():
    print(f"Starting vision ingestion. Backend: {BACKEND_URL}, interval: {CAPTURE_INTERVAL}s")
    while True:
        frame = grab_chart_frame()
        snapshot = parse_frame_to_snapshot(frame)
        print("Snapshot:", json.dumps(snapshot, indent=2))
        send_snapshot(snapshot)
        time.sleep(CAPTURE_INTERVAL)


if __name__ == "__main__":
    main_loop()

