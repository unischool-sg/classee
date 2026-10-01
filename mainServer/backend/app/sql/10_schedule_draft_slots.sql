-- 確定前の下書きのコマ。録画機はこのテーブルを一切読まない
-- 確定のときに schedule_slots へそのまま移るので、同じ制約をかけておく
CREATE TABLE schedule_draft_slots (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz NOT NULL,
    note          text,
    created_by    bigint      NOT NULL REFERENCES users(id),
    CHECK (starts_at < ends_at),
    CHECK (ends_at - starts_at <= interval '4 hours'),
    CHECK ((starts_at AT TIME ZONE 'Asia/Tokyo')::time >= time '07:00'),
    CHECK ((ends_at   AT TIME ZONE 'Asia/Tokyo')::time <= time '19:00'),
    CHECK ((starts_at AT TIME ZONE 'Asia/Tokyo')::date = (ends_at AT TIME ZONE 'Asia/Tokyo')::date),
    -- コマはその下書きの月の中だけ
    CHECK (date_trunc('month', starts_at AT TIME ZONE 'Asia/Tokyo')::date = month),
    UNIQUE (classroom_id, starts_at),
    EXCLUDE USING gist (classroom_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
);

-- 確定のときに消すので DELETE も要る。録画機には一切与えない
GRANT SELECT, INSERT, UPDATE, DELETE ON schedule_draft_slots TO classee_staff_api;

CREATE TRIGGER schedule_draft_slots_audit
    AFTER INSERT OR UPDATE OR DELETE ON schedule_draft_slots
    FOR EACH ROW EXECUTE FUNCTION audit_row();
