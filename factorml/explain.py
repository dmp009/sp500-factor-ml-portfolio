"""Why the model likes a stock: TreeSHAP contributions from LightGBM itself (pred_contrib).

Each contribution is in target units (monthly return relative to the median); per stock they add
up, together with the expected value, to the model's score.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LABELS = {
    "mom_12_1": "12-1 month momentum", "mom_6_1": "6-1 month momentum", "rev_1": "Last-month return",
    "vol_12": "12-month volatility", "beta_12": "12-month market beta", "size": "Market value",
    "bm": "Book-to-market", "ey": "Earnings yield", "sp": "Sales-to-price", "roe": "Return on equity",
    "gp": "Gross profitability", "accruals": "Accruals", "leverage": "Leverage", "asset_growth": "Asset growth",
    "sector": "Sector",
}


def shap_month(model, X: pd.DataFrame) -> pd.DataFrame:
    """Long [ticker, feature, shap] for the rows of X (index = ticker); attrs['expected_value'] = base score."""
    contrib = np.asarray(model.predict(X, pred_contrib=True))
    wide = pd.DataFrame(contrib[:, :-1], index=X.index, columns=X.columns)
    out = wide.rename_axis("ticker").reset_index().melt(id_vars="ticker", var_name="feature", value_name="shap")
    out.attrs["expected_value"] = float(contrib[0, -1])
    return out


def top_reasons(shap_df: pd.DataFrame, ticker: str, k: int = 3) -> list[str]:
    s = shap_df[shap_df["ticker"] == ticker]
    s = s.reindex(s["shap"].abs().sort_values(ascending=False).index).head(k)
    return [f"{LABELS.get(f, f)} {'raises' if v > 0 else 'lowers'} the expected relative return by "
            f"{abs(v) * 100:.2f} pp" for f, v in zip(s["feature"], s["shap"], strict=True)]
