-- Q9: Modernisation candidates: 12+ years old, warranty expired, 3+ failures in the last 12 months.
-- Thresholds are assumptions for the demo; a real team would agree them with Service and Sales.
WITH recent AS (
    SELECT machine_id, COUNT(*) AS failures_12m, ROUND(SUM(downtime_hours), 1) AS downtime_hours_12m
    FROM clean_failures
    WHERE datetime >= '2025-11-01'
    GROUP BY machine_id)
SELECT m.machine_id, m.serial_number, m.model, c.customer_name, c.country,
       ROUND((julianday('2026-11-01') - julianday(m.install_date)) / 365.25, 1) AS age_years,
       m.warranty_end, m.service_contract, r.failures_12m, r.downtime_hours_12m
FROM clean_machines m
JOIN clean_customers c ON c.customer_id = m.customer_id
JOIN recent r ON r.machine_id = m.machine_id
WHERE julianday('2026-11-01') - julianday(m.install_date) >= 12 * 365.25
  AND m.warranty_end < '2026-11-01'
  AND r.failures_12m >= 3
ORDER BY r.failures_12m DESC, r.downtime_hours_12m DESC;
