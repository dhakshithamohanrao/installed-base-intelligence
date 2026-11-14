# Data dictionary

All data is synthetic. Raw tables are loaded as delivered (with problems); clean tables have keys and repaired values.

## Customers (raw_customers, clean_customers)
| Column | Meaning |
|---|---|
| customer_id | Customer key (clean layer: primary key) |
| customer_name | Generated company name |
| country | Country. Raw has variants such as DE, Deutschland, germany; clean has eight standard names |

## Machines (raw_machines, clean_machines)
| Column | Meaning |
|---|---|
| machine_id | Machine key (clean layer: primary key) |
| serial_number | Machine serial number (clean layer: unique). Raw has duplicate serials |
| model | Product type: model1 to model4 |
| age | Machine age in years at the reference date |
| customer_id | Owner (clean layer: foreign key to customers) |
| install_date | Installation date. Raw has missing values; clean derives them from age |
| warranty_end | End of warranty. Raw has missing values and dates before installation; clean re-derives them |
| service_contract | 1 if a service contract exists, otherwise 0 |
| dq_flags | Clean layer only: what was repaired for this record |

## Service events (raw_service_events, clean_service_events, quarantine_service_events)
| Column | Meaning |
|---|---|
| service_id | Service event key |
| datetime | Time of the event |
| machine_id | Machine serviced |
| component | Component worked on (comp1 to comp4) |
| cost_eur | Cost in EUR. Raw has negative and zero values; clean sets them to NULL |
| dq_flags | Clean layer only: what was repaired |
| reason | Quarantine table only: why the event was set aside |

## Failures (raw_failures, clean_failures)
| Column | Meaning |
|---|---|
| datetime | Time of failure |
| machine_id | Machine that failed |
| component | Failed component |
| downtime_hours | Hours of downtime caused by the failure |

## Errors (raw_errors, clean_errors)
| Column | Meaning |
|---|---|
| datetime | Time of the error message |
| machine_id | Machine |
| error_id | Error code (error1 to error5) |

## Spare-part orders (raw_spare_part_orders, clean_spare_part_orders)
| Column | Meaning |
|---|---|
| order_id | Order key |
| machine_id | Machine the part was ordered for |
| order_date | Date of the order |
| part_category | filter, bearing, sensor, motor or seal |
| quantity | Number of parts |
| order_value_eur | Order value in EUR |

## Other tables
| Table | Meaning |
|---|---|
| country_mapping | Variant spelling to standard country name, used in cleaning |

## Glossary
| Term | Meaning |
|---|---|
| Installed base | All machines and systems delivered to customers and still in use |
| Asset lifecycle | Installation, operation, service, upgrade or modernisation, end of life |
| Warranty / service contract | Defines who pays for repairs and service, and for how long. Expiry dates trigger sales opportunities |
| Master data | Core descriptive records (machine, customer, product). Poor master data breaks every report |
| ETL | Extract, transform, load: moving data from sources, fixing it, and storing it in a target database |
| KPI | A number that tracks performance, such as average installed-base age |
