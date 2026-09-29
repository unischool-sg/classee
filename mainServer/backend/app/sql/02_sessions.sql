CREATE TABLE sessions (
    token_hash  text        PRIMARY KEY,                    -- セッショントークンのハッシュ
    user_id     bigint      NOT NULL REFERENCES users(id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    revoked_at  timestamptz                                 -- ログアウト・強制ログアウト
);

CREATE INDEX sessions_user_id_idx ON sessions (user_id);
