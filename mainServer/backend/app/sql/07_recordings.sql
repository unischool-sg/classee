CREATE TABLE recordings (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slot_id      bigint      NOT NULL REFERENCES schedule_slots(id),
    device_id    bigint      NOT NULL REFERENCES devices(id),
    file_name    text        NOT NULL,
    object_key   text        NOT NULL UNIQUE,               -- RustFS 上の場所
    size_bytes   bigint      NOT NULL CHECK (size_bytes > 0),
    sha256       char(64)    NOT NULL,
    uploaded_at  timestamptz NOT NULL DEFAULT now(),
    deleted_at   timestamptz,                               -- 保存期間切れで削除した時刻
    UNIQUE (slot_id, file_name)                             -- 送り直しは上書き扱い
);
