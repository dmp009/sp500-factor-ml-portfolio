import numpy as np
import pandas as pd

from factorml import model as md
from factorml.features import FEATURES

FAST = {"n_estimators": 60, "learning_rate": 0.1, "num_leaves": 7, "min_child_samples": 20, "random_state": 0,
        "verbose": -1}


def synthetic(n_months=30, n_tickers=120, noise=0.5, seed=0):
    rng = np.random.default_rng(seed)
    months = pd.period_range("2011-01", periods=n_months, freq="M")
    rows = []
    for m in months:
        x = rng.uniform(size=(n_tickers, len(FEATURES)))
        df = pd.DataFrame(x, columns=FEATURES)
        df["month"], df["ticker"] = m, [f"T{i}" for i in range(n_tickers)]
        df["sector"] = rng.choice(["Energy", "Financials", "Health Care"], n_tickers)
        df["target"] = (df["mom_12_1"] - 0.5) * 0.1 + rng.normal(0, 0.1 * noise, n_tickers)
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


def test_walk_forward_uses_only_past():
    p = synthetic()
    m = pd.Period("2012-06", "M")
    base = md.walk_forward(p, "2012-06", FAST)
    p2 = p.copy()
    p2.loc[p2["month"] >= m - 1, "target"] = 99.0  # target of M-1 needs the return of M: not known at M
    again = md.walk_forward(p2, "2012-06", FAST)
    s1 = base[base["month"] == m].set_index("ticker")["score"]
    s2 = again[again["month"] == m].set_index("ticker")["score"]
    pd.testing.assert_series_equal(s1, s2)
    assert set(base.columns) == {"month", "ticker", "score", "rank", "model_version"}


def test_signal_recovered():
    p = synthetic()
    s = md.walk_forward(p, "2012-01", FAST)
    ic = md.information_coefficient(s, p)
    assert ic.mean() > 0.2


def test_factor_rule_ranks_by_mean_rank():
    p = pd.DataFrame({"month": pd.Period("2015-01", "M"), "ticker": ["A", "B", "C"],
                      "mom_12_1": [1.0, 0.5, 0.2], "gp": [1.0, 0.4, 0.3], "bm": [0.1, 0.6, 0.2]})
    r = md.factor_rule(p).set_index("ticker")
    assert r.loc["A", "rank"] == 1 and r.loc["C", "rank"] == 3
    assert np.isclose(r.loc["B", "score"], 0.5)
