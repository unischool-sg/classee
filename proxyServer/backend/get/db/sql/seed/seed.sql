INSERT OR REPLACE INTO periods VALUES
  (1, '08:35', '09:25'),
  (2, '09:35', '10:25'),
  (3, '10:35', '11:25'),
  (4, '12:20', '13:10'),
  (5, '13:20', '14:10'),
  (6, '14:20', '15:10'),
  (7, '15:20', '16:10');

INSERT OR IGNORE INTO weekly_periods (weekday, period)
SELECT w.column1, p.period
FROM (VALUES (0, 7), (1, 6), (2, 6), (3, 7), (4, 6), (5, 4)) AS w
JOIN periods p ON p.period <= w.column2;
 