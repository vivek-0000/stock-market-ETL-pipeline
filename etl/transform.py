"""TRANSFORM: clean raw price data with Pandas."""
import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

RENAME = {
    "1. open": "open", "2. high": "high", "3. low": "low",
    "4. close": "close", "5. volume": "volume",
}
PRICE_COLS = ["open", "high", "low", "close"]
OUTPUT_COLS = [
    "symbol", "trade_date", "open", "high", "low", "close", "volume",
    "daily_return", "sma_20",
]


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=RENAME).copy()
    n_raw = len(df)

    # --- date formatting -------------------------------------------------
    df["trade_date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.drop(columns=["date"]).dropna(subset=["trade_date"])

    # --- symbol normalisation -------------------------------------------
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

    # --- types: API returns strings -------------------------------------
    for col in PRICE_COLS + ["volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- duplicates: keep the last record per (symbol, date) ------------
    df = df.sort_values(["symbol", "trade_date"])
    before = len(df)
    df = df.drop_duplicates(subset=["symbol", "trade_date"], keep="last")
    log.info("dropped %d duplicate rows", before - len(df))

    # --- missing values --------------------------------------------------
    # prices: non-positive values are invalid -> treat as missing
    df[PRICE_COLS] = df[PRICE_COLS].where(df[PRICE_COLS] > 0)
    # forward-fill within each symbol (carry last known price), then drop leftovers
    df[PRICE_COLS] = df.groupby("symbol")[PRICE_COLS].ffill()
    df = df.dropna(subset=PRICE_COLS)
    df["volume"] = df["volume"].fillna(0).clip(lower=0).astype("int64")

    # --- consistency: high/low must bracket open/close -------------------
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)

    # --- derived features ------------------------------------------------
    g = df.groupby("symbol")["close"]
    df["daily_return"] = g.pct_change().round(6)
    df["sma_20"] = g.transform(lambda s: s.rolling(20, min_periods=5).mean()).round(4)
    df[["daily_return", "sma_20"]] = df[["daily_return", "sma_20"]].replace([np.inf, -np.inf], np.nan)

    df = df[OUTPUT_COLS].reset_index(drop=True)
    log.info("transform: %d raw -> %d clean rows", n_raw, len(df))
    return df
