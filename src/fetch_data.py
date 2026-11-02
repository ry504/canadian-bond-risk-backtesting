"""Download Bank of Canada Valet yields and load them into SQLite.

Usage: python src/fetch_data.py
Writes data/raw_valet_yields.csv (exact API values) and data/yields.db.
"""
import datetime as dt
import sqlite3

import pandas as pd
import requests

import config as C


def fetch() -> pd.DataFrame:
    end = C.END_DATE or dt.date.today().isoformat()
    url = C.VALET_URL.format(ids=",".join(C.SERIES))
    r = requests.get(url, params={"start_date": C.START_DATE, "end_date": end}, timeout=60)
    r.raise_for_status()
    obs = r.json()["observations"]
    rows = []
    for o in obs:
        row = {"date": o["d"]}
        for sid in C.SERIES:
            v = o.get(sid, {}).get("v")
            row[sid] = float(v) if v not in (None, "") else None
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.rename(columns={sid: f"y{m}" for sid, m in C.SERIES.items()})


def load_sqlite(df: pd.DataFrame) -> None:
    long = df.melt(id_vars="date", var_name="tenor", value_name="yield_pct")
    long["tenor_years"] = long["tenor"].str.lstrip("y").astype(int)
    long["series_id"] = long["tenor_years"].map({m: s for s, m in C.SERIES.items()})
    long = long[["date", "series_id", "tenor_years", "yield_pct"]]
    with sqlite3.connect(C.DB_PATH) as con:
        con.execute("DROP TABLE IF EXISTS yields_raw")
        con.execute(
            """CREATE TABLE yields_raw (
                 date TEXT NOT NULL, series_id TEXT NOT NULL,
                 tenor_years INTEGER NOT NULL, yield_pct REAL,
                 PRIMARY KEY (date, series_id))"""
        )
        long.to_sql("yields_raw", con, if_exists="append", index=False)


if __name__ == "__main__":
    df = fetch()
    df.to_csv(C.RAW_CSV, index=False)
    load_sqlite(df)
    print(f"{len(df)} rows, {df.date.min()} -> {df.date.max()}")
    print("nulls per column:\n", df.isna().sum().to_string())
