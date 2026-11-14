# Pipeline run summary

Run time: 2026-11-14 16:49:17

All data is synthetic (generated). Data-quality problems were injected on purpose.

## Rows loaded (raw layer)

| table | rows |
|---|---|
| raw_machines | 156 |
| raw_customers | 30 |
| raw_service_events | 499 |
| raw_failures | 715 |
| raw_errors | 1197 |
| raw_spare_part_orders | 389 |

## Data quality (raw layer)

Data-quality score: **92.6%**

| rule | table | issues | pct_of_rows |
|---|---|---|---|
| duplicate_serial_number | machines | 6 | 3.85 |
| missing_install_date | machines | 6 | 3.85 |
| missing_warranty_end | machines | 4 | 2.56 |
| warranty_before_install | machines | 4 | 2.56 |
| inconsistent_country | customers | 10 | 33.33 |
| service_before_install | service_events | 10 | 2.0 |
| negative_cost | service_events | 8 | 1.6 |
| zero_cost | service_events | 3 | 0.6 |

## Cleaning

| step | count |
|---|---|
| customers | 30 |
| duplicate_machines_removed | 6 |
| machines | 150 |
| install_dates_imputed | 6 |
| warranty_ends_fixed | 8 |
| service_events_kept | 489 |
| service_events_quarantined | 10 |
| costs_nulled | 11 |
| failures | 715 |
| errors | 1197 |
| spare_part_orders | 389 |

Issues left in clean layer: **0** (score 100.0%)

## KPIs

| kpi | value |
|---|---|
| avg_installed_base_age_years | 10.7 |
| pct_out_of_warranty | 93.3 |
| failures_per_100_machines_last_12m | 165.3 |
| avg_downtime_hours_per_failure | 7.1 |
| spare_part_revenue_per_machine_eur | 4257.0 |
| data_quality_score_pct_raw | 92.6 |
