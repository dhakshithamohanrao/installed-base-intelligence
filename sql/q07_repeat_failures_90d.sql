-- Q7: Which machines have repeat failures (a failure within 90 days of the previous one)? Uses LAG().
WITH x AS (
    SELECT machine_id, datetime,
           LAG(datetime) OVER (PARTITION BY machine_id ORDER BY datetime) AS previous_failure
    FROM clean_failures)
SELECT machine_id, COUNT(*) AS repeat_failures_within_90d
FROM x
WHERE previous_failure IS NOT NULL
  AND julianday(datetime) - julianday(previous_failure) <= 90
GROUP BY machine_id
ORDER BY repeat_failures_within_90d DESC, machine_id
LIMIT 20;
