"""Independent re-computation of VaR and breaches from the stored daily P&L using plain loops (no pandas rolling)."""
import csv, math, pathlib
import numpy as np, pytest

OUT = pathlib.Path(__file__).resolve().parents[1] / "output"


def _load():
    with open(OUT / "daily_results.csv") as f:
        return list(csv.DictReader(f))


def test_breaches_recomputed_independently():
    rows = _load()
    pnl = [float(r["pnl"]) for r in rows]
    n_breach = {}
    for t in range(250, len(rows)):
        window = sorted(pnl[t - 250:t])                 # strictly prior 250 P&Ls
        pos = 0.01 * 249                                # numpy 'linear' position for q=1%
        lo = math.floor(pos)
        var = -(window[lo] + (pos - lo) * (window[lo + 1] - window[lo]))
        assert float(rows[t]["var"]) == pytest.approx(var, rel=1e-9)
        breach = pnl[t] < -var
        assert int(float(rows[t]["breach"])) == int(breach)
        if breach:
            n_breach[rows[t]["date"][:4]] = n_breach.get(rows[t]["date"][:4], 0) + 1
    assert n_breach["2022"] == 7
    assert sum(n_breach.values()) == 23
    assert not any(r["var"] for r in rows[:250])        # no VaR before 250 prior obs exist


def test_breach_list_matches_daily():
    rows = _load()
    expect = [r["date"] for r in rows if r["breach"] not in ("", None) and int(float(r["breach"])) == 1]
    with open(OUT / "breach_list.csv") as f:
        got = [r["date"] for r in csv.DictReader(f)]
    assert got == expect
