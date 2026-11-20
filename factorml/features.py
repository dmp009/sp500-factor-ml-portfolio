"""Monthly feature matrix: 14 classic equity characteristics, ranked within the month.

Everything at month M uses returns up to M and filings made by M's last day; the target is the
return in M+1 relative to the cross-sectional median, so the model learns to rank, not to time the market.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["mom_12_1", "mom_6_1", "rev_1", "vol_12", "beta_12", "size", "bm", "ey", "sp", "roe", "gp",
            "accruals", "leverage", "asset_growth"]
MIN_OBS = 8  # of 12 months for momentum, volatility and beta


def _window(wide: pd.DataFrame, month: pd.Period, first: int, last: int) -> pd.DataFrame:
    """Rows month-first .. month-last (inclusive), e.g. (11, 1) = M-11..M-1."""
    return wide.reindex(pd.period_range(month - first, month - last, freq="M"))


def _compound(w: pd.DataFrame, min_obs: int) -> pd.Series:
    return ((1 + w).prod(min_count=1) - 1).where(w.notna().sum() >= min_obs)


def _div(a: pd.Series, b: pd.Series) -> pd.Series:
    return a / b.where(b != 0)


def build(month: pd.Period, members: pd.DataFrame, returns: pd.DataFrame, fund_asof: pd.DataFrame,
          market_returns: pd.Series, mcap: pd.Series, fund_prev: pd.DataFrame | None = None) -> pd.DataFrame:
    """[month, ticker, *FEATURES, sector] for the members of `month`; numeric features ranked to (0, 1]."""
    mem = members[members["month"] == month].drop_duplicates("ticker").set_index("ticker")
    tickers = mem.index
    wide = returns[returns["month"] <= month].pivot_table(index="month", columns="ticker", values="ret")
    wide = wide.reindex(columns=tickers)
    w12 = _window(wide, month, 11, 0)
    mkt = market_returns.reindex(w12.index)

    f = fund_asof.pivot_table(index="ticker", columns="item", values="value").reindex(tickers)
    col = lambda item: f[item] if item in f else pd.Series(np.nan, index=tickers)
    assets, equity, ni = col("total_assets"), col("equity"), col("net_income")
    gross = col("gross_profit").fillna(col("revenue") - col("cost_of_revenue"))
    cap = mcap.reindex(tickers)
    prev_assets = pd.Series(np.nan, index=tickers)
    if fund_prev is not None and not fund_prev.empty:
        prev_assets = fund_prev[fund_prev["item"] == "total_assets"].set_index("ticker")["value"].reindex(tickers)

    x = pd.DataFrame(index=tickers)
    x["mom_12_1"] = _compound(_window(wide, month, 11, 1), MIN_OBS)
    x["mom_6_1"] = _compound(_window(wide, month, 5, 1), 4)
    x["rev_1"] = wide.reindex([month]).iloc[0] if month in wide.index else np.nan
    x["vol_12"] = w12.std().where(w12.notna().sum() >= MIN_OBS)
    mc = mkt - mkt.mean()
    beta = (w12.sub(w12.mean()).mul(mc, axis=0)).sum() / (mc ** 2).sum() if mkt.notna().all() else np.nan
    x["beta_12"] = pd.Series(beta, index=tickers).where(w12.notna().sum() >= MIN_OBS)
    x["size"] = np.log(cap.where(cap > 0))
    x["bm"] = _div(equity, cap)
    x["ey"] = _div(ni, cap)
    x["sp"] = _div(col("revenue"), cap)
    x["roe"] = _div(ni, equity.where(equity > 0))
    x["gp"] = _div(gross, assets)
    x["accruals"] = _div(ni - col("operating_cash_flow"), assets)
    x["leverage"] = 1 - _div(equity, assets)
    x["asset_growth"] = _div(assets, prev_assets) - 1

    out = x[FEATURES].rank(pct=True)
    out.insert(0, "month", month)
    out["sector"] = mem["sector"]
    return out.reset_index(names="ticker")[["month", "ticker", *FEATURES, "sector"]]


def target(returns: pd.DataFrame, month: pd.Period, tickers=None) -> pd.Series:
    """Return in month+1 minus that month's cross-sectional median (over `tickers` when given)."""
    nxt = returns[(returns["month"] == month + 1) & returns["ret"].notna()].set_index("ticker")["ret"]
    if tickers is not None:
        nxt = nxt[nxt.index.isin(tickers)]
    return (nxt - nxt.median()).rename("target")


def investable(panel: pd.DataFrame) -> pd.DataFrame:
    """Members that have a price in the formation month (a stock with no price cannot be bought).
    Without this, members missing on Yahoo (old delistings) get scored and then earn nothing."""
    return panel[panel["rev_1"].notna()]
