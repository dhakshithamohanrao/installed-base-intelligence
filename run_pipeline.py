"""run_pipeline.py - rebuild everything from the raw files with one command.

Usage:  python run_pipeline.py                 (uses data/raw as it is)
        python run_pipeline.py --regenerate    (also regenerates the synthetic source + messy raw data)
"""
import argparse
import logging
import os
import runpy
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

import clean
import load_db
import quality_checks as qc
import run_queries

LOG_FILE = Path("logs/pipeline.log")
REPORTS = Path("reports")
GENERATORS = ["make_machine_core.py", "make_business_layer.py", "inject_mess.py"]


def setup_logging():
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("pipeline")


def md_table(df):
    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "---|" * len(df.columns)
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def step_generate(ctx, log):
    for script in GENERATORS:
        runpy.run_path(f"src/{script}", run_name="__main__")
        log.info("generated with %s", script)


def step_load(ctx, log):
    counts = load_db.load_raw()
    for table, n in counts.items():
        log.info("loaded %s: %d rows", table, n)
    ctx["load_counts"] = counts


def step_quality(ctx, log):
    con = sqlite3.connect(load_db.DB)
    issues = qc.run_checks(con, "raw_")
    summ, sizes = qc.summary(issues, con, "raw_")
    con.close()
    REPORTS.mkdir(exist_ok=True)
    issues.to_csv(REPORTS / "data_quality_report.csv", index=False)
    summ.to_csv(REPORTS / "data_quality_summary.csv", index=False)
    for r in summ.itertuples():
        log.info("quality rule %s: %d issues (%.2f%% of %s rows)", r.rule, r.issues, r.pct_of_rows, r.table)
    ctx["dq"] = summ
    ctx["score_raw"] = qc.quality_score(issues, sizes)
    log.info("data-quality score (raw layer): %s%%", ctx["score_raw"])
    cmp_ = qc.compare_with_log(issues)
    if cmp_ is not None and (cmp_["missed"].sum() or cmp_["unexpected"].sum()):
        log.warning("checker output differs from the injection log:\n%s", cmp_.to_string(index=False))


def step_clean(ctx, log):
    stats = clean.clean_all()
    for k, v in stats.items():
        log.info("clean %s: %s", k, v)
    ctx["clean_stats"] = stats


def step_verify(ctx, log):
    con = sqlite3.connect(load_db.DB)
    left = qc.run_checks(con, "clean_")
    summ, sizes = qc.summary(left, con, "clean_")
    con.close()
    ctx["issues_left"] = len(left)
    ctx["score_clean"] = qc.quality_score(left, sizes)
    log.info("issues left in clean layer: %d (score %s%%)", len(left), ctx["score_clean"])
    if len(left):
        raise RuntimeError(f"{len(left)} quality issues remain in the clean layer")


def step_kpis(ctx, log):
    results, kpis = run_queries.run_queries(show=False)
    for name, df in results.items():
        log.info("query %s: %d rows", name, len(df))
    for k, v in kpis.items():
        log.info("KPI %s = %s", k, v)
    ctx["kpis"] = kpis


def step_report(ctx, log):
    lines = [
        "# Pipeline run summary", "",
        f"Run time: {datetime.now():%Y-%m-%d %H:%M:%S}", "",
        "All data is synthetic (generated). Data-quality problems were injected on purpose.", "",
        "## Rows loaded (raw layer)", "",
        md_table(pd.DataFrame(list(ctx["load_counts"].items()), columns=["table", "rows"])), "",
        "## Data quality (raw layer)", "",
        f"Data-quality score: **{ctx['score_raw']}%**", "", md_table(ctx["dq"]), "",
        "## Cleaning", "",
        md_table(pd.DataFrame(list(ctx["clean_stats"].items()), columns=["step", "count"])), "",
        f"Issues left in clean layer: **{ctx['issues_left']}** (score {ctx['score_clean']}%)", "",
        "## KPIs", "",
        md_table(pd.DataFrame(list(ctx["kpis"].items()), columns=["kpi", "value"])),
    ]
    (REPORTS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("summary report written to reports/summary.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerate", action="store_true",
                    help="regenerate synthetic source data and the messy raw files first")
    args = ap.parse_args()
    log = setup_logging()
    steps = [("load raw files into SQLite", step_load), ("data-quality checks", step_quality),
             ("cleaning", step_clean), ("verify clean layer", step_verify),
             ("SQL queries and KPIs", step_kpis), ("summary report", step_report)]
    if args.regenerate or not Path("data/raw/machines.csv").exists():
        steps.insert(0, ("generate synthetic data", step_generate))
    ctx, t0 = {}, time.time()
    log.info("=== pipeline start ===")
    for name, fn in steps:
        log.info("STEP START: %s", name)
        t = time.time()
        try:
            fn(ctx, log)
        except Exception:
            log.exception("STEP FAILED: %s", name)
            log.error("pipeline stopped")
            sys.exit(1)
        log.info("STEP OK: %s (%.1fs)", name, time.time() - t)
    log.info("=== pipeline finished in %.1fs ===", time.time() - t0)


if __name__ == "__main__":
    main()
