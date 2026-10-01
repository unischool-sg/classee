-- 操作記録: 誰がいつ何をしたか
-- 各テーブルの追加・変更・削除は、そのテーブルのトリガーが audit_row() で自動で書く
-- 録画の閲覧など、読み取りの記録だけはアプリが直接書く
--
-- 誰が操作したかは、アプリがトランザクションの最初に次のどれかを渡す:
--   SELECT set_config('app.user_id',   '5',       true);  -- 教職員用 API（先生の users.id）
--   SELECT set_config('app.device_id', '3',       true);  -- 録画機用 API（devices.id）
--   SELECT set_config('app.actor',     'cleanup', true);  -- 定期実行のスクリプトや、管理者の手作業
-- どれも渡されていなければ、記録の対象のテーブルは変更できない

CREATE TABLE audit_logs (
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at      timestamptz NOT NULL DEFAULT now(),
    -- 記録は元の行が変わっても残すものなので、外部キーにはしない
    actor_user_id    bigint,
    actor_device_id  bigint,
    actor_system     text,
    action           text        NOT NULL,  -- 例: 'schedule_slots.insert', 'recordings.view'
    target_table     text        NOT NULL,
    target_id        text,                  -- 対象の行の id（id 列がないテーブルは NULL）
    detail           jsonb       NOT NULL DEFAULT '{}',  -- 変更前（old）と変更後（new）の行
    CHECK (num_nonnulls(actor_user_id, actor_device_id, actor_system) >= 1)
);

CREATE INDEX audit_logs_occurred_at_idx ON audit_logs (occurred_at);
CREATE INDEX audit_logs_target_idx ON audit_logs (target_table, target_id);

-- 記録は足すだけ。書き換え・削除はどちらのロールにもさせない
GRANT SELECT, INSERT ON audit_logs TO classee_staff_api;
GRANT INSERT ON audit_logs TO classee_camera_api;

-- 共通のトリガー関数
--   引数1: 変わっても記録しない列（カンマ区切り）。例: 'last_seen_at'
--   引数2: 記録に値を残さない列（カンマ区切り）。例: 'token_hash'
CREATE FUNCTION audit_row() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_user    bigint := nullif(current_setting('app.user_id', true), '')::bigint;
    v_device  bigint := nullif(current_setting('app.device_id', true), '')::bigint;
    v_system  text   := nullif(current_setting('app.actor', true), '');
    v_ignore  text[] := string_to_array(coalesce(TG_ARGV[0], ''), ',');
    v_redact  text[] := string_to_array(coalesce(TG_ARGV[1], ''), ',');
    v_old     jsonb  := CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END;
    v_new     jsonb  := CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END;
BEGIN
    IF num_nonnulls(v_user, v_device, v_system) = 0 THEN
        RAISE EXCEPTION '操作した人が設定されていないので、% は変更できません（app.user_id などを設定すること）',
            TG_TABLE_NAME;
    END IF;

    -- 記録しない列だけが変わった更新は、記録しない
    IF TG_OP = 'UPDATE' AND (v_old - v_ignore) = (v_new - v_ignore) THEN
        RETURN NULL;
    END IF;

    INSERT INTO audit_logs (actor_user_id, actor_device_id, actor_system,
                            action, target_table, target_id, detail)
    VALUES (v_user, v_device, v_system,
            TG_TABLE_NAME || '.' || lower(TG_OP),
            TG_TABLE_NAME,
            coalesce(v_new, v_old) ->> 'id',
            jsonb_build_object('old', v_old - v_redact, 'new', v_new - v_redact));
    RETURN NULL;
END;
$$;
