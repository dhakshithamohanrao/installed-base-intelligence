-- Q3: Which warranties expire in the next 6 and 12 months? (sales opportunities)
SELECT m.machine_id, m.serial_number, m.model, c.customer_name, c.country, m.warranty_end,
       CASE WHEN m.warranty_end <= date('2026-11-01', '+6 months')
            THEN 'within 6 months' ELSE 'within 12 months' END AS expiry_window
FROM clean_machines m
JOIN clean_customers c ON c.customer_id = m.customer_id
WHERE m.warranty_end > '2026-11-01'
  AND m.warranty_end <= date('2026-11-01', '+12 months')
ORDER BY m.warranty_end;
