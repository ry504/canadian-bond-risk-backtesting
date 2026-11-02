"""Static charts (PNG) from output/*.csv. Simulated portfolio P&L only - not actual bank losses."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import config as C

NAVY, RED, GREY, BLUE = "#1f3a5f", "#c0392b", "#8a94a0", "#2e7bb4"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "axes.titleweight": "bold", "axes.titlesize": 12,
                     "figure.dpi": 150})
CH = C.OUT_DIR / "charts"; CH.mkdir(exist_ok=True)
d = pd.read_csv(C.OUT_DIR / "daily_results.csv", parse_dates=["date"]).set_index("date")
t = d.dropna(subset=["var"]).copy()
t["breach"] = t["breach"].astype(bool)
M = lambda v, _=None: f"{v/1e6:.1f}"
NOTE = "Simulated C$100M GoC bond portfolio (2/5/10y, equal weights); not actual bank trading losses. Source: Bank of Canada Valet."


def finish(fig, ax, name, title, ylabel="C$ millions"):
    ax.set_title(title, loc="left"); ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(M))
    fig.text(0.01, 0.005, NOTE, fontsize=6.5, color=GREY)
    fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(CH / name); plt.close(fig)


# 1. Full sample
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(t.index, t["pnl"], width=1.2, color=GREY, alpha=0.8, label="Daily simulated P&L")
ax.plot(t.index, -t["var"], color=NAVY, lw=1.6, label="-99% VaR (rolling 250 prior days)")
ax.scatter(t.index[t.breach], t.loc[t.breach, "pnl"], color=RED, s=28, zorder=5, label=f"VaR breach (n={t.breach.sum()})")
ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"), color=RED, alpha=0.07, label="2022")
ax.legend(loc="lower left", ncol=2, fontsize=8, frameon=False)
finish(fig, ax, "fig1_pnl_vs_var.png", "Daily simulated P&L vs 99% historical VaR, 2020-2026")

# 2. 2022 zoom
z = t.loc["2022"]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(z.index, z["pnl"], width=0.9, color=GREY, alpha=0.8, label="Daily simulated P&L")
ax.plot(z.index, -z["var"], color=NAVY, lw=2, label="-99% VaR")
b = z[z.breach]
ax.scatter(b.index, b["pnl"], color=RED, s=40, zorder=5, label=f"Breach (n={len(b)}; expected ~2.5)")
for i, (dt_, r) in enumerate(b.iterrows()):
    dx, dy = [(0, -26), (0, -26), (-30, -30), (22, -20), (22, -38), (0, -26), (0, -26)][i]
    ax.annotate(f"{dt_:%d %b}\n{-r.pnl/r['var']:.2f}x VaR", (dt_, r.pnl), xytext=(dx, dy), textcoords="offset points",
                ha="center", fontsize=6.5, color=RED, arrowprops=dict(arrowstyle="-", color=RED, lw=0.5))
ax.set_ylim(top=0.9e6); ax.legend(loc="upper left", ncol=3, fontsize=8, frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
finish(fig, ax, "fig2_2022_breaches.png", "2022: seven breaches, loss 1.02x-1.50x the VaR forecast")

# 3. VaR adjustment 2021H2-2024
a = d.loc["2021-07-01":"2024-12-31"]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(a.index, a["var"], color=NAVY, lw=2, label="99% VaR forecast (left)")
loss = (-a["pnl"]).where(a["pnl"] < 0)
ax.scatter(a.index, loss, s=3, color=GREY, alpha=0.6, label="Daily simulated loss (left)")
ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"), color=RED, alpha=0.07)
ax.set_ylim(0, 1.1e6)
ax2 = ax.twinx(); ax2.plot(a.index, a["y10"], color=BLUE, lw=1, ls="--", label="10y GoC yield, % (right)")
ax2.spines["right"].set_visible(True); ax2.grid(False); ax2.set_ylabel("10-year yield, %")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8, frameon=False)
finish(fig, ax, "fig3_var_adjustment.png", "How VaR adjusted: it lagged the 2022 rise, then stayed high through 2024")

# 4. Breach rate by year
s = pd.read_csv(C.OUT_DIR / "backtest_summary.csv")
s = s[s.period.str.fullmatch(r"\d{4}")].sort_values("period")
fig, ax = plt.subplots(figsize=(10, 4.2))
cols = [RED if p == "2022" else NAVY for p in s.period]
ax.bar(s.period, s.breaches, color=cols)
ax.axhline(2.5, color=GREY, ls="--", lw=1.2); ax.text(len(s) - 0.5, 2.6, "expected ~2.5 / year", ha="right", fontsize=8, color=GREY)
for i, (n, o) in enumerate(zip(s.breaches, s.obs)):
    ax.text(i, n + 0.12, f"{n}/{o}", ha="center", fontsize=8)
ax.set_ylim(0, 8.5); ax.grid(axis="x", visible=False)
finish(fig, ax, "fig4_breaches_by_year.png", "99% VaR breaches by year (expected: 1% of days)", ylabel="Breaches")
ax.figure  # noqa

# 5. Stress tests
st = pd.read_csv(C.OUT_DIR / "stress_tests.csv").sort_values("pnl_cad")
fig, ax = plt.subplots(figsize=(10, 4.2))
lab = st.scenario.str.replace("Hypothetical: ", "Hyp: ").str.replace(r" \((\d{4}-\d\d)-\d\d -> (\d{4}-\d\d)-\d\d\)", r" (\1 to \2)", regex=True)
ax.barh(lab, st.pnl_cad, color=[RED if v < 0 else BLUE for v in st.pnl_cad])
ax.axvline(0, color="k", lw=0.8); ax.grid(axis="y", visible=False)
for i, v in enumerate(st.pnl_cad):
    ax.text(v + (0.15e6 if v >= 0 else -0.15e6), i, f"{v/1e6:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8)
ax.set_xlim(-14e6, 7.5e6); ax.xaxis.set_major_formatter(plt.FuncFormatter(M))
fig.text(0.01, 0.005, NOTE + " Hypothetical scenarios start from 30-Oct-2026 yields.", fontsize=6.5, color=GREY)
ax.set_title("Stress tests: simulated portfolio P&L (full revaluation)", loc="left"); ax.set_xlabel("C$ millions")
fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(CH / "fig5_stress_tests.png"); plt.close(fig)
print("charts written:", sorted(p.name for p in CH.glob("*.png")))
