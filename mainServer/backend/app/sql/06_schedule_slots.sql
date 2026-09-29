CREATE TABLE schedule_slots (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    period        smallint,                                 -- 手動で足したコマは NULL でよい
    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz NOT NULL,
    note          text,
    created_by    bigint      REFERENCES users(id),         -- NULL なら月初の自動書き出し
    created_at    timestamptz NOT NULL DEFAULT now(),
    cancelled_at  timestamptz,                              -- 取り消し（行は消さない）
    cancelled_by  bigint      REFERENCES users(id),
    CHECK (starts_at < ends_at),
    CHECK (ends_at - starts_at <= interval '4 hours'),      -- 録画機の上限と揃える
    CHECK ((cancelled_at IS NULL) = (cancelled_by IS NULL)),
    -- 取り消したコマも含めて、同じ教室・同じ開始時刻は1行だけ
    -- （月初の書き出しをやり直しても、取り消したコマが復活しないようにするため）
    UNIQUE (classroom_id, starts_at),
    -- 取り消されていないコマ同士は、同じ教室で時間が重ならない
    EXCLUDE USING gist (classroom_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
        WHERE (cancelled_at IS NULL)
);
