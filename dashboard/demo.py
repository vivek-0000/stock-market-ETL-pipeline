"""Synthetic data so the dashboard works before the pipeline has ever run."""
import random
from datetime import date, datetime, timedelta, timezone

BASE = {"AAPL": 230, "MSFT": 440, "GOOGL": 185, "AMZN": 210, "NVDA": 140}


def _series(symbol: str, days: int = 120):
    rnd = random.Random(symbol)
    price, out, d = BASE.get(symbol, 100), [], date.today()
    rows = []
    while len(rows) < days:
        if d.weekday() < 5:
            rows.append(d)
        d -= timedelta(days=1)
    for day in reversed(rows):
        o = price
        c = o * (1 + rnd.gauss(0.0006, 0.015))
        h, l = max(o, c) * (1 + rnd.random() * 0.007), min(o, c) * (1 - rnd.random() * 0.007)
        out.append({"date": day.isoformat(), "open": o, "high": h, "low": l, "close": c,
                    "volume": int(rnd.uniform(2e7, 9e7))})
        price = c
    closes = [r["close"] for r in out]
    for i, r in enumerate(out):
        w = closes[max(0, i - 19): i + 1]
        r["sma_20"] = sum(w) / len(w)
    return out


def symbols():
    res = []
    for s in BASE:
        rows = _series(s)
        last, prev = rows[-1], rows[-2]
        res.append({"symbol": s, "last_close": round(last["close"], 2),
                    "change_pct": round((last["close"] / prev["close"] - 1) * 100, 2),
                    "volume": last["volume"], "last_date": last["date"]})
    return res


def prices(symbol: str, days: int):
    return _series(symbol.upper())[-days:]


def runs():
    now = datetime.now(timezone.utc)
    out = []
    for i in range(8):
        failed = i == 3
        out.append({"run_id": 108 - i,
                    "started_at": (now - timedelta(days=i, minutes=7)).isoformat(),
                    "status": "failed" if failed else "success",
                    "rows_extracted": 0 if failed else 500,
                    "rows_loaded": 0 if failed else 497 - i,
                    "duration_s": 94 - i * 3,
                    "message": "NVDA: rate limit reached" if failed else "497 clean rows from 5 symbols"})
    return out
