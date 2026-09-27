CREATE TABLE IF NOT EXISTS weekly_periods (
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0=月 1=火 … 6=日
    period  INTEGER NOT NULL,
    PRIMARY KEY (weekday, period)
);