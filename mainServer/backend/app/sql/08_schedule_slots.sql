-- 録画予定: 確定したコマだけが入る。録画機はこのテーブルだけを読む
CREATE TABLE schedule_slots (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    period        smallint,                                 -- 手動で足したコマは NULL でよい
    starts_at     timestamptz NOT NULL,
    ends_at       timestamptz NOT NULL,
    note          text,
    created_by    bigint      NOT NULL REFERENCES users(id), -- 確定・追加した人
    created_at    timestamptz NOT NULL DEFAULT now(),
    cancelled_at  timestamptz,                              -- 取り消し（行は消さない）
    cancelled_by  bigint      REFERENCES users(id),
    CHECK (starts_at < ends_at),
    CHECK (ends_at - starts_at <= interval '4 hours'),      -- 録画機の上限と揃える
    -- 学校の時間帯（日本時間）の外、日付をまたぐコマは、どんな事情でも入れない
    CHECK ((starts_at AT TIME ZONE 'Asia/Tokyo')::time >= time '07:00'),
    CHECK ((ends_at   AT TIME ZONE 'Asia/Tokyo')::time <= time '19:00'),
    CHECK ((starts_at AT TIME ZONE 'Asia/Tokyo')::date = (ends_at AT TIME ZONE 'Asia/Tokyo')::date),
    CHECK ((cancelled_at IS NULL) = (cancelled_by IS NULL)),
    -- 取り消したコマも含めて、同じ教室・同じ開始時刻は1行だけ
    -- （取り消したコマを戻すときは、新しく足すのではなく取り消しを解除する）
    UNIQUE (classroom_id, starts_at),
    -- 取り消されていないコマ同士は、同じ教室で時間が重ならない
    EXCLUDE USING gist (classroom_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
        WHERE (cancelled_at IS NULL)
);

-- 教職員は足す・読む、時刻の変更と取り消しだけ。誰が足したか（created_by）は書き換えさせず、行も消させない
GRANT SELECT, INSERT ON schedule_slots TO classee_staff_api;
GRANT UPDATE (starts_at, ends_at, note, cancelled_at, cancelled_by) ON schedule_slots TO classee_staff_api;
-- 録画機は読むだけ
GRANT SELECT ON schedule_slots TO classee_camera_api;

CREATE TRIGGER schedule_slots_audit
    AFTER INSERT OR UPDATE OR DELETE ON schedule_slots
    FOR EACH ROW EXECUTE FUNCTION audit_row();
