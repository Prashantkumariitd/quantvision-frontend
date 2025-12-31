# engine.py
import pandas as pd
import yfinance as yf
from typing import Optional, Sequence, Dict


# ---------- DATA LOADING ----------

def load_price_df(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """
    Download OHLCV data for a ticker and return a DataFrame
    with a single 'close_price' column.
    """
    raw = yf.download(ticker, period=period, interval=interval, auto_adjust=False)

    if raw.empty:
        raise ValueError(f"No data returned for ticker {ticker}")

    # Handle MultiIndex columns if present (yfinance sometimes does this)
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = list(raw.columns.get_level_values(0))
        lvl1 = list(raw.columns.get_level_values(1))
        price_labels = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

        if any(lbl in price_labels for lbl in lvl0):
            raw.columns = raw.columns.get_level_values(0)
        elif any(lbl in price_labels for lbl in lvl1):
            raw.columns = raw.columns.get_level_values(1)
        else:
            raise ValueError("Could not detect price columns from MultiIndex")

    # Pick a price column
    price_col = None
    for col in ["Close", "Adj Close", "close", "adjclose", "Price", "price"]:
        if col in raw.columns:
            price_col = col
            break

    if price_col is None:
        raise ValueError(f"No price column found in data. Got columns: {list(raw.columns)}")

    df = raw[[price_col]].copy()
    df.rename(columns={price_col: "close_price"}, inplace=True)

    # Ensure it's 1D numeric
    cp = df["close_price"]
    if isinstance(cp, pd.DataFrame):
        cp = cp.iloc[:, 0]
    df["close_price"] = pd.to_numeric(cp, errors="coerce")

    return df


# ---------- SIGNAL BUILDING ----------

def build_signals(data: pd.DataFrame) -> pd.DataFrame:
    """
    Take a DataFrame with a 'close_price' column and add all technical features.
    Returns a new DataFrame with signals.
    """
    if "close_price" not in data.columns:
        raise ValueError("DataFrame must contain a 'close_price' column")

    df = data.copy()
    cp = df["close_price"]

    # Moving averages
    df["MA_short"] = cp.rolling(20).mean()
    df["MA_long"] = cp.rolling(50).mean()

    # Returns
    df["return"] = cp.pct_change()

    # Trend signal (short MA above long MA)
    df["trend_signal"] = (df["MA_short"] > df["MA_long"]).astype(int)

    # Trend strength
    df["trend_strength"] = (cp - df["MA_long"]) / df["MA_long"]

    # Volatility
    df["volatility"] = df["return"].rolling(14).std()

    # Market regime
    df["market_regime"] = "Sideways"
    df.loc[(df["trend_strength"] > 0.01) & (df["volatility"] < 0.02), "market_regime"] = "Bull-Low-Vol"
    df.loc[(df["trend_strength"] > 0.01) & (df["volatility"] >= 0.02), "market_regime"] = "Bull-High-Vol"
    df.loc[df["trend_strength"] < -0.01, "market_regime"] = "Bear"

    # RSI
    window = 14
    delta = cp.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # RSI-based signal
    df["rsi_signal"] = 0
    df.loc[(df["market_regime"].str.startswith("Bull")) & (df["rsi"] > 55), "rsi_signal"] = 1
    df.loc[(df["market_regime"] == "Bear") & (df["rsi"] < 45), "rsi_signal"] = -1

    # Breakout strategy
    breakout_window = 20
    df["recent_high"] = cp.rolling(breakout_window).max().shift(1)
    df["recent_low"] = cp.rolling(breakout_window).min().shift(1)

    df["breakout_signal"] = 0
    df.loc[cp > df["recent_high"], "breakout_signal"] = 1
    df.loc[cp < df["recent_low"], "breakout_signal"] = -1

    # Combined voting
    strategy_cols = ["trend_signal", "rsi_signal", "breakout_signal"]
    df["signal_sum"] = df[strategy_cols].sum(axis=1)
    df["signal_count"] = (df[strategy_cols] != 0).sum(axis=1)

    return df


# ---------- RECOMMENDATION LOGIC ----------

def make_recommendation(
    row: pd.Series,
    ml_model=None,
    feature_cols: Optional[Sequence[str]] = None,
) -> Dict:
    """
    Take the latest row of features and produce a recommendation dict.
    """
    # Cast everything to plain Python types to avoid pandas ambiguity
    signal_sum = float(row["signal_sum"])
    signal_count = float(row["signal_count"])
    trend_signal = int(row["trend_signal"])
    rsi_signal = int(row["rsi_signal"])
    breakout_signal = int(row["breakout_signal"])
    price = float(row["close_price"])
    rsi_value = float(row["rsi"]) if pd.notna(row["rsi"]) else None
    market_regime = str(row["market_regime"])

    # Decide action
    if signal_sum > 0:
        action = "BUY / LONG"
    elif signal_sum < 0:
        action = "SELL / SHORT"
    else:
        action = "NO TRADE"

    # Confidence
    confidence = abs(signal_sum) / signal_count if signal_count > 0 else 0.0

    # Optional ML probability
    ml_prob = None
    if (ml_model is not None) and (feature_cols is not None):
        X = row[list(feature_cols)].astype(float).values.reshape(1, -1)
        ml_prob = float(ml_model.predict_proba(X)[0, 1])

    return {
        "price": price,
        "market_regime": market_regime,
        "rsi": rsi_value,
        "trend_signal": trend_signal,
        "rsi_signal": rsi_signal,
        "breakout_signal": breakout_signal,
        "signal_sum": signal_sum,
        "signal_count": signal_count,
        "action": action,
        "confidence_score": round(confidence, 2),
        "ml_prob_profitable": ml_prob,
    }


def get_recommendation_for_ticker(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
    ml_model=None,
    feature_cols: Optional[Sequence[str]] = None,
) -> Dict:
    """
    High-level helper:
    1) downloads data
    2) builds signals
    3) takes latest row
    4) returns recommendation dict
    """
    df_price = load_price_df(ticker, period=period, interval=interval)
    df_sig = build_signals(df_price)

    # Require essential fields available
    df_sig = df_sig.dropna(subset=["close_price", "MA_long", "return", "trend_strength", "volatility", "rsi"])

    if df_sig.empty:
        raise ValueError("Not enough data to compute signals after dropping NaNs.")

    latest = df_sig.iloc[-1]
    rec = make_recommendation(latest, ml_model=ml_model, feature_cols=feature_cols)
    rec["ticker"] = ticker
    rec["period_used"] = period
    rec["interval_used"] = interval
    return rec
