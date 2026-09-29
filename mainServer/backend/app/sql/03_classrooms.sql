CREATE TABLE classrooms (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text        NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now()
);
