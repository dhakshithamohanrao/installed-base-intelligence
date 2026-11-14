"""Build the clean_ layer from the raw_ layer. The raw_ layer is never modified."""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from quality_checks import run_checks, to_datetime

DB = Path("data/installed_base.db")
REF_DATE = pd.Timestamp("2026-11-01")   # reference date of the synthetic data
WARRANTY_MONTHS = 24                     # assumed standard warranty when it must be re-derived

VARIANTS = {
    "Germany": ["de", "deutschland", "germany"],
    "France": ["fr", "frankreich", "france"],
    "Italy": ["it", "italien", "italy"],
    "Spain": ["es", "spanien", "spain"],
    "Poland": ["pl", "polen", "poland"],
    "Netherlands": ["nl", "niederlande", "netherlands"],
    "United States": ["us", "usa", "united states of america", "united states"],
    "China": ["cn", "prc", "china"],
}
COUNTRY_MAP = {v: c for c, vs in VARIANTS.items() for v in vs + [c.lower()]}

DDL = """
DROP TABLE IF EXISTS clean_spare_part_orders;
DROP TABLE IF EXISTS clean_errors;
DROP TABLE IF EXISTS clean_failures;
DROP TABLE IF EXISTS clean_service_events;
DROP TABLE IF EXISTS quarantine_service_events;
DROP TABLE IF EXISTS clean_machines;
DROP TABLE IF EXISTS clean_customers;
DROP TABLE IF EXISTS country_mapping;

CREATE TABLE country_mapping (variant TEXT PRIMARY KEY, country TEXT NOT NULL);
CREATE TABLE clean_customers (
    customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL, country TEXT);
CREATE TABLE clean_machines (
    machine_id INTEGER PRIMARY KEY, serial_number TEXT NOT NULL UNIQUE, model TEXT, age INTEGER,
    customer_id INTEGER REFERENCES clean_customers(customer_id),
    install_date TEXT, warranty_end TEXT, service_contract INTEGER, dq_flags TEXT);
CREATE TABLE clean_service_events (
    service_id INTEGER PRIMARY KEY, datetime TEXT,
    machine_id INTEGER REFERENCES clean_machines(machine_id),
    component TEXT, cost_eur REAL, dq_flags TEXT);
CREATE TABLE quarantine_service_events (
    service_id INTEGER, datetime TEXT, machine_id INTEGER, component TEXT,
    cost_eur REAL, reason TEXT);
CREATE TABLE clean_failures (
    datetime TEXT, machine_id INTEGER REFERENCES clean_machines(machine_id),
    component TEXT, downtime_hours REAL);
CREATE TABLE clean_errors (
    datetime TEXT, machine_id INTEGER REFERENCES clean_machines(machine_id), error_id TEXT);
CREATE TABLE clean_spare_part_orders (
    order_id INTEGER PRIMARY KEY, machine_id INTEGER REFERENCES clean_machines(machine_id),
    order_date TEXT, part_category TEXT, quantity INTEGER, order_value_eur REAL);
"""


def _flag(flags, mask, text):
    for pos in np.flatnonzero(mask.to_numpy()):
        flags[pos].append(text)


def clean_all(db_path=DB):
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(DDL)
    stats = {}

    # customers: standardise country names with the mapping table
    pd.DataFrame(list(COUNTRY_MAP.items()), columns=["variant", "country"]) \
        .to_sql("country_mapping", con, if_exists="append", index=False)
    cust = pd.read_sql_query("SELECT * FROM raw_customers ORDER BY rowid", con)
    cust["country"] = cust["country"].str.strip().str.lower().map(COUNTRY_MAP)
    cust.to_sql("clean_customers", con, if_exists="append", index=False)
    stats["customers"] = len(cust)

    # machines: remove duplicate serials, repair or impute impossible/missing dates, flag every fix
    m = pd.read_sql_query("SELECT * FROM raw_machines ORDER BY rowid", con)
    n_raw = len(m)
    m = m.drop_duplicates("serial_number", keep="first").reset_index(drop=True)
    stats["duplicate_machines_removed"] = n_raw - len(m)
    inst = to_datetime(m["install_date"])
    ward = to_datetime(m["warranty_end"])
    flags = [[] for _ in range(len(m))]

    missing_inst = inst.isna()
    inst_fixed = inst.copy()
    inst_fixed[missing_inst] = REF_DATE - pd.to_timedelta(m.loc[missing_inst, "age"] * 365, unit="D")
    _flag(flags, missing_inst, "install_date_imputed_from_age")

    bad_ward = ward.notna() & inst.notna() & (ward < inst)
    missing_ward = ward.isna()
    fix_ward = bad_ward | missing_ward
    ward_fixed = ward.copy()
    ward_fixed[fix_ward] = inst_fixed[fix_ward] + pd.DateOffset(months=WARRANTY_MONTHS)
    _flag(flags, missing_ward, "warranty_end_imputed")
    _flag(flags, bad_ward, "warranty_end_corrected")

    m["install_date"] = inst_fixed.dt.strftime("%Y-%m-%d")
    m["warranty_end"] = ward_fixed.dt.strftime("%Y-%m-%d")
    m["dq_flags"] = [";".join(f) if f else None for f in flags]
    m[["machine_id", "serial_number", "model", "age", "customer_id", "install_date",
       "warranty_end", "service_contract", "dq_flags"]] \
        .to_sql("clean_machines", con, if_exists="append", index=False)
    stats["machines"] = len(m)
    stats["install_dates_imputed"] = int(missing_inst.sum())
    stats["warranty_ends_fixed"] = int(fix_ward.sum())

    # service events: quarantine impossible dates, null impossible costs
    ev = pd.read_sql_query("SELECT * FROM raw_service_events ORDER BY rowid", con)
    inst_map = dict(zip(m["machine_id"], to_datetime(m["install_date"])))
    before = to_datetime(ev["datetime"]) < pd.to_datetime(ev["machine_id"].map(inst_map))
    quarantine = ev[before].assign(reason="service_before_install")
    quarantine.to_sql("quarantine_service_events", con, if_exists="append", index=False)
    keep = ev[~before].copy()
    keep["dq_flags"] = None
    neg = keep["cost_eur"] < 0
    zero = keep["cost_eur"] == 0
    keep.loc[neg, "dq_flags"] = "negative_cost_nulled"
    keep.loc[zero, "dq_flags"] = "zero_cost_nulled"
    keep.loc[neg | zero, "cost_eur"] = np.nan
    keep.to_sql("clean_service_events", con, if_exists="append", index=False)
    stats["service_events_kept"] = len(keep)
    stats["service_events_quarantined"] = len(quarantine)
    stats["costs_nulled"] = int((neg | zero).sum())

    # remaining tables: copy, keeping only rows whose machine exists in the clean master
    ok = set(m["machine_id"])
    for name in ("failures", "errors", "spare_part_orders"):
        df = pd.read_sql_query(f"SELECT * FROM raw_{name} ORDER BY rowid", con)
        df = df[df["machine_id"].isin(ok)]
        df.to_sql(f"clean_{name}", con, if_exists="append", index=False)
        stats[name] = len(df)

    con.commit()
    con.close()
    return stats


if __name__ == "__main__":
    for k, v in clean_all().items():
        print(f"{k}: {v}")
    con = sqlite3.connect(DB)
    print("issues left in clean layer:", len(run_checks(con, "clean_")))
    con.close()
