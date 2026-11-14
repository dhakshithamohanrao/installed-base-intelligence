-- Q6: Which customers have the most total downtime?
SELECT c.customer_name, c.country, COUNT(*) AS failures,
       ROUND(SUM(f.downtime_hours), 1) AS total_downtime_hours
FROM clean_failures f
JOIN clean_machines m ON m.machine_id = f.machine_id
JOIN clean_customers c ON c.customer_id = m.customer_id
GROUP BY c.customer_id
ORDER BY total_downtime_hours DESC
LIMIT 10;
