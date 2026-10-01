-- 確定の記録: 行があれば、その教室のその月は確定済み
-- 録画機はこれを見ない。画面の表示と、未確定の月を知らせるためだけに使う
CREATE TABLE schedule_months (
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    month         date        NOT NULL CHECK (EXTRACT(DAY FROM month) = 1),
    confirmed_at  timestamptz NOT NULL DEFAULT now(),
    confirmed_by  bigint      NOT NULL REFERENCES users(id),
    PRIMARY KEY (classroom_id, month)
);

GRANT SELECT, INSERT ON schedule_months TO classee_staff_api;

CREATE TRIGGER schedule_months_audit
    AFTER INSERT OR UPDATE OR DELETE ON schedule_months
    FOR EACH ROW EXECUTE FUNCTION audit_row();
