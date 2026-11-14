-- RAW layer: loaded exactly as delivered, deliberately without constraints (messy data must load).
DROP TABLE IF EXISTS raw_machines;
DROP TABLE IF EXISTS raw_customers;
DROP TABLE IF EXISTS raw_service_events;
DROP TABLE IF EXISTS raw_failures;
DROP TABLE IF EXISTS raw_errors;
DROP TABLE IF EXISTS raw_spare_part_orders;

CREATE TABLE raw_machines (
    machine_id INTEGER, serial_number TEXT, model TEXT, age INTEGER,
    customer_id INTEGER, install_date TEXT, warranty_end TEXT, service_contract INTEGER);
CREATE TABLE raw_customers (customer_id INTEGER, customer_name TEXT, country TEXT);
CREATE TABLE raw_service_events (
    service_id INTEGER, datetime TEXT, machine_id INTEGER, component TEXT, cost_eur REAL);
CREATE TABLE raw_failures (
    datetime TEXT, machine_id INTEGER, component TEXT, downtime_hours REAL);
CREATE TABLE raw_errors (datetime TEXT, machine_id INTEGER, error_id TEXT);
CREATE TABLE raw_spare_part_orders (
    order_id INTEGER, machine_id INTEGER, order_date TEXT, part_category TEXT,
    quantity INTEGER, order_value_eur REAL);
