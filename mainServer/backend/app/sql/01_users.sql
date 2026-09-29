CREATE TABLE users (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    login_id            text        NOT NULL UNIQUE,
    display_name        text        NOT NULL,
    password_hash       text        NOT NULL,              -- argon2 などのハッシュ
    is_admin            boolean     NOT NULL DEFAULT false, -- 教職員・録画機の管理
    can_edit_schedule   boolean     NOT NULL DEFAULT false, -- 予定の編集
    can_view_recordings boolean     NOT NULL DEFAULT false, -- 録画の閲覧
    created_at          timestamptz NOT NULL DEFAULT now(),
    disabled_at         timestamptz                         -- 退職などで無効化
);
