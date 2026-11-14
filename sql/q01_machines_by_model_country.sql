-- Q1: How many machines do we have by product type (model) and country?
SELECT c.country, m.model, COUNT(*) AS machines
FROM clean_machines m
JOIN clean_customers c ON c.customer_id = m.customer_id
GROUP BY c.country, m.model
ORDER BY c.country, m.model;
