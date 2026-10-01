-- 録画機
CREATE TABLE devices (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    classroom_id  bigint      NOT NULL REFERENCES classrooms(id),
    name          text        NOT NULL,
    token_hash    text        NOT NULL UNIQUE,              -- トークンの SHA-256
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz,                              -- 最後に予定を取りに来た時刻
    revoked_at    timestamptz                               -- 盗難・交換で無効化
);

-- 1つの教室で有効な録画機は1台まで（無効化した古い録画機は残してよい）
CREATE UNIQUE INDEX devices_one_active_per_classroom
    ON devices (classroom_id) WHERE revoked_at IS NULL;

GRANT SELECT, INSERT, UPDATE ON devices TO classee_staff_api;
-- 録画機は自分の情報を読み、最後に来た時刻だけ書ける。トークンは書き換えられない
GRANT SELECT ON devices TO classee_camera_api;
GRANT UPDATE (last_seen_at) ON devices TO classee_camera_api;

-- last_seen_at は1分ごとに変わるので記録しない。トークンのハッシュは記録に残さない
CREATE TRIGGER devices_audit
    AFTER INSERT OR UPDATE OR DELETE ON devices
    FOR EACH ROW EXECUTE FUNCTION audit_row('last_seen_at', 'token_hash');
