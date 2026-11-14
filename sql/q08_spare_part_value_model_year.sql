-- Q8: How much spare-part order value do we have per product type and year?
SELECT m.model, substr(o.order_date, 1, 4) AS year,
       COUNT(*) AS orders, ROUND(SUM(o.order_value_eur), 2) AS order_value_eur
FROM clean_spare_part_orders o
JOIN clean_machines m ON m.machine_id = o.machine_id
GROUP BY m.model, year
ORDER BY m.model, year;
