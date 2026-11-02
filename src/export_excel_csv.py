"""Flatten output/*.csv into the five comma-safe CSVs in excel/ that the dashboard's VBA refresh button loads."""
import numpy as np
import pandas as pd
import config as C

X = C.ROOT / "excel"; X.mkdir(exist_ok=True)
d = pd.read_csv(C.OUT_DIR / "daily_results.csv")
d["neg_var"] = -d["var"]
d["breach_pnl"] = np.where(d["breach"] == 1, d["pnl"], np.nan)
cols = ["date", "year", "pnl", "var", "neg_var", "breach", "breach_pnl", "port_dur", "y10"]
d = d[cols].round({"pnl": 0, "var": 0, "neg_var": 0, "breach_pnl": 0, "port_dur": 3, "y10": 2})
d["breach"] = d["breach"].astype("Int64")  # blank where no VaR yet
d.to_csv(X / "daily.csv", index=False)
d[d.year == 2022][["date", "pnl", "neg_var", "breach_pnl"]].to_csv(X / "y2022.csv", index=False)

s = pd.read_csv(C.OUT_DIR / "backtest_summary.csv")
s["period"] = s["period"].map(lambda p: f"Year {p}" if p.isdigit() else {"All other years (ex-2022)": "Ex-2022 (2020-26)"}.get(p, p))
s = s[["period", "obs", "breaches", "expected_breaches", "breach_rate_pct", "kupiec_p", "christoffersen_ind_p",
       "avg_var_cad", "worst_loss_cad", "avg_breach_loss_over_var"]].round(4)
s.to_csv(X / "summary.csv", index=False)

st = pd.read_csv(C.OUT_DIR / "stress_tests.csv")
st["scenario"] = st["scenario"].str.replace(",", ";")
st[["scenario", "type", "shock2_bp", "shock5_bp", "shock10_bp", "pnl_cad", "pnl_pct"]].round(2).to_csv(X / "stress.csv", index=False)

b = pd.read_csv(C.OUT_DIR / "breach_list.csv")
b = b[b.date.str.startswith("2022")].copy()
b["loss"] = -b["pnl"]; b["loss_over_var"] = b["loss"] / b["var"]
b[["date", "loss", "var", "loss_over_var"]].round({"loss": 0, "var": 0, "loss_over_var": 3}).to_csv(X / "breaches2022.csv", index=False)
print("exported:", sorted(p.name for p in X.glob("*.csv")))
