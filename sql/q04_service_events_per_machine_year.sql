-- Q4: How many service events does each machine have per year?
SELECT m.model, e.machine_id, substr(e.datetime, 1, 4) AS year, COUNT(*) AS service_events
FROM clean_service_events e
JOIN clean_machines m ON m.machine_id = e.machine_id
GROUP BY m.model, e.machine_id, year
ORDER BY e.machine_id, year;
