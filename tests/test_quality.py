import sqlite3

import pandas as pd
import pytest

import clean
import load_db
import quality_checks as qc

LOG = pd.read_csv("data/source/injection_log.csv", dtype=str)


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    db = tmp_path_factory.mktemp("db") / "test.db"
    load_db.load_raw(db)
    clean.clean_all(db)
    c = sqlite3.connect(db)
    yield c
    c.close()


@pytest.mark.parametrize("rule", sorted(LOG["rule"].unique()))
def test_checker_finds_every_injected_issue(con, rule):
    issues = qc.run_checks(con, "raw_")
    found = set(issues.loc[issues["rule"] == rule, "key"])
    injected = set(LOG.loc[LOG["rule"] == rule, "key"])
    assert injected, "nothing was injected for this rule"
    assert found == injected


def test_raw_layer_is_untouched(con):
    bad = con.execute(
        "SELECT COUNT(*) FROM raw_customers WHERE country NOT IN ({})".format(
            ",".join("?" * len(qc.CANONICAL_COUNTRIES))), qc.CANONICAL_COUNTRIES).fetchone()[0]
    assert bad > 0


def test_clean_layer_has_no_issues(con):
    assert qc.run_checks(con, "clean_").empty


def test_no_duplicate_serials_left(con):
    n, d = con.execute("SELECT COUNT(*), COUNT(DISTINCT serial_number) FROM clean_machines").fetchone()
    assert n == d


def test_duplicates_removed_count(con):
    raw = con.execute("SELECT COUNT(*) FROM raw_machines").fetchone()[0]
    cln = con.execute("SELECT COUNT(*) FROM clean_machines").fetchone()[0]
    assert raw - cln == len(LOG[LOG["rule"] == "duplicate_serial_number"])


def test_countries_standardised(con):
    rows = con.execute("SELECT DISTINCT country FROM clean_customers").fetchall()
    assert {r[0] for r in rows} <= set(qc.CANONICAL_COUNTRIES)
