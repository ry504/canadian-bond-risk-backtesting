"""Build excel/Risk_Dashboard_base.xlsx (macro-free) from excel/*.csv with xlsxwriter - no Excel needed.
The shipped excel/Risk_Dashboard.xlsm is this workbook plus the VBA module and refresh button.
Data lives in five Excel Tables; every dashboard number is a formula on those tables, so the VBA
macro in vba/RefreshDashboard.bas only has to reload the tables from the CSVs."""
import pandas as pd
import xlsxwriter
import config as C

X = C.ROOT / "excel"
OUT = C.ROOT / "excel" / "Risk_Dashboard_base.xlsx"
NAVY, RED, GREY, BLUE, LIGHT = "#1f3a5f", "#c0392b", "#8a94a0", "#2e7bb4", "#eef2f7"

wb = xlsxwriter.Workbook(OUT)
F = lambda **k: wb.add_format({"font_name": "Calibri", **k})
title = F(bold=True, font_size=20, font_color=NAVY)
sub = F(italic=True, font_size=9, font_color="#555555")
kl = F(font_size=9, font_color="#555555", bg_color=LIGHT, align="center", top=1, top_color=NAVY)
kv = lambda nf: F(bold=True, font_size=18, font_color=NAVY, bg_color=LIGHT, align="center", valign="vcenter", num_format=nf)
h = F(bold=True, font_color="white", bg_color=NAVY, align="center", border=1, text_wrap=True, valign="vcenter")
cell = lambda nf="General", **k: F(num_format=nf, border=1, border_color="#cccccc", **k)
sec = F(bold=True, font_size=12, font_color=NAVY, bottom=2, bottom_color=NAVY)
warn = F(font_size=9, font_color=RED, text_wrap=True, valign="top")
verdict = F(bold=True, font_size=11, font_color=RED, text_wrap=True, valign="vcenter")

dash = wb.add_worksheet("Dashboard")
about = wb.add_worksheet("About")
wsd, ws22, wss, wsx, wsb = (wb.add_worksheet(n) for n in ("Data_Daily", "Data_2022", "Data_Summary", "Data_Stress", "Data_Breaches2022"))
for w in (dash, about):
    w.hide_gridlines(2)


def add_table(ws, name, csv, formats=None):
    df = pd.read_csv(X / csv)
    n = len(df)
    formats = formats or {}
    cols = [{"header": c, **({"format": formats[c]} if c in formats else {})} for c in df.columns]
    data = df.astype(object).where(df.notna(), None).values.tolist()
    ws.add_table(0, 0, n, len(df.columns) - 1, {"name": name, "columns": cols, "data": data, "style": "Table Style Light 9"})
    ws.set_column(0, len(df.columns) - 1, 16)
    ws.freeze_panes(1, 0)
    return n


dfmt = wb.add_format({"num_format": "yyyy-mm-dd"})
# dates as real Excel dates
for csv in ("daily.csv", "y2022.csv", "breaches2022.csv"):
    df = pd.read_csv(X / csv); df["date"] = pd.to_datetime(df["date"]); df.to_csv(X / ("_" + csv), index=False, date_format="%Y-%m-%d")


def add_table_dates(ws, name, csv, formats):
    df = pd.read_csv(X / csv, parse_dates=["date"])
    n = len(df)
    cols = [{"header": c, **({"format": formats[c]} if c in formats else {})} for c in df.columns]
    data = [[(None if pd.isna(v) else (v.to_pydatetime() if c == "date" else (float(v) if not isinstance(v, str) else v)))
             for c, v in zip(df.columns, row)] for row in df.itertuples(index=False)]
    ws.add_table(0, 0, n, len(df.columns) - 1, {"name": name, "columns": cols, "data": data, "style": "Table Style Light 9"})
    ws.set_column(0, len(df.columns) - 1, 15)
    ws.freeze_panes(1, 0)
    return n


for csv in ("_daily.csv", "_y2022.csv", "_breaches2022.csv"):
    (X / csv).unlink()
n_d = add_table_dates(wsd, "tblDaily", "daily.csv", {"date": dfmt, "pnl": cell("#,##0"), "var": cell("#,##0"), "neg_var": cell("#,##0"), "breach_pnl": cell("#,##0")})
n_22 = add_table_dates(ws22, "tblY2022", "y2022.csv", {"date": dfmt})
n_s = add_table(wss, "tblSummary", "summary.csv")
n_x = add_table(wsx, "tblStress", "stress.csv")
n_b = add_table_dates(wsb, "tblBreaches2022", "breaches2022.csv", {"date": dfmt})
for w in (wsd, ws22, wss, wsx, wsb):
    w.set_tab_color(GREY)

# ---------- Dashboard ----------
dash.set_column("A:A", 2); dash.set_column("B:M", 11.5)
dash.write("B1", "Canadian Fixed-Income Risk Backtesting", title)
dash.write("B2", "Did a 99% one-day historical VaR underestimate losses on a SIMULATED C$100M Government of Canada bond portfolio in 2022? "
           "Data: Bank of Canada Valet. Simulated P&L only - NOT actual bank trading losses.", sub)
dash.write("K3", "Last refreshed:", F(font_size=9, align="right")); dash.merge_range("L3:M3", "Built by Python", F(font_size=9, bold=True))
wb.define_name("LastRefreshed", "=Dashboard!$L$3")
dash.set_row(3, 16); dash.set_row(4, 38)

S = lambda label, col: f'INDEX(tblSummary[{col}],MATCH("{label}",tblSummary[period],0))'
tiles = [
    ("Portfolio (C$, simulated)", f"={C.PORTFOLIO_VALUE}", "#,##0"),
    ("Avg portfolio duration (yrs)", "=AVERAGE(tblDaily[port_dur])", "0.00"),
    ("Days backtested", "=COUNT(tblDaily[var])", "#,##0"),
    ("Total breaches", "=COUNT(tblDaily[breach_pnl])", "0"),
    ("2022 breaches", "=" + S("Year 2022", "breaches"), "0"),
    ("2022 breach rate (target 1%)", "=" + S("Year 2022", "breach_rate_pct") + "/100", "0.0%"),
]
for i, (lab, f, nf) in enumerate(tiles):
    c = 1 + 2 * i
    dash.merge_range(3, c, 3, c + 1, lab, kl)
    dash.merge_range(4, c, 4, c + 1, "", kv(nf)); dash.write_formula(4, c, f, kv(nf))

dash.merge_range("B7:M7", "", verdict)
dash.write_formula("B7", '="2022 Kupiec test p-value = "&TEXT(' + S("Year 2022", "kupiec_p") + ',"0.000")&": "&IF(' + S("Year 2022", "kupiec_p") + '<0.01,"breach rate rejected at 1%",IF(' + S("Year 2022", "kupiec_p") + '<0.05,"breach rate rejected at 5% but NOT at 1% - modest evidence of underestimation","not rejected"))&". One year of data (7 breaches) - treat as suggestive, not conclusive."', verdict)
dash.set_row(6, 30)

# charts
base = {"x_axis": {"date_axis": True, "num_format": "mmm yy", "num_font": {"size": 8}}, "legend": {"position": "bottom", "font": {"size": 8}}}


def pnl_var_chart(tbl, n_rows, sheet, kind, ttl, w, hgt):
    first = 1
    cats = [sheet, first, 0, n_rows, 0]
    ch = wb.add_chart({"type": "column" if kind == "col" else "line"})
    ch.add_series({"name": "Daily simulated P&L", "categories": cats, "values": [sheet, first, 2 if sheet == "Data_Daily" else 1, n_rows, 2 if sheet == "Data_Daily" else 1],
                   "line": {"color": GREY, "width": 0.75}, "fill": {"color": GREY}, "gap": 20} if kind == "col" else
                  {"name": "Daily simulated P&L", "categories": cats, "values": [sheet, first, 2, n_rows, 2], "line": {"color": GREY, "width": 0.75}})
    ln = wb.add_chart({"type": "line"})
    vc, bc = (4, 6) if sheet == "Data_Daily" else (2, 3)
    ln.add_series({"name": "-99% VaR", "categories": cats, "values": [sheet, first, vc, n_rows, vc], "line": {"color": NAVY, "width": 2}})
    ln.add_series({"name": "Breach", "categories": cats, "values": [sheet, first, bc, n_rows, bc], "line": {"none": True},
                   "marker": {"type": "circle", "size": 6, "fill": {"color": RED}, "border": {"color": RED}}})
    ch.combine(ln)
    ch.set_title({"name": ttl, "name_font": {"size": 11, "color": NAVY}})
    ch.set_x_axis({"date_axis": True, "num_format": "mmm yy", "num_font": {"size": 8}, "label_position": "low"})
    ch.set_y_axis({"num_format": '#,##0,,"M"', "num_font": {"size": 8}, "major_gridlines": {"visible": True, "line": {"color": "#e5e5e5"}}, "name": "C$"})
    ch.set_legend({"position": "bottom", "font": {"size": 8}}); ch.set_size({"width": w, "height": hgt})
    ch.show_blanks_as("gap")
    return ch


dash.insert_chart("B9", pnl_var_chart("tblDaily", n_d, "Data_Daily", "line", "Daily simulated P&L vs 99% VaR (all days)", 640, 320))
dash.insert_chart("H9", pnl_var_chart("tblY2022", n_22, "Data_2022", "col", "2022 zoom: breaches in red", 560, 320))

# summary table
r0 = 27
dash.merge_range(r0, 1, r0, 12, "Backtest: 2022 vs other years (rolling 250-day window, no look-ahead)", sec)
hdr = ["Period", "Days", "Breaches", "Expected", "Breach rate", "Kupiec p", "Christoffersen p", "Avg VaR (C$)", "Worst loss (C$)", "Avg breach / VaR"]
cols_ = ["period", "obs", "breaches", "expected_breaches", "breach_rate_pct", "kupiec_p", "christoffersen_ind_p", "avg_var_cad", "worst_loss_cad", "avg_breach_loss_over_var"]
fm = ["@", "#,##0", "0", "0.0", '0.00"%"', "0.000", "0.000", "#,##0", "#,##0", '0.00"x"']
dash.set_row(r0 + 1, 30)
for j, t in enumerate(hdr):
    dash.write(r0 + 1, 1 + j, t, h)
labels = ["Year 2022", "Ex-2022 (2020-26)", "All tested days", "Year 2020", "Year 2021", "Year 2023", "Year 2024", "Year 2025", "Year 2026"]
for i, lab in enumerate(labels):
    for j, (c, nf) in enumerate(zip(cols_, fm)):
        f = f'=IFERROR(INDEX(tblSummary[{c}],MATCH("{lab}",tblSummary[period],0)),"n/a")'
        if j == 0:
            dash.write(r0 + 2 + i, 1, lab, cell(bold=(i == 0), bg_color="#fdecea" if i == 0 else "white"))
        else:
            dash.write_formula(r0 + 2 + i, 1 + j, f, cell(nf, align="right", bg_color="#fdecea" if i == 0 else "white"))
dash.merge_range(r0 + 11, 1, r0 + 12, 12, "Christoffersen p is 'n/a' where a year has too few breaches to test clustering. Kupiec p < 0.05 means the breach rate differs from 1% "
                 "(2024's 0 breaches is rejected as too conservative). With 1 test per year, 7 yearly tests have multiple-testing noise: one p<0.05 is expected by chance ~30% of the time.", warn)

# breaches 2022 + stress
r1 = r0 + 14
dash.merge_range(r1, 1, r1, 5, "2022 VaR breaches (simulated loss vs VaR)", sec)
for j, t in enumerate(["Date", "Loss (C$)", "VaR (C$)", "Loss / VaR"]):
    dash.write(r1 + 1, 1 + j, t, h)
for i in range(10):
    for j, (c, nf) in enumerate(zip(["date", "loss", "var", "loss_over_var"], ["yyyy-mm-dd", "#,##0", "#,##0", '0.00"x"'])):
        dash.write_formula(r1 + 2 + i, 1 + j, f'=IFERROR(INDEX(tblBreaches2022[{c}],{i + 1}),"")', cell(nf, align="right"))
dash.merge_range(r1, 6, r1, 12, "Stress tests (simulated portfolio, full revaluation)", sec)
dash.merge_range(r1 + 1, 6, r1 + 1, 10, "Scenario", h); dash.write(r1 + 1, 11, "P&L (C$M)", h); dash.write(r1 + 1, 12, "% of port.", h)
for i in range(8):
    dash.merge_range(r1 + 2 + i, 6, r1 + 2 + i, 10, "", cell())
    dash.write_formula(r1 + 2 + i, 6, f'=IFERROR(INDEX(tblStress[scenario],{i + 1}),"")', cell())
    dash.write_formula(r1 + 2 + i, 11, f'=IFERROR(INDEX(tblStress[pnl_cad],{i + 1})/1000000,"")', cell('0.0;[Red]-0.0', align="right"))
    dash.write_formula(r1 + 2 + i, 12, f'=IFERROR(INDEX(tblStress[pnl_pct],{i + 1})/100,"")', cell('0.0%;[Red]-0.0%', align="right"))

# stress + breaches-by-year charts
ch = wb.add_chart({"type": "bar"})
ch.add_series({"name": "P&L (C$)", "categories": ["Data_Stress", 1, 0, n_x, 0], "values": ["Data_Stress", 1, 5, n_x, 5],
               "fill": {"color": RED}, "invert_if_negative": True, "invert_if_negative_color": RED, "data_labels": {"value": True, "num_format": '#,##0.0,,"M"', "font": {"size": 8}}})
ch.set_title({"name": "Stress tests - simulated P&L", "name_font": {"size": 11, "color": NAVY}})
ch.set_legend({"none": True}); ch.set_y_axis({"reverse": True, "num_font": {"size": 7}, "label_position": "low"})
ch.set_x_axis({"num_format": '#,##0,,"M"', "num_font": {"size": 8}}); ch.set_size({"width": 640, "height": 300})
dash.insert_chart(r1 + 13, 1, ch)
cb = wb.add_chart({"type": "column"})
cb.add_series({"name": "Breaches", "categories": ["Data_Summary", 2, 0, 8, 0], "values": ["Data_Summary", 2, 2, 8, 2], "fill": {"color": NAVY},
               "points": [{}, {}, {"fill": {"color": RED}}, {}, {}, {}, {}], "data_labels": {"value": True}})
cb.set_title({"name": "VaR breaches per year (expected ~2.5)", "name_font": {"size": 11, "color": NAVY}})
cb.set_legend({"none": True}); cb.set_size({"width": 560, "height": 300}); cb.set_y_axis({"major_gridlines": {"visible": True, "line": {"color": "#e5e5e5"}}})
dash.insert_chart(r1 + 13, 6, cb, {"x_offset": 10})

# ---------- About ----------
about.set_column("A:A", 2); about.set_column("B:B", 110)
lines = [
    ("Canadian Fixed-Income Risk Backtesting - how this workbook works", title),
    ("", None),
    ("WHAT THIS IS: a simulated C$100M portfolio (1/3 each in 2y, 5y, 10y Government of Canada benchmark bonds). Losses are SIMULATED from daily yield changes; they are not any bank's actual trading losses.", None),
    ("DATA: Bank of Canada Valet API, series BD.CDN.2YR/5YR/10YR.DQ.YLD, 2019-01-02 to 2026-10-30. Rounded to 0.01% by the Bank, so yield changes are in whole basis points.", None),
    ("P&L: -ModDuration x dy + 0.5 x Convexity x dy^2 on each tranche, duration/convexity of a par bond (coupon = yield, semi-annual) at the PREVIOUS day's yield. Price effect only: no carry, roll-down or funding.", None),
    ("VaR: 99% one-day historical VaR from the 250 daily P&Ls strictly before the day tested (no look-ahead). Breach = loss larger than VaR.", None),
    ("", None),
    ("REFRESHING FROM PYTHON RESULTS", sec),
    ("1. In a terminal: python src/run_all.py   (re-downloads data, recomputes everything, rewrites excel/*.csv).", None),
    ("2. In this workbook (Risk_Dashboard.xlsm, macros enabled) click 'Refresh Dashboard' on the Dashboard sheet. It reloads the five Data_ tables from the CSVs in this folder; every dashboard cell and chart updates.", None),
    ("On macOS, Excel asks once to grant access to the CSV files - click Select/Allow. Full details: README.md.", None),
]
for i, (t, f) in enumerate(lines):
    about.write(i, 1, t, f or F(text_wrap=True, valign="top"))
    if f is None and t:
        about.set_row(i, 32)
about.set_row(0, 30)
dash.activate()
wb.close()
print("wrote", OUT)
