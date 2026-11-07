"""Dashboard backend. Reads PostgreSQL; falls back to demo data if the DB is unreachable or empty."""
import os

import psycopg2
from flask import Flask, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

from dashboard import demo

app = Flask(__name__)

DB = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "stocks"),
    "user": os.getenv("POSTGRES_USER", "etl"),
    "password": os.getenv("POSTGRES_PASSWORD", "etl_password"),
    "connect_timeout": 2,
}
FORCE_DEMO = os.getenv("DASHBOARD_DEMO") == "1"


def query(sql, args=()):
    """Return rows, or None when the database is unavailable."""
    if FORCE_DEMO:
        return None
    try:
        conn_obj = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5) if os.getenv("DATABASE_URL") \
            else psycopg2.connect(**DB)
        with conn_obj as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    except psycopg2.Error:
        return None


def num(v):
    return float(v) if v is not None else None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/symbols")
def symbols():
    rows = query("""
        SELECT DISTINCT ON (symbol) symbol, trade_date, close, volume, daily_return
        FROM stock_prices ORDER BY symbol, trade_date DESC""")
    if not rows:
        return jsonify(mode="demo", data=demo.symbols())
    data = [{"symbol": r["symbol"], "last_close": num(r["close"]),
             "change_pct": round((num(r["daily_return"]) or 0) * 100, 2),
             "volume": r["volume"], "last_date": r["trade_date"].isoformat()} for r in rows]
    return jsonify(mode="live", data=data)


@app.get("/api/prices/<symbol>")
def prices(symbol):
    days = min(int(request.args.get("days", 90)), 500)
    rows = query("""
        SELECT trade_date, open, high, low, close, volume, sma_20 FROM (
            SELECT * FROM stock_prices WHERE symbol = %s ORDER BY trade_date DESC LIMIT %s
        ) t ORDER BY trade_date""", (symbol.upper(), days))
    if not rows:
        return jsonify(mode="demo", data=demo.prices(symbol, days))
    data = [{"date": r["trade_date"].isoformat(), **{k: num(r[k]) for k in ("open", "high", "low", "close", "sma_20")},
             "volume": r["volume"]} for r in rows]
    return jsonify(mode="live", data=data)


@app.get("/api/runs")
def runs():
    rows = query("""
        SELECT run_id, started_at, status, rows_extracted, rows_loaded, message,
               EXTRACT(EPOCH FROM (finished_at - started_at))::int AS duration_s
        FROM etl_runs ORDER BY run_id DESC LIMIT 8""")
    if not rows:
        return jsonify(mode="demo", data=demo.runs())
    for r in rows:
        r["started_at"] = r["started_at"].isoformat()
    return jsonify(mode="live", data=rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
