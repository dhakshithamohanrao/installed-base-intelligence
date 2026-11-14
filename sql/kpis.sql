-- KPIs (one row). The data-quality score is added in Python from the raw layer.
SELECT
  ROUND((SELECT AVG((julianday('2026-11-01') - julianday(install_date)) / 365.25) FROM clean_machines), 1)
      AS avg_installed_base_age_years,
  ROUND(100.0 * (SELECT COUNT(*) FROM clean_machines WHERE warranty_end < '2026-11-01')
      / (SELECT COUNT(*) FROM clean_machines), 1) AS pct_out_of_warranty,
  ROUND(100.0 * (SELECT COUNT(*) FROM clean_failures WHERE datetime >= '2025-11-01')
      / (SELECT COUNT(*) FROM clean_machines), 1) AS failures_per_100_machines_last_12m,
  ROUND((SELECT AVG(downtime_hours) FROM clean_failures), 1) AS avg_downtime_hours_per_failure,
  ROUND((SELECT SUM(order_value_eur) FROM clean_spare_part_orders)
      / (SELECT COUNT(*) FROM clean_machines), 0) AS spare_part_revenue_per_machine_eur;
