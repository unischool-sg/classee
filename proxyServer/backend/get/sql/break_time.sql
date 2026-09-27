CREATE TABLE IF NOT EXISTS weekly (
    weekday INTEGER PRIMARY KEY CHECK (weekday BETWEEN 0 AND 6),  -- 0=月 1=火 … 6=日
    periods INTEGER NOT NULL CHECK (periods >= 0)
);