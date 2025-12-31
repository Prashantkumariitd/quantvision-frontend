from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class MarketSnapshot(BaseModel):
    source: str  # e.g. "screen_capture"
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    timestamp: datetime
    last_price: Optional[float] = None
    pnl: Optional[float] = None
    position_size: Optional[float] = None
    extra: Optional[Dict[str, float]] = None  # for indicators etc.
