"""EXTRACT: pull daily OHLCV prices from the Alpha Vantage REST API."""
import logging
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from etl import config

log = logging.getLogger(__name__)


class ExtractError(RuntimeError):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def fetch_symbol(symbol: str, session: requests.Session | None = None) -> pd.DataFrame:
    """Return the raw daily time series for one symbol as a DataFrame."""
    session = session or _session()
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": config.OUTPUT_SIZE,
        "apikey": config.API_KEY,
    }
    resp = session.get(config.API_URL, params=params, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    series = payload.get("Time Series (Daily)")
    if not series:
        # Alpha Vantage returns HTTP 200 with a message on rate limit / bad symbol
        msg = payload.get("Note") or payload.get("Information") or payload.get("Error Message") or "empty response"
        raise ExtractError(f"{symbol}: {msg}")

    df = (
        pd.DataFrame.from_dict(series, orient="index")
        .rename_axis("date")
        .reset_index()
    )
    df.insert(0, "symbol", symbol)
    return df


def extract(symbols: list[str] | None = None) -> pd.DataFrame:
    """Fetch all symbols; a failure on one symbol does not abort the others."""
    symbols = symbols or config.SYMBOLS
    session = _session()
    frames, failures = [], []

    for i, sym in enumerate(symbols):
        try:
            frames.append(fetch_symbol(sym, session))
            log.info("extracted %s (%d rows)", sym, len(frames[-1]))
        except (ExtractError, requests.RequestException) as exc:
            log.error("extract failed for %s: %s", sym, exc)
            failures.append(sym)
        if i < len(symbols) - 1:
            time.sleep(config.REQUEST_PAUSE_SECONDS)

    if not frames:
        raise ExtractError(f"all symbols failed: {failures}")
    if failures:
        log.warning("partial extract, failed symbols: %s", failures)
    return pd.concat(frames, ignore_index=True)
