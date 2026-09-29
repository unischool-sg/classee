CREATE TABLE audit_logs (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at  timestamptz NOT NULL DEFAULT now(),
    user_id      bigint      REFERENCES users(id),
    device_id    bigint      REFERENCES devices(id),
    action       text        NOT NULL,                      -- 例: 'slot.cancel', 'recording.view'
    target_type  text,
    target_id    bigint,
    detail       jsonb       NOT NULL DEFAULT '{}'
);

CREATE INDEX audit_logs_occurred_at_idx ON audit_logs (occurred_at);
