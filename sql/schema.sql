-- Run automatically by the postgres container on first start.
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol        VARCHAR(12)    NOT NULL,
    trade_date    DATE           NOT NULL,
    open          NUMERIC(14, 4) NOT NULL,
    high          NUMERIC(14, 4) NOT NULL,
    low           NUMERIC(14, 4) NOT NULL,
    close         NUMERIC(14, 4) NOT NULL,
    volume        BIGINT         NOT NULL DEFAULT 0,
    daily_return  NUMERIC(10, 6),
    sma_20        NUMERIC(14, 4),
    updated_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, trade_date),
    CHECK (high >= low)
);

CREATE INDEX IF NOT EXISTS idx_stock_prices_date ON stock_prices (trade_date DESC);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id          BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(12) NOT NULL DEFAULT 'running',  -- running | success | failed
    rows_extracted  INTEGER,
    rows_loaded     INTEGER,
    message         TEXT
);
