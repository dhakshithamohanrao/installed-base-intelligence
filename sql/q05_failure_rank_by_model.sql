-- Q5: Which machines fail most within each product type? (top 3 per model, window function RANK)
WITH f AS (
    SELECT m.machine_id, m.model, COUNT(fa.machine_id) AS failures
    FROM clean_machines m
    LEFT JOIN clean_failures fa ON fa.machine_id = m.machine_id
    GROUP BY m.machine_id, m.model),
r AS (
    SELECT model, machine_id, failures,
           RANK() OVER (PARTITION BY model ORDER BY failures DESC) AS rank_in_model
    FROM f)
SELECT * FROM r WHERE rank_in_model <= 3 ORDER BY model, rank_in_model, machine_id;
