"""Run every sql/*.sql file against data/yields.db and print results. Reproduces all SQL checks."""
import sqlite3
import pandas as pd
import config as C

con = sqlite3.connect(C.DB_PATH)
for f in sorted(C.SQL_DIR.glob("*.sql")):
    print(f"\n=== {f.name} ===")
    for stmt in [s.strip() for s in f.read_text().split(";") if s.strip()]:
        cur = con.execute(stmt)
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            print(pd.DataFrame(rows, columns=cols).to_string(index=False) if rows else "(no rows)")
con.commit()
