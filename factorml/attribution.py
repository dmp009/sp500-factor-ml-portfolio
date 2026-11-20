"""Is the excess return alpha, or known factor exposure? Fama-French 5 + momentum regression.

Monthly OLS with Newey-West (HAC, 6 lags) standard errors, because overlapping holdings make
residuals autocorrelated.
"""
from __future__ import annotations

import pandas as pd
import statsmodels.api as sm

FACTORS = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom"]
NAMES = {"mkt_rf": "market", "smb": "size", "hml": "value", "rmw": "profitability", "cma": "investment",
         "mom": "momentum"}


def regress(excess: pd.Series, factors: pd.DataFrame) -> dict:
    data = pd.concat([excess.rename("y"), factors[FACTORS]], axis=1, join="inner").dropna()
    fit = sm.OLS(data["y"], sm.add_constant(data[FACTORS], has_constant="add")).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return {
        "alpha_annual": float(fit.params["const"] * 12),
        "alpha_t": float(fit.tvalues["const"]),
        "betas": {k: float(fit.params[k]) for k in FACTORS},
        "t_values": {k: float(fit.tvalues[k]) for k in FACTORS},
        "r2": float(fit.rsquared),
        "n": int(fit.nobs),
    }


def reading(result: dict) -> str:
    """One plain-English sentence; |t| >= 2 counts as significant."""
    a, t = result["alpha_annual"], result["alpha_t"]
    tilts = [NAMES[k] for k, v in result["t_values"].items() if k != "mkt_rf" and abs(v) >= 2]
    tilt = f" The significant tilts are {', '.join(tilts)}." if tilts else ""
    if abs(t) >= 2:
        return (f"After controlling for the five Fama-French factors and momentum, the annual alpha is {a:.1%} "
                f"(t = {t:.1f}), which is statistically significant.{tilt}")
    return (f"After controlling for the five Fama-French factors and momentum, the annual alpha is {a:.1%} "
            f"(t = {t:.1f}), which is not statistically significant: factor exposure explains the returns.{tilt}")
