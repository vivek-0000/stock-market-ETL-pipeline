"""Daily stock ETL DAG. Runs weekdays after the US market close (21:00 UTC)."""
from __future__ import annotations

import os
import tempfile
from datetime import timedelta

import pendulum
import pandas as pd
from airflow.decorators import dag, task

from etl import config

TMP = os.path.join(tempfile.gettempdir(), "stock_etl")


@dag(
    dag_id="stock_market_etl",
    description="Extract -> Transform -> Load daily stock prices into PostgreSQL",
    schedule="30 22 * * 1-5",  # 22:30 UTC, Mon-Fri
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 3, "retry_delay": timedelta(minutes=10), "retry_exponential_backoff": True},
    tags=["etl", "stocks"],
)
def stock_market_etl():
    @task
    def extract_task(run_id=None) -> str:
        from etl.extract import extract
        os.makedirs(TMP, exist_ok=True)
        path = os.path.join(TMP, f"{run_id}_raw.parquet".replace(":", "_"))
        extract(config.SYMBOLS).to_parquet(path)
        return path  # pass a file path via XCom, not the data itself

    @task
    def transform_task(raw_path: str) -> str:
        from etl.transform import transform
        clean = transform(pd.read_parquet(raw_path))
        out = raw_path.replace("_raw", "_clean")
        clean.to_parquet(out)
        return out

    @task
    def load_task(clean_path: str) -> int:
        from etl.load import load
        return load(pd.read_parquet(clean_path))

    @task(trigger_rule="all_done")
    def cleanup(*paths: str):
        for p in paths:
            if p and os.path.exists(p):
                os.remove(p)

    raw = extract_task()
    clean = transform_task(raw)
    loaded = load_task(clean)
    loaded >> cleanup(raw, clean)


stock_market_etl()
