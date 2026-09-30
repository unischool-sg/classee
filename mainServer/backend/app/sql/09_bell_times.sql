CREATE TABLE bell_times (
    weekday     smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),  -- 1=月 … 7=日
    period      smallint NOT NULL CHECK (period BETWEEN 1 AND 10),
    start_time  time     NOT NULL,
    end_time    time     NOT NULL,
    CHECK (start_time < end_time),
    PRIMARY KEY (weekday, period)
);
