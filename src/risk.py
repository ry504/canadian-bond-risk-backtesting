"""Portfolio P&L, rolling historical VaR, breach tests, stress tests. Pure functions, no I/O."""

import numpy as np
import pandas as pd
from scipy import stats

import config as C

TENORS = (2, 5, 10)


# ---------- bond maths ----------
def par_bond_price(y, coupon, n_years, f=C.COUPONS_PER_YEAR):
    """Price per 1 face of a bond with annual coupon rate `coupon`, yield `y` (decimals)."""
    y, coupon = np.asarray(y, float), np.asarray(coupon, float)
    k = np.arange(1, int(n_years * f) + 1)[:, None]
    disc = (1 + y / f) ** (-k)
    return (coupon / f * disc).sum(0) + disc[-1]


def duration_convexity(y, n_years, f=C.COUPONS_PER_YEAR):
    """Modified duration and convexity (in years, years^2) of a par bond (coupon = yield).
    Closed-form-equivalent cash-flow sums; y is an array of decimal yields."""
    y = np.asarray(y, float)
    k = np.arange(1, int(n_years * f) + 1)[:, None]
    cf = np.where(k == k[-1], 1 + y / f, y / f)  # per 1 face
    disc = (1 + y / f) ** (-k)
    price = (cf * disc).sum(0)
    mod_dur = (cf * disc * k / f).sum(0) / price / (1 + y / f)
    convex = (cf * disc * k * (k + 1) / f**2).sum(0) / price / (1 + y / f) ** 2
    return mod_dur, convex


# ---------- P&L ----------
def daily_pnl(yields: pd.DataFrame) -> pd.DataFrame:
    """Approximate daily P&L (C$) of the simulated portfolio.

    yields: index = date, columns y2,y5,y10 in PERCENT.
    P&L_t = sum_i  w_i * V * ( -D_i(y_{t-1}) * dy + 0.5 * Cvx_i(y_{t-1}) * dy^2 ),  dy = y_t - y_{t-1} (decimal).
    Duration/convexity use the PREVIOUS day's yield (information known at t-1). Price return only:
    no coupon carry, roll-down, funding or transaction costs. Exposure reset to V every day.
    """
    out = pd.DataFrame(index=yields.index)
    total = 0.0
    for m in TENORS:
        y = yields[f"y{m}"] / 100
        dy = y.diff()
        D, X = duration_convexity(y.shift(1).fillna(y.iloc[0]).values, m)
        contrib = C.WEIGHTS[m] * C.PORTFOLIO_VALUE * (-D * dy + 0.5 * X * dy**2)
        out[f"pnl{m}"] = contrib
        out[f"dur{m}"] = D
        total = total + contrib
    out["pnl"] = total
    out["port_dur"] = sum(C.WEIGHTS[m] * out[f"dur{m}"] for m in TENORS)
    return out.iloc[1:]  # first row has no change


# ---------- VaR ----------
def rolling_var(pnl: pd.Series, window=C.WINDOW, conf=C.CONFIDENCE) -> pd.Series:
    """99% 1-day historical VaR (positive C$ loss) for day t from the `window` P&Ls strictly BEFORE t.
    shift(1) guarantees day t's own P&L never enters its own VaR (no look-ahead).
    Quantile uses numpy's default linear interpolation."""
    q = pnl.shift(1).rolling(window).quantile(1 - conf)
    return -q


def backtest_frame(pnl: pd.Series, window=C.WINDOW, conf=C.CONFIDENCE) -> pd.DataFrame:
    df = pd.DataFrame({"pnl": pnl})
    df["var"] = rolling_var(pnl, window, conf)
    df = df.dropna()
    df["breach"] = df["pnl"] < -df["var"]
    return df


# ---------- backtest statistics ----------
def kupiec_pof(n_obs: int, n_breach: int, p=1 - C.CONFIDENCE):
    """Kupiec (1995) proportion-of-failures likelihood-ratio test. Returns (LR, p_value)."""
    if n_obs == 0:
        return np.nan, np.nan
    x, N = n_breach, n_obs
    ll0 = (N - x) * np.log(1 - p) + x * np.log(p)
    ph = x / N
    ll1 = (N - x) * np.log(1 - ph) if ph < 1 else 0.0
    ll1 += x * np.log(ph) if x > 0 else 0.0
    lr = -2 * (ll0 - ll1)
    return lr, 1 - stats.chi2.cdf(lr, 1)


def christoffersen_independence(b: np.ndarray):
    """Christoffersen (1998) independence test on a 0/1 breach sequence. Returns (LR, p_value).
    NaN if there are too few breaches to estimate transitions."""
    b = np.asarray(b, int)
    n00 = n01 = n10 = n11 = 0
    for a, c in zip(b[:-1], b[1:]):
        n00 += a == 0 and c == 0
        n01 += a == 0 and c == 1
        n10 += a == 1 and c == 0
        n11 += a == 1 and c == 1
    if n01 + n11 == 0 or n01 == 0 and n11 == 0:
        return np.nan, np.nan
    pi01 = n01 / (n00 + n01)
    pi11 = n11 / (n10 + n11) if n10 + n11 > 0 else 0.0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    def ll(p, a, c):  # a = count of "not", c = count of "event"
        return (a * np.log(1 - p) if a else 0) + (c * np.log(p) if c else 0)

    l0 = ll(pi, n00 + n10, n01 + n11)
    l1 = ll(pi01, n00, n01) + ll(pi11, n10, n11)
    lr = -2 * (l0 - l1)
    return lr, 1 - stats.chi2.cdf(lr, 1)


def summarize(bt: pd.DataFrame, label: str) -> dict:
    n, x = len(bt), int(bt["breach"].sum())
    lr, pv = kupiec_pof(n, x)
    ci_lr, ci_p = christoffersen_independence(bt["breach"].values)
    br = bt[bt["breach"]]
    return {
        "period": label,
        "obs": n,
        "breaches": x,
        "breach_rate_pct": 100 * x / n if n else np.nan,
        "expected_breaches": n * (1 - C.CONFIDENCE),
        "kupiec_LR": lr,
        "kupiec_p": pv,
        "christoffersen_ind_p": ci_p,
        "avg_var_cad": bt["var"].mean(),
        "worst_loss_cad": -bt["pnl"].min(),
        "avg_breach_loss_over_var": (-br["pnl"] / br["var"]).mean()
        if len(br)
        else np.nan,
        "max_breach_loss_over_var": (-br["pnl"] / br["var"]).max()
        if len(br)
        else np.nan,
    }


# ---------- stress tests ----------
def reprice(yields_pct_start: dict, shocks_bp: dict) -> dict:
    """FULL revaluation: each tranche is a par bond (coupon = start yield) repriced at start + shock.
    Returns P&L (C$) per tenor and total. Exact (no duration approximation)."""
    res = {}
    for m in TENORS:
        y0 = yields_pct_start[m] / 100
        y1 = y0 + shocks_bp[m] / 1e4
        res[m] = (
            C.WEIGHTS[m]
            * C.PORTFOLIO_VALUE
            * (float(np.squeeze(par_bond_price(y1, y0, m))) - 1.0)
        )
    res["total"] = sum(res[m] for m in TENORS)
    return res
