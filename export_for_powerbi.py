import glob, sqlite3, os
import pandas as pd

dbs = glob.glob("**/*.db", recursive=True)
print("Databases found:", dbs)
con = sqlite3.connect(dbs[0])
os.makedirs("powerbi/data", exist_ok=True)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
for t in tables:
    if t.startswith("raw_"):
        continue
    df = pd.read_sql(f"SELECT * FROM {t}", con)
    df.to_csv(f"powerbi/data/{t}.csv", index=False)
    print(t, len(df), list(df.columns))