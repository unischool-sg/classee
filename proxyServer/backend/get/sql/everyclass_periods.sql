CREATE TABLE IF NOT EXISTS periods (
    period     INTEGER PRIMARY KEY,
    start_time TEXT NOT NULL,          -- 'HH:MM'
    end_time   TEXT NOT NULL,
    CHECK (time(start_time) IS NOT NULL AND time(end_time) IS NOT NULL),
    CHECK (time(start_time) < time(end_time))
);