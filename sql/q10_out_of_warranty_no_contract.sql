-- Q10: What share of machines is out of warranty AND has no service contract? (conditional aggregation)
SELECT COUNT(*) AS machines,
       SUM(CASE WHEN warranty_end < '2026-11-01' THEN 1 ELSE 0 END) AS out_of_warranty,
       SUM(CASE WHEN warranty_end < '2026-11-01' AND service_contract = 0 THEN 1 ELSE 0 END) AS out_of_warranty_no_contract,
       ROUND(100.0 * SUM(CASE WHEN warranty_end < '2026-11-01' AND service_contract = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_of_all_machines,
       ROUND(100.0 * SUM(CASE WHEN warranty_end < '2026-11-01' AND service_contract = 0 THEN 1 ELSE 0 END)
             / SUM(CASE WHEN warranty_end < '2026-11-01' THEN 1 ELSE 0 END), 1) AS pct_of_out_of_warranty
FROM clean_machines;
