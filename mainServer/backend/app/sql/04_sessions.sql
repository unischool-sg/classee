-- ログイン中のセッション
CREATE TABLE sessions (
    token_hash  text        PRIMARY KEY,                    -- セッショントークンのハッシュ
    user_id     bigint      NOT NULL REFERENCES users(id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz                                 -- ログアウト・強制ログアウト
);

CREATE INDEX sessions_user_id_idx ON sessions (user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON sessions TO classee_staff_api;

-- ログインとログアウトを記録する。トークンのハッシュは記録に残さない
CREATE TRIGGER sessions_audit
    AFTER INSERT OR UPDATE OR DELETE ON sessions
    FOR EACH ROW EXECUTE FUNCTION audit_row('', 'token_hash');
