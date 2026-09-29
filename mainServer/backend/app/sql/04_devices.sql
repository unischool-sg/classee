CREATE TABLE devices (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    name          text        NOT NULL,
    token_hash    text        NOT NULL UNIQUE,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz,
    revoked_at    timestamptz
);

CREATE UNIQUE INDEX devices_one_active_per_classroom
    ON devices (classroom_id) WHERE revoked_at IS NULL;
