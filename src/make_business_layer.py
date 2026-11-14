"""Synthetic business layer: customers, machine master data, spare-part orders. ALL SYNTHETIC."""
from pathlib import Path
import numpy as np
import pandas as pd
from faker import Faker

SEED = 43
REF = pd.Timestamp("2026-11-01")
WINDOW_START = pd.Timestamp("2024-01-01")
SRC = Path("data/source")

rng = np.random.default_rng(SEED)
Faker.seed(SEED)
fake = Faker("en_US")

machines = pd.read_csv(SRC / "machines.csv")

COUNTRIES = ["Germany", "France", "Italy", "Spain", "Poland", "Netherlands", "United States", "China"]
C_P = [.30, .12, .10, .08, .10, .08, .12, .10]
N_CUST = 30
customers = pd.DataFrame({
    "customer_id": range(1, N_CUST + 1),
    "customer_name": [fake.unique.company() for _ in range(N_CUST)],
    "country": rng.choice(COUNTRIES, N_CUST, p=C_P),
})
cust_w = rng.dirichlet(np.ones(N_CUST))

mm = machines.copy()
mm["serial_number"] = [f"SN-{i:05d}" for i in mm["machine_id"]]
mm["customer_id"] = rng.choice(customers["customer_id"], len(mm), p=cust_w)
mm["install_date"] = [REF - pd.Timedelta(days=int(a) * 365 + int(rng.integers(0, 365))) for a in mm["age"]]
months = rng.choice([24, 36], len(mm), p=[.6, .4])
mm["warranty_end"] = [d + pd.DateOffset(months=int(m)) for d, m in zip(mm["install_date"], months)]
mm["service_contract"] = (rng.random(len(mm)) < 0.45).astype(int)

PRICE = {"filter": 80, "bearing": 150, "sensor": 220, "motor": 900, "seal": 40}
rows = []
for m in mm.itertuples():
    start = max(WINDOW_START, m.install_date)
    span = (REF - start).days
    n = rng.poisson(0.9 * span / 365)
    for _ in range(n):
        cat = str(rng.choice(list(PRICE)))
        qty = int(rng.integers(1, 11))
        d = start + pd.Timedelta(days=int(rng.integers(0, span + 1)))
        rows.append((m.machine_id, d.strftime("%Y-%m-%d"), cat, qty,
                     round(qty * PRICE[cat] * float(rng.lognormal(0, 0.2)), 2)))
orders = pd.DataFrame(rows, columns=["machine_id", "order_date", "part_category", "quantity", "order_value_eur"])
orders = orders.sort_values("order_date").reset_index(drop=True)
orders.insert(0, "order_id", range(1, len(orders) + 1))

mm["install_date"] = mm["install_date"].dt.strftime("%Y-%m-%d")
mm["warranty_end"] = mm["warranty_end"].dt.strftime("%Y-%m-%d")

customers.to_csv(SRC / "customers.csv", index=False)
mm[["machine_id", "serial_number", "model", "age", "customer_id", "install_date",
    "warranty_end", "service_contract"]].to_csv(SRC / "machine_master.csv", index=False)
orders.to_csv(SRC / "spare_part_orders.csv", index=False)

print("customers", customers.shape, "| machine_master", mm.shape, "| spare_part_orders", orders.shape)
