"""Long-only top-N, equal weight, monthly rebalance with linear trading costs.

Weights formed at the close of month M earn the returns of M+1. Turnover is measured against the
previous holdings after they drifted with M's returns. A holding with no return in M+1 (delisted,
missing on Yahoo) earns 0 and is counted in `n_missing`, so the gap is visible rather than filled.
"""
from __future__ import annotations

import pandas as pd


def weights(ranks: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    top = ranks[ranks["rank"] <= top_n][["month", "ticker"]].copy()
    top["weight"] = 1.0 / top.groupby("month")["ticker"].transform("count")
    return top.reset_index(drop=True)


def turnover(w_prev: pd.Series, w_new: pd.Series) -> float:
    """One-way turnover: half the sum of absolute weight changes."""
    d = w_new.reindex(w_new.index.union(w_prev.index), fill_value=0) - w_prev.reindex(
        w_new.index.union(w_prev.index), fill_value=0)
    return float(d.abs().sum() / 2)


def strategy_returns(weights: pd.DataFrame, returns: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """[month, gross, cost, net, turnover, n_missing]; `month` is the month the return was earned."""
    ret = returns.set_index(["month", "ticker"])["ret"]
    held = pd.Series(dtype=float)  # drifted holdings before this rebalance; empty = cash
    rows = []
    for m, w in weights.groupby("month", sort=True):
        w = w.set_index("ticker")["weight"]
        to = turnover(held, w)
        r = pd.Series([ret.get((m + 1, t), float("nan")) for t in w.index], index=w.index)
        n_missing = int(r.isna().sum())
        r = r.fillna(0.0)
        gross = float((w * r).sum())
        cost = 2 * to * cost_bps / 1e4  # buys and sells both pay cost_bps
        rows.append((m + 1, gross, cost, gross - cost, to, n_missing))
        grown = w * (1 + r)
        held = grown / grown.sum() if grown.sum() > 0 else grown
    return pd.DataFrame(rows, columns=["month", "gross", "cost", "net", "turnover", "n_missing"])


def equal_weight_universe(members: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """Benchmark 2: every index member at M, equally weighted, earning M+1 (missing returns earn 0 too)."""
    nxt = members.assign(month=members["month"] + 1).merge(returns[["month", "ticker", "ret"]],
                                                          on=["month", "ticker"], how="left")
    return nxt.assign(ret=nxt["ret"].fillna(0.0)).groupby("month")["ret"].mean().rename("equal_weight")
