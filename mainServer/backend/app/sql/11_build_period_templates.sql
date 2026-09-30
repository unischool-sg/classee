CREATE OR REPLACE FUNCTION build_period_templates(p_classroom_id bigint)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_missing text;
    v_count   integer;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM classrooms WHERE id = p_classroom_id) THEN
        RAISE EXCEPTION '教室 % は存在しません', p_classroom_id;
    END IF;

    -- 必要な時限のチャイムの時刻が全部そろっているか
    SELECT string_agg(format('曜日%s の %s限', c.weekday, p.period), ', '
                      ORDER BY c.weekday, p.period)
    INTO v_missing
    FROM classroom_period_counts c
    CROSS JOIN LATERAL generate_series(1, c.periods) AS p(period)
    LEFT JOIN bell_times b ON b.weekday = c.weekday AND b.period = p.period
    WHERE c.classroom_id = p_classroom_id
      AND b.period IS NULL;

    IF v_missing IS NOT NULL THEN
        RAISE EXCEPTION 'bell_times に時刻がない時限があります: %', v_missing;
    END IF;

    DELETE FROM period_templates WHERE classroom_id = p_classroom_id;

    INSERT INTO period_templates (classroom_id, weekday, period, start_time, end_time)
    SELECT c.classroom_id, b.weekday, b.period, b.start_time, b.end_time
    FROM classroom_period_counts c
    JOIN bell_times b ON b.weekday = c.weekday AND b.period <= c.periods
    WHERE c.classroom_id = p_classroom_id
      AND NOT EXISTS (
          SELECT 1 FROM classroom_skips s
          WHERE s.classroom_id = c.classroom_id
            AND s.weekday = b.weekday
            AND s.period = b.period
      );

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;
