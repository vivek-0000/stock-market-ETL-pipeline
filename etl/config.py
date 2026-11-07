"""Central configuration, read from environment variables."""
import os

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
API_URL = os.getenv("API_URL", "https://www.alphavantage.co/query")
SYMBOLS = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,NVDA").split(",") if s.strip()]
OUTPUT_SIZE = os.getenv("OUTPUT_SIZE", "compact")  # compact = last 100 days, full = 20+ years
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
# Alpha Vantage free tier allows 5 calls/minute -> wait 13s between symbols
REQUEST_PAUSE_SECONDS = float(os.getenv("REQUEST_PAUSE_SECONDS", "13"))

# Hosted databases (Neon, Supabase, ...) give one connection string; it takes priority.
DATABASE_URL = os.getenv("DATABASE_URL")

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "stocks"),
    "user": os.getenv("POSTGRES_USER", "etl"),
    "password": os.getenv("POSTGRES_PASSWORD", "etl_password"),
}
