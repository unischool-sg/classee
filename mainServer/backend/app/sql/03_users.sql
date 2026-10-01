-- 教職員（ログインを許可するメールアドレスの一覧を兼ねる）
-- 管理者がメールアドレスを登録し、初回の Google ログインで google_sub を記録する
CREATE TABLE users (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email               text        NOT NULL UNIQUE CHECK (email = lower(email)),
    google_sub          text        UNIQUE,                 -- 初回ログインで記録。以後は一致しないと通さない
    display_name        text,                               -- 初回ログインで Google から取る
    is_admin            boolean     NOT NULL DEFAULT false, -- 教職員・録画機の管理
    can_view_recordings boolean     NOT NULL DEFAULT false, -- 録画の閲覧
    created_at          timestamptz NOT NULL DEFAULT now(),
    disabled_at         timestamptz                         -- 退職などで無効化（セッションも切ること）
);

GRANT SELECT, INSERT, UPDATE ON users TO classee_staff_api;

CREATE TRIGGER users_audit
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_row();
