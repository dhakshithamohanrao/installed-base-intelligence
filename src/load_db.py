"""Build the SQLite database from scratch and load the raw CSVs into the raw_ layer."""
import sqlite3
from pathlib import Path
import pandas as pd

DB = Path("data/installed_base.db")
RAW = Path("data/raw")
SCHEMA = Path("sql/schema_raw.sql")

TABLES = {
    "raw_machines": "machines.csv",
    "raw_customers": "customers.csv",
    "raw_service_events": "maintenance.csv",
    "raw_failures": "failures.csv",
    "raw_errors": "errors.csv",
    "raw_spare_part_orders": "spare_part_orders.csv",
}

def load_raw(db_path=DB):
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    counts = {}
    for table, csv in TABLES.items():
        df = pd.read_csv(RAW / csv)
        df.to_sql(table, con, if_exists="append", index=False)
        counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.commit()
    con.close()
    return counts

if __name__ == "__main__":
    for t, n in load_raw().items():
        print(f"{t}: {n} rows")
