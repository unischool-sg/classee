-- 録画機に返す予定（camera の API から使う）
-- schedule_slots には確定したコマしかないので、取り消されていないかだけを見る
--
-- $1 = トークンのハッシュ
-- $2 = 範囲の開始（Unix 秒、この時刻を含む）
-- $3 = 範囲の終了（Unix 秒、この時刻を含まない）
SELECT s.id AS "classId",
       EXTRACT(EPOCH FROM s.starts_at)::bigint AS start_at,
       EXTRACT(EPOCH FROM s.ends_at)::bigint   AS end_at
FROM schedule_slots s
JOIN devices d ON d.classroom_id = s.classroom_id
WHERE d.token_hash = $1
  AND d.revoked_at IS NULL
  AND s.cancelled_at IS NULL
  AND s.starts_at >= to_timestamp($2)
  AND s.starts_at <  to_timestamp($3)
ORDER BY s.starts_at;
