-- アプリが使う DB のロール（ログインはできない。権限は各テーブルのファイルで与える）
-- パスワード付きのログイン用ユーザーはリポジトリに入れず、サーバー上で別に作る:
--   CREATE ROLE staff_app  LOGIN PASSWORD '...' IN ROLE classee_staff_api;
--   CREATE ROLE camera_app LOGIN PASSWORD '...' IN ROLE classee_camera_api;
CREATE ROLE classee_staff_api  NOLOGIN;  -- 教職員用 API
CREATE ROLE classee_camera_api NOLOGIN;  -- 録画機用 API
