"""Performance statistics on monthly return series (annualised with 12 periods per year)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def drawdown(r: pd.Series) -> pd.Series:
    wealth = (1 + r).cumprod()
    return wealth / wealth.cummax().clip(lower=1.0) - 1


def metrics(net: pd.Series, bench: pd.Series, rf: pd.Series, turnover: pd.Series | None = None) -> dict:
    idx = net.dropna().index.intersection(bench.dropna().index)
    net, bench, rf = net[idx], bench[idx], rf.reindex(idx).fillna(0.0)
    n = len(net)
    excess, active = net - rf, net - bench
    te = active.std() * np.sqrt(12)
    return {
        "months": n,
        "cagr": float((1 + net).prod() ** (12 / n) - 1),
        "vol": float(net.std() * np.sqrt(12)),
        "sharpe": float(excess.mean() / excess.std() * np.sqrt(12)),
        "max_dd": float(-drawdown(net).min()),
        "tracking_error": float(te),
        "info_ratio": float(active.mean() * 12 / te) if te > 0 else float("nan"),
        "hit_rate": float((active > 0).mean()),
        "avg_turnover": float(turnover.reindex(idx).mean()) if turnover is not None else float("nan"),
    }
