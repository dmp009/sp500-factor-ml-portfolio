import numpy as np
import pandas as pd

from factorml import portfolio as pf

M = pd.Period("2016-01", "M")


def ranks(n=120, month=M):
    return pd.DataFrame({"month": month, "ticker": [f"T{i}" for i in range(n)], "rank": range(1, n + 1)})


def test_equal_weight_top_n():
    w = pf.weights(ranks(), top_n=50)
    assert len(w) == 50 and np.allclose(w["weight"], 0.02)
    assert set(w["ticker"]) == {f"T{i}" for i in range(50)}


def test_turnover_full_switch_is_one():
    a = pd.Series({"A": 0.5, "B": 0.5})
    b = pd.Series({"C": 0.5, "D": 0.5})
    assert pf.turnover(a, b) == 1.0
    assert pf.turnover(a, a) == 0.0


def test_costs():
    # first rebalance from cash: one-way turnover 0.5 (buy everything), 10 bps per side -> 0.001
    w = pd.DataFrame({"month": M, "ticker": ["A", "B"], "weight": [0.5, 0.5]})
    r = pd.DataFrame({"month": M + 1, "ticker": ["A", "B"], "ret": [0.02, 0.04]})
    s = pf.strategy_returns(w, r, cost_bps=10).set_index("month")
    assert np.isclose(s.loc[M + 1, "turnover"], 0.5)
    assert np.isclose(s.loc[M + 1, "cost"], 0.001)
    assert np.isclose(s.loc[M + 1, "gross"], 0.03) and np.isclose(s.loc[M + 1, "net"], 0.029)


def test_missing_return_earns_zero_and_is_reported():
    w = pd.DataFrame({"month": M, "ticker": ["A", "B"], "weight": [0.5, 0.5]})
    r = pd.DataFrame({"month": M + 1, "ticker": ["A"], "ret": [0.02]})
    s = pf.strategy_returns(w, r, cost_bps=0).set_index("month")
    assert np.isclose(s.loc[M + 1, "gross"], 0.01) and s.loc[M + 1, "n_missing"] == 1


def test_equal_weight_universe_mean():
    members = pd.DataFrame({"month": M, "ticker": ["A", "B", "C"]})
    r = pd.DataFrame({"month": [M + 1] * 4, "ticker": ["A", "B", "C", "Z"], "ret": [0.03, 0.0, -0.03, 0.5]})
    ew = pf.equal_weight_universe(members, r)
    assert np.isclose(ew[M + 1], 0.0)  # Z is not a member
