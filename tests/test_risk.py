import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np, pandas as pd, pytest
import config as C, risk


def test_par_bond_prices_at_par():
    assert float(np.squeeze(risk.par_bond_price(0.04, 0.04, 10))) == pytest.approx(1.0, abs=1e-12)


def test_duration_matches_closed_form_and_finite_difference():
    y, n = 0.03, 10
    D, X = risk.duration_convexity(np.array([y]), n)
    closed = (1 / y) * (1 - (1 + y / 2) ** (-2 * n))      # par bond modified duration
    assert D[0] == pytest.approx(closed, rel=1e-10)
    h = 1e-5
    p = lambda yy: float(np.squeeze(risk.par_bond_price(yy, y, n)))
    assert D[0] == pytest.approx(-(p(y + h) - p(y - h)) / (2 * h), rel=1e-6)
    assert X[0] == pytest.approx((p(y + h) - 2 * p(y) + p(y - h)) / h**2, rel=1e-4)


def test_pnl_approximation_close_to_full_revaluation_for_daily_moves():
    y0 = {2: 3.0, 5: 3.2, 10: 3.5}
    sh = {2: 10, 5: 8, 10: 6}  # large daily move, bp
    full = risk.reprice(y0, sh)["total"]
    yl = pd.DataFrame({"y2": [3.0, 3.10], "y5": [3.2, 3.28], "y10": [3.5, 3.56]})
    approx = risk.daily_pnl(yl)["pnl"].iloc[0]
    assert approx == pytest.approx(full, rel=2e-3)


def test_var_matches_independent_loop_and_has_no_lookahead():
    rng = np.random.default_rng(0)
    pnl = pd.Series(rng.normal(0, 1e5, 600), index=pd.bdate_range("2020-01-01", periods=600))
    v = risk.rolling_var(pnl)
    for t in (250, 300, 599):
        manual = -np.quantile(pnl.iloc[t - 250:t].values, 0.01)  # strictly prior 250 obs
        assert v.iloc[t] == pytest.approx(manual)
    assert v.iloc[:250].isna().all()
    # changing today's P&L must not change today's VaR
    p2 = pnl.copy(); p2.iloc[400] = -1e9
    assert risk.rolling_var(p2).iloc[400] == pytest.approx(v.iloc[400])


def test_breach_definition():
    pnl = pd.Series([-1.0] * 250 + [-5.0, 0.5], index=pd.bdate_range("2020-01-01", periods=252))
    bt = risk.backtest_frame(pnl)
    assert list(bt["breach"]) == [True, False]  # VaR = 1.0 (loss); -5 < -1 breach, 0.5 not


def test_kupiec_known_values():
    lr, p = risk.kupiec_pof(250, 0)
    assert lr == pytest.approx(-2 * 250 * np.log(0.99), rel=1e-9)  # closed form for x=0
    lr, p = risk.kupiec_pof(1000, 10)
    assert lr == pytest.approx(0, abs=1e-9) and p == pytest.approx(1.0)


def test_yields_in_db_are_sane():
    import sqlite3
    df = pd.read_sql("SELECT * FROM yields_wide", sqlite3.connect(C.DB_PATH))
    assert df.date.is_unique and df[["y2", "y5", "y10"]].notna().all().all()
    assert ((df[["y2", "y5", "y10"]] > 0) & (df[["y2", "y5", "y10"]] < 10)).all().all()
    assert df.date.min() <= "2019-01-04"
