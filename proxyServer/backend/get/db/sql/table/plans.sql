CREATE TABLE IF NOT EXISTS schedule (
    start_at INTEGER PRIMARY KEY,
    end_at   INTEGER NOT NULL,
    label    TEXT NOT NULL DEFAULT ''
);