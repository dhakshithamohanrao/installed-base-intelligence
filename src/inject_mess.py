"""Inject deliberate data-quality problems into the synthetic source data and log what was injected."""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 44
SRC, RAW = Path("data/source"), Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(SEED)

machines = pd.read_csv(SRC / "machine_master.csv")
customers = pd.read_csv(SRC / "customers.csv")
orders = pd.read_csv(SRC / "spare_part_orders.csv")
maint = pd.read_csv(SRC / "maintenance.csv")
failures = pd.read_csv(SRC / "failures.csv")
errors = pd.read_csv(SRC / "errors.csv")
maint.insert(0, "service_id", range(1, len(maint) + 1))
orig_install = machines.set_index("machine_id")["install_date"].to_dict()

log = []
def note(rule, table, key, detail=""):
    log.append({"rule": rule, "table": table, "key": key, "detail": detail})

# 1) inconsistent country names
VARIANTS = {
    "Germany": ["DE", "Deutschland", "germany", "GERMANY "], "France": ["FR", "Frankreich", "france"],
    "Italy": ["IT", "Italien", "italy"], "Spain": ["ES", "Spanien", "spain"],
    "Poland": ["PL", "Polen", "poland"], "Netherlands": ["NL", "Niederlande", "netherlands"],
    "United States": ["US", "USA", "United States of America"], "China": ["CN", "PRC", "china"],
}
for i in customers.index:
    if rng.random() < 0.4:
        old = customers.at[i, "country"]
        new = str(rng.choice(VARIANTS[old]))
        customers.at[i, "country"] = new
        note("inconsistent_country", "customers", int(customers.at[i, "customer_id"]), f"{old} -> {new}")

# 2) machine date problems (disjoint sets of machines)
ids = [int(x) for x in rng.permutation(machines["machine_id"])]
miss_install, miss_warranty, bad_warranty, dup_ids = ids[:6], ids[6:10], ids[10:14], ids[14:20]
for mid in miss_install:
    machines.loc[machines.machine_id == mid, "install_date"] = np.nan
    note("missing_install_date", "machines", mid)
for mid in miss_warranty:
    machines.loc[machines.machine_id == mid, "warranty_end"] = np.nan
    note("missing_warranty_end", "machines", mid)
for mid in bad_warranty:
    d = pd.to_datetime(orig_install[mid]) - pd.Timedelta(days=30)
    machines.loc[machines.machine_id == mid, "warranty_end"] = d.strftime("%Y-%m-%d")
    note("warranty_before_install", "machines", mid)

# 3) duplicate serial numbers (copies get a new machine_id)
dups = machines[machines.machine_id.isin(dup_ids)].copy()
start_id = int(machines.machine_id.max()) + 1
dups["machine_id"] = range(start_id, start_id + len(dups))
for s in dups.serial_number:
    note("duplicate_serial_number", "machines", s)
machines = pd.concat([machines, dups], ignore_index=True)

# 4) maintenance problems
perm = [int(x) for x in rng.permutation(maint.index)]
neg, zero = perm[:8], perm[8:11]
early = [i for i in perm[11:] if int(maint.at[i, "machine_id"]) not in set(miss_install)][:10]
maint["datetime"] = maint["datetime"].astype(str)
for i in neg:
    maint.at[i, "cost_eur"] = -abs(maint.at[i, "cost_eur"])
    note("negative_cost", "maintenance", int(maint.at[i, "service_id"]))
for i in zero:
    maint.at[i, "cost_eur"] = 0.0
    note("zero_cost", "maintenance", int(maint.at[i, "service_id"]))
for i in early:
    inst = pd.to_datetime(orig_install[int(maint.at[i, "machine_id"])])
    maint.at[i, "datetime"] = (inst - pd.Timedelta(days=int(rng.integers(30, 400)))).strftime("%Y-%m-%d %H:%M:%S")
    note("service_before_install", "maintenance", int(maint.at[i, "service_id"]))

machines.to_csv(RAW / "machines.csv", index=False)
customers.to_csv(RAW / "customers.csv", index=False)
orders.to_csv(RAW / "spare_part_orders.csv", index=False)
maint.to_csv(RAW / "maintenance.csv", index=False)
failures.to_csv(RAW / "failures.csv", index=False)
errors.to_csv(RAW / "errors.csv", index=False)
pd.DataFrame(log).to_csv(SRC / "injection_log.csv", index=False)
print(pd.DataFrame(log).groupby("rule").size())
