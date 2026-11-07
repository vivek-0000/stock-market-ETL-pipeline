"""Run the whole pipeline: python -m etl.pipeline [--symbols AAPL,MSFT]"""
import argparse
import logging

from etl import config
from etl.extract import extract
from etl.load import connect, load
from etl.transform import transform

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("etl.pipeline")


def run(symbols: list[str] | None = None) -> dict:
    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute("INSERT INTO etl_runs DEFAULT VALUES RETURNING run_id")
        run_id = cur.fetchone()[0]

    extracted = loaded = 0
    try:
        raw = extract(symbols)
        extracted = len(raw)
        clean = transform(raw)
        loaded = load(clean, conn)
        status, msg = "success", f"{len(clean)} clean rows from {raw['symbol'].nunique()} symbols"
    except Exception as exc:  # record failure, then re-raise so Airflow marks the task failed
        status, msg = "failed", str(exc)[:500]
        log.exception("pipeline failed")
        raise
    finally:
        with conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE etl_runs SET finished_at = NOW(), status=%s, rows_extracted=%s, "
                "rows_loaded=%s, message=%s WHERE run_id=%s",
                (status, extracted, loaded, msg, run_id),
            )
        conn.close()
    return {"run_id": run_id, "extracted": extracted, "loaded": loaded}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", help="comma-separated, defaults to $SYMBOLS")
    args = ap.parse_args()
    syms = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else config.SYMBOLS
    print(run(syms))
