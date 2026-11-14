"""Data-quality rules: one function per rule.
Every rule takes (con, prefix) and returns the offending rows as a DataFrame
with the columns: rule, table, record_id, key.
prefix is 'raw_' or 'clean_', so the same rules check both layers."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd

DB = Path("data/installed_base.db")
REPORTS = Path("reports")
LOG = Path("data/source/injection_log.csv")
CANONICAL_COUNTRIES = ["Germany", "France", "Italy", "Spain", "Poland",
                       "Netherlands", "United States", "China"]
COLUMNS = ["rule", "table", "record_id", "key"]


def to_datetime(s):
    return pd.to_datetime(s, format="mixed", errors="coerce")


def _read(con, table):
    return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY rowid", con)


def _issues(rule, table, df, id_col, key_col=None):
    key_col = key_col or id_col
    return pd.DataFrame({
        "rule": [rule] * len(df),
        "table": [table] * len(df),
        "record_id": df[id_col].astype(str).tolist(),
        "key": df[key_col].astype(str).tolist(),
    }, columns=COLUMNS)


def duplicate_serial_number(con, prefix):
    m = _read(con, prefix + "machines")
    d = m[m.duplicated("serial_number", keep="first")]
    return _issues("duplicate_serial_number", "machines", d, "machine_id", "serial_number")


def missing_install_date(con, prefix):
    m = _read(con, prefix + "machines")
    return _issues("missing_install_date", "machines", m[m["install_date"].isna()], "machine_id")


def missing_warranty_end(con, prefix):
    m = _read(con, prefix + "machines")
    return _issues("missing_warranty_end", "machines", m[m["warranty_end"].isna()], "machine_id")


def warranty_before_install(con, prefix):
    m = _read(con, prefix + "machines")
    bad = to_datetime(m["warranty_end"]) < to_datetime(m["install_date"])
    return _issues("warranty_before_install", "machines", m[bad], "machine_id")


def inconsistent_country(con, prefix):
    c = _read(con, prefix + "customers")
    return _issues("inconsistent_country", "customers",
                   c[~c["country"].isin(CANONICAL_COUNTRIES)], "customer_id")


def service_before_install(con, prefix):
    e = _read(con, prefix + "service_events")
    m = _read(con, prefix + "machines")[["machine_id", "install_date"]].drop_duplicates("machine_id")
    j = e.merge(m, on="machine_id", how="left")
    bad = to_datetime(j["datetime"]) < to_datetime(j["install_date"])
    return _issues("service_before_install", "service_events", j[bad], "service_id")


def negative_cost(con, prefix):
    e = _read(con, prefix + "service_events")
    return _issues("negative_cost", "service_events", e[e["cost_eur"] < 0], "service_id")


def zero_cost(con, prefix):
    e = _read(con, prefix + "service_events")
    return _issues("zero_cost", "service_events", e[e["cost_eur"] == 0], "service_id")


RULES = [
    ("duplicate_serial_number", "machines", duplicate_serial_number),
    ("missing_install_date", "machines", missing_install_date),
    ("missing_warranty_end", "machines", missing_warranty_end),
    ("warranty_before_install", "machines", warranty_before_install),
    ("inconsistent_country", "customers", inconsistent_country),
    ("service_before_install", "service_events", service_before_install),
    ("negative_cost", "service_events", negative_cost),
    ("zero_cost", "service_events", zero_cost),
]


def run_checks(con, prefix="raw_"):
    return pd.concat([fn(con, prefix) for _, _, fn in RULES], ignore_index=True)


def summary(issues, con, prefix="raw_"):
    sizes = {t: con.execute(f"SELECT COUNT(*) FROM {prefix}{t}").fetchone()[0]
             for t in ("machines", "customers", "service_events")}
    rows = []
    for name, table, _ in RULES:
        n = int((issues["rule"] == name).sum())
        rows.append({"rule": name, "table": table, "issues": n,
                     "pct_of_rows": round(100 * n / sizes[table], 2)})
    return pd.DataFrame(rows), sizes


def quality_score(issues, sizes):
    flagged = len(issues.drop_duplicates(["table", "record_id"]))
    return round(100 * (1 - flagged / sum(sizes.values())), 1)


def compare_with_log(issues):
    if not LOG.exists():
        return None
    log = pd.read_csv(LOG, dtype=str)
    rows = []
    for rule in sorted(set(log["rule"]) | set(issues["rule"])):
        injected = set(log.loc[log["rule"] == rule, "key"])
        found = set(issues.loc[issues["rule"] == rule, "key"])
        rows.append({"rule": rule, "injected": len(injected), "found": len(found),
                     "matched": len(injected & found), "missed": len(injected - found),
                     "unexpected": len(found - injected)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "raw_"
    con = sqlite3.connect(DB)
    issues = run_checks(con, prefix)
    summ, sizes = summary(issues, con, prefix)
    print(f"--- {prefix} layer ---")
    print(summ.to_string(index=False))
    print(f"Data-quality score: {quality_score(issues, sizes)}% of records pass all rules")
    if prefix == "raw_":
        REPORTS.mkdir(exist_ok=True)
        issues.to_csv(REPORTS / "data_quality_report.csv", index=False)
        summ.to_csv(REPORTS / "data_quality_summary.csv", index=False)
        cmp_ = compare_with_log(issues)
        if cmp_ is not None:
            print("\nChecker vs injection log:")
            print(cmp_.to_string(index=False))
    con.close()
