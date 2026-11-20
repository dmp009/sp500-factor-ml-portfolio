import numpy as np
import pandas as pd

from factorml import performance as pm


def series(values, start="2016-01"):
    return pd.Series(values, index=pd.period_range(start, periods=len(values), freq="M"), dtype=float)


def test_metrics_hand_case():
    net = series([0.1, -0.1])
    m = pm.metrics(net, series([0.0, 0.0]), series([0.0, 0.0]))
    assert np.isclose(m["max_dd"], 0.1)
    assert np.isclose(m["hit_rate"], 0.5)


def test_sharpe_known_value():
    net = series([0.02, 0.0] * 6)  # mean 1%, sample std 1% * sqrt(12/11)
    m = pm.metrics(net, series([0.0] * 12), series([0.0] * 12))
    assert np.isclose(m["sharpe"], np.sqrt(11))
    assert np.isclose(m["cagr"], 1.02 ** 6 - 1)
    assert np.isclose(m["info_ratio"], m["sharpe"])  # benchmark 0 -> active = net
