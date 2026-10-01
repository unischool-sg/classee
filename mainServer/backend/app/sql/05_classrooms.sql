-- 教室
CREATE TABLE classrooms (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        text        NOT NULL UNIQUE,                -- 例: '3年1組'
    created_at  timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE ON classrooms TO classee_staff_api;

CREATE TRIGGER classrooms_audit
    AFTER INSERT OR UPDATE OR DELETE ON classrooms
    FOR EACH ROW EXECUTE FUNCTION audit_row();
