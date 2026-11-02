"""End-to-end analysis: SQLite -> P&L -> VaR -> backtests -> stress tests -> CSVs + SQLite result tables."""
import sqlite3
import numpy as np
import pandas as pd
import config as C
import risk

con = sqlite3.connect(C.DB_PATH)
for f in ["02_clean_yields.sql", "03_daily_changes.sql"]:
    con.executescript((C.SQL_DIR / f).read_text())
yld = pd.read_sql("SELECT date,y2,y5,y10 FROM yields_wide ORDER BY date", con, parse_dates=["date"]).set_index("date")

pnl = risk.daily_pnl(yld)
bt = risk.backtest_frame(pnl["pnl"])
daily = pnl.join(bt[["var", "breach"]], how="left")
daily = daily.join(yld)
daily["year"] = daily.index.year

# --- backtest by period
rows = [risk.summarize(bt, "All tested days")]
for y, g in bt.groupby(bt.index.year):
    rows.append(risk.summarize(g, str(y)))
rows.append(risk.summarize(bt[bt.index.year == 2022], "2022"))
rows.append(risk.summarize(bt[bt.index.year != 2022], "All other years (ex-2022)"))
summary = pd.DataFrame(rows).drop_duplicates("period", keep="last")

# --- sensitivity: window / confidence
sens = []
for w in (250, 500):
    for cf in (0.99, 0.975):
        b = risk.backtest_frame(pnl["pnl"], w, cf)
        for lab, sub in (("2022", b[b.index.year == 2022]), ("ex-2022", b[b.index.year != 2022])):
            s = risk.summarize(sub, lab)
            sens.append({"window": w, "confidence": cf, "period": lab, "obs": s["obs"], "breaches": s["breaches"],
                         "breach_rate_pct": s["breach_rate_pct"], "expected_rate_pct": 100 * (1 - cf)})
sens = pd.DataFrame(sens)

# --- 2022 diagnostics: VaR forecast vs realised distribution
b22 = bt[bt.index.year == 2022]
diag = {
    "var_first_day_2022": b22["var"].iloc[0], "var_last_day_2022": b22["var"].iloc[-1],
    "var_avg_2022": b22["var"].mean(),
    "realised_99pct_loss_2022": -np.quantile(b22["pnl"], 0.01),
    "realised_vol_2022_cad": b22["pnl"].std(),
    "pre_2022_vol_cad": pnl.loc["2021-01-01":"2021-12-31", "pnl"].std(),
    "cum_pnl_2022_cad": b22["pnl"].sum(),
}
diag["realised_over_forecast"] = diag["realised_99pct_loss_2022"] / diag["var_avg_2022"]

# --- stress tests
S = []
y_end = lambda d: {m: float(yld.loc[:d, f"y{m}"].iloc[-1]) for m in risk.TENORS}
latest = y_end(yld.index[-1])
hyp = {
    "Hypothetical: +100bp parallel": {2: 100, 5: 100, 10: 100},
    "Hypothetical: +200bp parallel": {2: 200, 5: 200, 10: 200},
    "Hypothetical: -100bp parallel": {2: -100, 5: -100, 10: -100},
    "Hypothetical: bear flattener (+150/+125/+100)": {2: 150, 5: 125, 10: 100},
    "Hypothetical: bull steepener (-100/-60/-30)": {2: -100, 5: -60, 10: -30},
}
for name, sh in hyp.items():
    r = risk.reprice(latest, sh)
    S.append({"scenario": name, "type": "hypothetical", "start": str(yld.index[-1].date()), **{f"shock{m}_bp": sh[m] for m in risk.TENORS},
              "pnl_cad": r["total"], "pnl_pct": 100 * r["total"] / C.PORTFOLIO_VALUE})
# historical replays (real yield moves, applied to the starting-date yields via full revaluation)
def replay(name, d0, d1):
    y0, y1 = y_end(d0), y_end(d1)
    sh = {m: round((y1[m] - y0[m]) * 100, 1) for m in risk.TENORS}
    r = risk.reprice(y0, sh)
    S.append({"scenario": name, "type": "historical replay", "start": d0, **{f"shock{m}_bp": sh[m] for m in risk.TENORS},
              "pnl_cad": r["total"], "pnl_pct": 100 * r["total"] / C.PORTFOLIO_VALUE})
replay("2022 calendar year (31-Dec-21 -> 30-Dec-22)", "2021-12-31", "2022-12-31")
# worst rolling 10-business-day and 60-day windows of the simulated P&L in the sample
for h in (10, 60):
    roll = pnl["pnl"].rolling(h).sum()
    end = roll.idxmin()
    start = pnl.index[pnl.index.get_loc(end) - h]
    replay(f"Worst {h}-day window in sample ({start.date()} -> {end.date()})", str(start.date()), str(end.date()))
stress = pd.DataFrame(S)

# --- write outputs
daily_out = daily.reset_index().rename(columns={"index": "date"})
daily_out["date"] = daily_out["date"].dt.strftime("%Y-%m-%d")
daily_out["breach"] = daily_out["breach"].map({True: 1, False: 0})
daily_out.to_csv(C.OUT_DIR / "daily_results.csv", index=False)
summary.to_csv(C.OUT_DIR / "backtest_summary.csv", index=False)
sens.to_csv(C.OUT_DIR / "sensitivity.csv", index=False)
stress.to_csv(C.OUT_DIR / "stress_tests.csv", index=False)
pd.Series(diag).to_csv(C.OUT_DIR / "diagnostics_2022.csv", header=["value"])
breaches = daily_out[daily_out["breach"] == 1][["date", "pnl", "var"]]
breaches.to_csv(C.OUT_DIR / "breach_list.csv", index=False)
for name, df in (("daily_results", daily_out), ("backtest_summary", summary), ("stress_tests", stress), ("sensitivity", sens)):
    df.to_sql(name, con, if_exists="replace", index=False)
con.commit()

pd.set_option("display.width", 250, "display.float_format", lambda v: f"{v:,.3f}")
print(summary.to_string(index=False)); print(); print(sens.to_string(index=False)); print()
print(pd.Series(diag).to_string()); print(); print(stress.to_string(index=False)); print()
print(breaches.assign(year=breaches.date.str[:4]).groupby("year").size().to_string())
print(f"\nPortfolio duration range: {pnl['port_dur'].min():.2f} - {pnl['port_dur'].max():.2f}; first VaR date {bt.index[0].date()}")
