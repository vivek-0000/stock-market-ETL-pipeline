"""LOAD: idempotent upsert of clean data into PostgreSQL."""
import logging

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from etl import config

log = logging.getLogger(__name__)

UPSERT_SQL = """
INSERT INTO stock_prices
    (symbol, trade_date, open, high, low, close, volume, daily_return, sma_20)
VALUES %s
ON CONFLICT (symbol, trade_date) DO UPDATE SET
    open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
    close = EXCLUDED.close, volume = EXCLUDED.volume,
    daily_return = EXCLUDED.daily_return, sma_20 = EXCLUDED.sma_20,
    updated_at = NOW();
"""


def connect():
    if config.DATABASE_URL:
        return psycopg2.connect(config.DATABASE_URL)
    return psycopg2.connect(**config.DB_CONFIG)


def load(df: pd.DataFrame, conn=None) -> int:
    """Upsert rows; re-running the same day never creates duplicates."""
    if df.empty:
        return 0
    own = conn is None
    conn = conn or connect()
    # NaN -> None so PostgreSQL stores NULL
    rows = list(df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))
    try:
        with conn, conn.cursor() as cur:
            execute_values(cur, UPSERT_SQL, rows, page_size=1000)
        log.info("loaded %d rows", len(rows))
        return len(rows)
    finally:
        if own:
            conn.close()
