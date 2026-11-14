"""Run every query in sql/ against the clean layer, export the results, and compute the KPIs."""
import sqlite3
from pathlib import Path

import pandas as pd

import quality_checks as qc

DB = Path("data/installed_base.db")
SQL_DIR = Path("sql")
OUT = Path("reports/query_results")


def run_queries(db_path=DB, show=True):
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    results = {}
    for f in sorted(SQL_DIR.glob("q*.sql")) + [SQL_DIR / "kpis.sql"]:
        df = pd.read_sql_query(f.read_text(encoding="utf-8"), con)
        df.to_csv(OUT / f"{f.stem}.csv", index=False)
        results[f.stem] = df
        if show:
            print(f"\n=== {f.stem} ({len(df)} rows) ===")
            print(df.head(8).to_string(index=False))
    issues = qc.run_checks(con, "raw_")
    _, sizes = qc.summary(issues, con, "raw_")
    kpis = results["kpis"].iloc[0].to_dict()
    kpis["data_quality_score_pct_raw"] = qc.quality_score(issues, sizes)
    pd.DataFrame({"kpi": list(kpis), "value": list(kpis.values())}).to_csv("reports/kpis.csv", index=False)
    con.close()
    return results, kpis


if __name__ == "__main__":
    _, kpis = run_queries()
    print("\n=== KPIs ===")
    for k, v in kpis.items():
        print(f"{k}: {v}")
