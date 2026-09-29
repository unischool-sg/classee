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
