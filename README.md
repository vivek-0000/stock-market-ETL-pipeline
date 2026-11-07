# Stock Market Data ETL Pipeline

Extract daily stock prices from a REST API, clean them with Pandas, load them into PostgreSQL, and
refresh automatically every weekday with Airflow. Includes a dark-mode monitoring dashboard.

```
Alpha Vantage API ──► extract.py ──► transform.py ──► load.py ──► PostgreSQL ──► Dashboard
                        (Airflow DAG: stock_market_etl, Mon–Fri 22:30 UTC)
```

## Quick start (Docker)

```bash
cp .env.example .env        # add your free Alpha Vantage key
docker compose up -d
```

| Service   | URL                    | Notes                              |
|-----------|------------------------|------------------------------------|
| Dashboard | http://localhost:5000  | dark UI; shows demo data until the DB has rows |
| Airflow   | http://localhost:8080  | admin password: `docker compose logs airflow \| grep -i password` |
| Postgres  | localhost:5432         | schema auto-created from `sql/schema.sql` |

In Airflow, unpause **stock_market_etl** and trigger it once manually.

## Run without Airflow

```bash
pip install -r requirements.txt
docker compose up -d postgres
python -m etl.pipeline --symbols AAPL,MSFT
DASHBOARD_DEMO=1 python -m dashboard.app     # or omit DASHBOARD_DEMO to read the DB
```

## What the transform step does

| Problem            | Handling                                                        |
|--------------------|-----------------------------------------------------------------|
| String values      | `pd.to_numeric(errors="coerce")`                                |
| Bad / mixed dates  | `pd.to_datetime(errors="coerce")` → `DATE`, invalid rows dropped |
| Duplicates         | one row per `(symbol, trade_date)`, last record wins             |
| Missing / ≤0 prices| forward-filled per symbol; leading gaps dropped                  |
| Missing volume     | filled with 0                                                    |
| OHLC consistency   | `high`/`low` recomputed to bracket open/close                    |
| Features           | `daily_return`, 20-day SMA                                       |

## Design notes

- **Idempotent loads**: `INSERT … ON CONFLICT DO UPDATE`, so retries and backfills never duplicate rows.
- **Rate limits**: free Alpha Vantage allows 5 calls/min; the extractor pauses between symbols and a single failing symbol doesn't abort the run.
- **Observability**: every run is logged to `etl_runs` and shown in the dashboard.
- **Airflow**: tasks pass parquet file paths through XCom (not DataFrames); 3 retries with exponential backoff.
- Set `OUTPUT_SIZE=full` once for a historical backfill.
- Never commit `.env`; the default `demo` API key only works for a few symbols.
