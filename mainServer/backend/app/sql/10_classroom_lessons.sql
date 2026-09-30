CREATE TABLE classroom_period_counts (
    classroom_id  bigint   NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    weekday       smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    periods       smallint NOT NULL CHECK (periods BETWEEN 0 AND 10),
    PRIMARY KEY (classroom_id, weekday)
);

CREATE TABLE classroom_skips (
    classroom_id  bigint   NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    weekday       smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    period        smallint NOT NULL CHECK (period BETWEEN 1 AND 10),
    note          text,
    PRIMARY KEY (classroom_id, weekday, period)
);
