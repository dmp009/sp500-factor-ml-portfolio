import numpy as np
import pandas as pd

from factorml import attribution as at

COLS = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]


def factors(n=240, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2005-01", periods=n, freq="M")
    return pd.DataFrame(rng.normal(0, 0.04, (n, len(COLS))), index=idx, columns=COLS)


def test_recovers_synthetic_betas():
    f = factors()
    noise = np.random.default_rng(1).normal(0, 0.002, len(f))  # annual alpha s.e. ~0.15 pp
    excess = 0.002 + 1.0 * f["mkt_rf"] + 0.5 * f["mom"] + noise
    r = at.regress(excess, f)
    assert abs(r["betas"]["mkt_rf"] - 1.0) < 0.1 and abs(r["betas"]["mom"] - 0.5) < 0.1
    assert abs(r["alpha_annual"] - 0.024) < 0.005
    assert r["n"] == 240 and r["alpha_t"] > 2
    assert "significant" in at.reading(r) and "not" not in at.reading(r)


def test_reading_says_not_significant():
    f = factors()
    excess = 1.0 * f["mkt_rf"] + np.random.default_rng(2).normal(0, 0.03, len(f))
    r = at.regress(excess, f)
    assert abs(r["alpha_t"]) < 2
    assert "not statistically significant" in at.reading(r)
