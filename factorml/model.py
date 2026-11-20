"""Walk-forward LightGBM ranker, a transparent factor rule, and the information coefficient.

The score for month M comes from a model trained on months <= M-2: the target of M-1 is the
return of M, which is only complete at M's close, so one month is left out as a buffer.
"""
from __future__ import annotations

import hashlib
import itertools
import json

import pandas as pd

from factorml.features import FEATURES

SECTORS = ["Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy", "Financials",
           "Health Care", "Industrials", "Information Technology", "Materials", "Real Estate", "Utilities", "Other"]
RULE = ["mom_12_1", "gp", "bm"]  # momentum, gross profitability, value


def _X(panel: pd.DataFrame) -> pd.DataFrame:
    X = panel[FEATURES].copy()
    X["sector"] = pd.Categorical(panel["sector"].fillna("Other"), categories=SECTORS)
    return X


def version(params: dict) -> str:
    return "lgbm-" + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]


def fit(X: pd.DataFrame, y: pd.Series, params: dict):
    import lightgbm as lgb

    m = lgb.LGBMRegressor(**{"random_state": 0, "deterministic": True, "force_row_wise": True, **params})
    return m.fit(X, y, categorical_feature=["sector"])


def _ranked(df: pd.DataFrame) -> pd.DataFrame:
    df["rank"] = df.groupby("month")["score"].rank(ascending=False, method="first").astype(int)
    return df


def walk_forward(panel: pd.DataFrame, first_oos: str, params: dict, on_fit=None) -> pd.DataFrame:
    """[month, ticker, score, rank, model_version] for every month >= first_oos (expanding window).

    on_fit(month, model, X_test) is called after each fit (X_test is indexed by ticker), e.g. for SHAP.
    """
    months = sorted(panel["month"].unique())
    out = []
    for m in [m for m in months if m >= pd.Period(first_oos, "M")]:
        train = panel[(panel["month"] <= m - 2) & panel["target"].notna()]
        test = panel[panel["month"] == m]
        if train.empty or test.empty:
            continue
        model = fit(_X(train), train["target"], params)
        X_test = _X(test).set_axis(test["ticker"].to_numpy())
        out.append(pd.DataFrame({"month": m, "ticker": test["ticker"].to_numpy(), "score": model.predict(X_test)}))
        if on_fit:
            on_fit(m, model, X_test)
    res = _ranked(pd.concat(out, ignore_index=True))
    res["model_version"] = version(params)
    return res


def factor_rule(panel: pd.DataFrame) -> pd.DataFrame:
    """Baseline: mean of the momentum, gross-profitability and book-to-market ranks."""
    df = panel[["month", "ticker"]].copy()
    df["score"] = panel[RULE].mean(axis=1)
    return _ranked(df.dropna(subset=["score"]).reset_index(drop=True))


def information_coefficient(scores: pd.DataFrame, realised: pd.DataFrame) -> pd.Series:
    """Spearman correlation of score and realised target, per month."""
    j = scores[["month", "ticker", "score"]].merge(realised[["month", "ticker", "target"]], on=["month", "ticker"])
    j = j.dropna(subset=["target"])
    return j.groupby("month").apply(lambda g: g["score"].corr(g["target"], method="spearman")).rename("ic")


def tune(panel: pd.DataFrame, until: str = "2012-12") -> dict:
    """Small grid, scored by mean IC on the last 12 months before `until`; run once, then frozen."""
    end = pd.Period(until, "M")
    sample = panel[panel["month"] <= end]
    base = {"n_estimators": 300, "learning_rate": 0.03, "subsample": 0.8, "subsample_freq": 1,
            "colsample_bytree": 0.8, "random_state": 0, "verbose": -1}
    best, best_ic = None, -1.0
    for leaves, child in itertools.product([7, 15, 31], [100, 200, 400]):
        params = {**base, "num_leaves": leaves, "min_child_samples": child}
        s = walk_forward(sample, str(end - 11), params)
        ic = information_coefficient(s, sample).mean()
        if ic > best_ic:
            best, best_ic = params, ic
    return {"params": best, "validation_ic": round(float(best_ic), 4)}
