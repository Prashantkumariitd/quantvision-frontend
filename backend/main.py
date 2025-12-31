from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime
from pydantic import BaseModel

from .models import MarketSnapshot
from engine import get_recommendation_for_ticker




app = FastAPI(title="QuantVision Backend", version="1.0")
clients = set()
clients: List[WebSocket] = []
SNAPSHOT_BUFFER: List[MarketSnapshot] = []
LATEST_SIGNAL = {}




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
async def broadcast_snapshot(snapshot: dict):
    dead = []
    for ws in clients:
        try:
            await ws.send_json(snapshot)
        except:
            dead.append(ws)

    for ws in dead:
        clients.remove(ws)




@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}




class Calibration(BaseModel):
    x: float
    y: float
    width: float
    height: float


@app.post("/calibrate")
def save_calibration(data: Calibration):
    region = {
        "left": int(data.x),
        "top": int(data.y),
        "width": int(data.width),
        "height": int(data.height),
    }

    import json
    with open("vision_service/calibration.json", "w") as f:
        json.dump(region, f, indent=2)

    return {"status": "saved"}




async def broadcast_snapshot(data: dict):
    dead_clients = []

    for client in clients:
        try:
            await client.send_json(data)
        except:
            dead_clients.append(client)

    for client in dead_clients:
        clients.remove(client)




@app.post("/ingest/market_snapshot")
async def ingest_market_snapshot(snapshot: MarketSnapshot):
    SNAPSHOT_BUFFER.append(snapshot)
    await broadcast_snapshot(snapshot.dict())
    await analyze_snapshot(snapshot)
    return {"status": "received"}




@app.post("/analyze_snapshot")
async def analyze_snapshot(snapshot: MarketSnapshot):
    if snapshot.symbol:
        try:
            rec = get_recommendation_for_ticker(snapshot.symbol)
            LATEST_SIGNAL.update(rec)
            return {"status": "ok", "signal": rec}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    return {"status": "no_symbol"}




@app.websocket("/ws/vision")
async def vision_socket(ws: WebSocket):
    await ws.accept()
    clients.append(ws)

    try:
        while True:
            await ws.receive_text()
    except:
        pass
    finally:
        if ws in clients:
            clients.remove(ws)
