"""Generate a synthetic machine core (machines, failures, maintenance, errors).
Seeded for reproducibility. Same table shapes as the Azure PdM dataset, but ALL DATA IS SYNTHETIC."""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
N_MACHINES = 150
REF = pd.Timestamp("2026-11-01")      # "today" for the project
WINDOW_START = pd.Timestamp("2024-01-01")
OUT = Path("data/raw")

rng = np.random.default_rng(SEED)
OUT.mkdir(parents=True, exist_ok=True)

machines = pd.DataFrame({
    "machine_id": range(1, N_MACHINES + 1),
    "model": rng.choice(["model1", "model2", "model3", "model4"], N_MACHINES, p=[.2, .3, .3, .2]),
    "age": rng.integers(1, 21, N_MACHINES),            # years
})
model_factor = {"model1": 0.8, "model2": 1.0, "model3": 1.2, "model4": 1.5}

def random_dates(start, end, n):
    span = (end - start).days
    return start + pd.to_timedelta(rng.integers(0, span + 1, n), unit="D") \
                 + pd.to_timedelta(rng.integers(0, 24, n), unit="h")

failures, maint, errors = [], [], []
for m in machines.itertuples():
    # events only after the earliest possible install date (REF - age years)
    start = max(WINDOW_START, REF - pd.Timedelta(days=365 * m.age))
    years = max((REF - start).days / 365, 0.05)
    rate = (0.3 + 0.12 * m.age) * model_factor[m.model]   # older machines fail more

    n = rng.poisson(rate * years)
    for d in random_dates(start, REF, n):
        failures.append((d, m.machine_id, rng.choice(["comp1", "comp2", "comp3", "comp4"]),
                         round(float(rng.gamma(2, 3) + 1), 1)))
    n = rng.poisson(1.2 * years)
    for d in random_dates(start, REF, n):
        maint.append((d, m.machine_id, rng.choice(["comp1", "comp2", "comp3", "comp4"]),
                      round(float(rng.lognormal(6, 0.6)), 2)))
    n = rng.poisson(3 * years)
    for d in random_dates(start, REF, n):
        errors.append((d, m.machine_id, rng.choice(["error1", "error2", "error3", "error4", "error5"])))

pd.DataFrame(failures, columns=["datetime", "machine_id", "component", "downtime_hours"]).sort_values("datetime").to_csv(OUT / "failures.csv", index=False)
pd.DataFrame(maint, columns=["datetime", "machine_id", "component", "cost_eur"]).sort_values("datetime").to_csv(OUT / "maintenance.csv", index=False)
pd.DataFrame(errors, columns=["datetime", "machine_id", "error_id"]).sort_values("datetime").to_csv(OUT / "errors.csv", index=False)
machines.to_csv(OUT / "machines.csv", index=False)

for f in ["machines", "failures", "maintenance", "errors"]:
    print(f, pd.read_csv(OUT / f"{f}.csv").shape)
