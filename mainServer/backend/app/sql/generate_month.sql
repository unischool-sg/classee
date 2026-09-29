INSERT INTO schedule_slots (classroom_id, period, starts_at, ends_at)
SELECT t.classroom_id, t.period,
       (day.d + t.start_time) AT TIME ZONE 'Asia/Tokyo',
       (day.d + t.end_time)   AT TIME ZONE 'Asia/Tokyo'
FROM generate_series(:'month'::date,
                     :'month'::date + interval '1 month' - interval '1 day',
                     interval '1 day') AS g(ts)
CROSS JOIN LATERAL (SELECT g.ts::date AS d) AS day
JOIN period_templates t ON t.weekday = EXTRACT(ISODOW FROM day.d)
WHERE t.classroom_id = :classroom_id
ON CONFLICT DO NOTHING;
