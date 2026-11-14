"""Installed Base Intelligence dashboard (Streamlit). Reads the clean layer of the SQLite database."""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, "src")
import quality_checks as qc

DB = Path("data/installed_base.db")
REF = pd.Timestamp("2026-11-01")
LAST_12M = pd.Timestamp("2025-11-01")

st.set_page_config(page_title="Installed Base Intelligence", layout="wide")


@st.cache_data
def load():
    con = sqlite3.connect(DB)
    m = pd.read_sql_query(
        "SELECT m.*, c.customer_name, c.country FROM clean_machines m "
        "JOIN clean_customers c ON c.customer_id = m.customer_id", con)
    f = pd.read_sql_query("SELECT * FROM clean_failures", con)
    o = pd.read_sql_query("SELECT * FROM clean_spare_part_orders", con)
    issues = qc.run_checks(con, "raw_")
    dq, sizes = qc.summary(issues, con, "raw_")
    score = qc.quality_score(issues, sizes)
    con.close()
    m["install_date"] = pd.to_datetime(m["install_date"])
    m["warranty_end"] = pd.to_datetime(m["warranty_end"])
    m["age_years"] = (REF - m["install_date"]).dt.days / 365.25
    m["out_of_warranty"] = m["warranty_end"] < REF
    f["datetime"] = pd.to_datetime(f["datetime"])
    o["order_date"] = pd.to_datetime(o["order_date"])
    return m, f, o, dq, score


m, f, o, dq, score = load()

st.title("Installed Base Intelligence")
st.caption("All data in this dashboard is synthetic and was generated for this project. "
           "Data-quality problems were injected on purpose. Reference date: 2026-11-01.")

st.sidebar.header("Filters")
countries = st.sidebar.multiselect("Country", sorted(m["country"].unique()), default=sorted(m["country"].unique()))
models = st.sidebar.multiselect("Product type (model)", sorted(m["model"].unique()), default=sorted(m["model"].unique()))

mf = m[m["country"].isin(countries) & m["model"].isin(models)]
if mf.empty:
    st.warning("No machines match the filters.")
    st.stop()
ids = set(mf["machine_id"])
ff = f[f["machine_id"].isin(ids)]
of = o[o["machine_id"].isin(ids)]

tab_over, tab_life, tab_serv, tab_mod, tab_dq = st.tabs(
    ["Overview", "Lifecycle and warranty", "Service", "Modernisation candidates", "Data quality"])

with tab_over:
    n = len(mf)
    f12 = ff[ff["datetime"] >= LAST_12M]
    c1, c2, c3 = st.columns(3)
    c1.metric("Machines", n)
    c2.metric("Average age (years)", f"{mf['age_years'].mean():.1f}")
    c3.metric("Out of warranty", f"{100 * mf['out_of_warranty'].mean():.1f}%")
    c4, c5, c6 = st.columns(3)
    c4.metric("Failures per 100 machines (last 12 months)", f"{100 * len(f12) / n:.0f}")
    c5.metric("Average downtime per failure (h)", f"{ff['downtime_hours'].mean():.1f}")
    c6.metric("Spare-part revenue per machine (EUR)", f"{of['order_value_eur'].sum() / n:,.0f}")
    left, right = st.columns(2)
    by_country = mf["country"].value_counts().rename_axis("country").reset_index(name="machines")
    left.plotly_chart(px.bar(by_country, x="country", y="machines", title="Machines by country"), width='stretch')
    by_model = mf["model"].value_counts().sort_index().rename_axis("model").reset_index(name="machines")
    right.plotly_chart(px.bar(by_model, x="model", y="machines", title="Machines by product type"), width='stretch')

with tab_life:
    bins = pd.cut(mf["age_years"], [0, 5, 10, 15, 100], right=False,
                  labels=["under 5", "5-9", "10-14", "15+"]).value_counts().sort_index()
    bins = bins.rename_axis("age bracket (years)").reset_index(name="machines")
    left, right = st.columns(2)
    left.plotly_chart(px.bar(bins, x="age bracket (years)", y="machines", title="Age distribution"), width='stretch')
    out_nc = ((mf["out_of_warranty"]) & (mf["service_contract"] == 0)).sum()
    right.metric("Out of warranty and no service contract", f"{out_nc} machines",
                 f"{100 * out_nc / len(mf):.1f}% of the filtered base", delta_color="off")
    exp = mf[(mf["warranty_end"] > REF) & (mf["warranty_end"] <= REF + pd.DateOffset(months=12))].copy()
    st.subheader("Warranties expiring in the next 12 months")
    if exp.empty:
        st.info("No warranties expire in the next 12 months for the current filters.")
    else:
        exp["month"] = exp["warranty_end"].dt.to_period("M").astype(str)
        by_month = exp.groupby("month").size().reset_index(name="machines")
        st.plotly_chart(px.bar(by_month, x="month", y="machines"), width='stretch')
        st.dataframe(exp.sort_values("warranty_end")[["machine_id", "serial_number", "model", "customer_name",
                                                       "country", "warranty_end", "service_contract"]],
                     width='stretch', hide_index=True)

with tab_serv:
    x = ff.merge(mf[["machine_id", "model", "customer_name"]], on="machine_id")
    x["year"] = x["datetime"].dt.year.astype(str)
    by_year = x.groupby(["year", "model"]).size().reset_index(name="failures")
    left, right = st.columns(2)
    left.plotly_chart(px.bar(by_year, x="year", y="failures", color="model", barmode="group",
                             title="Failures per year and model (2026 is a partial year)"), width='stretch')
    top = x.groupby("customer_name")["downtime_hours"].sum().nlargest(10).reset_index()
    right.plotly_chart(px.bar(top.sort_values("downtime_hours"), x="downtime_hours", y="customer_name",
                              orientation="h", title="Top 10 customers by downtime (hours)"), width='stretch')
    st.subheader("Repeat failures (within 90 days of the previous failure)")
    s = ff.sort_values(["machine_id", "datetime"]).copy()
    s["days_since_previous"] = s.groupby("machine_id")["datetime"].diff().dt.days
    rep = s[s["days_since_previous"] <= 90].groupby("machine_id").size().reset_index(name="repeat_failures")
    rep = rep.merge(mf[["machine_id", "serial_number", "model", "customer_name"]], on="machine_id") \
             .sort_values("repeat_failures", ascending=False).head(15)
    st.dataframe(rep, width='stretch', hide_index=True)

with tab_mod:
    st.write("Old machines with frequent failures and an expired warranty. The thresholds are assumptions "
             "that a real team would agree with Service and Sales.")
    a, b, c = st.columns(3)
    min_age = a.slider("Minimum age (years)", 5, 20, 12)
    min_fail = b.slider("Minimum failures in the last 12 months", 1, 10, 3)
    only_expired = c.checkbox("Only out of warranty", value=True)
    rec = ff[ff["datetime"] >= LAST_12M].groupby("machine_id").agg(
        failures_12m=("datetime", "size"), downtime_hours_12m=("downtime_hours", "sum")).reset_index()
    cand = mf.merge(rec, on="machine_id")
    cand = cand[(cand["age_years"] >= min_age) & (cand["failures_12m"] >= min_fail)]
    if only_expired:
        cand = cand[cand["out_of_warranty"]]
    cand = cand.sort_values(["failures_12m", "downtime_hours_12m"], ascending=False)
    st.metric("Candidates", len(cand))
    cols = ["machine_id", "serial_number", "model", "customer_name", "country", "age_years",
            "warranty_end", "service_contract", "failures_12m", "downtime_hours_12m"]
    show = cand[cols].round({"age_years": 1, "downtime_hours_12m": 1})
    st.dataframe(show, width='stretch', hide_index=True)
    st.download_button("Download as CSV", show.to_csv(index=False), "modernisation_candidates.csv")

with tab_dq:
    st.write("Measured on the raw layer, before cleaning. The problems were injected on purpose.")
    st.metric("Data-quality score (records passing all rules)", f"{score}%")
    st.plotly_chart(px.bar(dq, x="rule", y="issues", title="Issues per rule (raw layer)"), width='stretch')
    st.dataframe(dq, width='stretch', hide_index=True)
