import numpy as np

from factorml import explain as ex
from factorml import model as md
from tests.test_model import FAST, synthetic


def test_shap_sums_to_prediction():
    p = synthetic(n_months=6)
    X = md._X(p).set_index(p["ticker"] + "_" + p["month"].astype(str))
    m = md.fit(X, p["target"], FAST)
    s = ex.shap_month(m, X)
    total = s.groupby("ticker")["shap"].sum() + s.attrs["expected_value"]
    pred = np.asarray(m.predict(X))
    assert np.allclose(total.reindex(X.index).to_numpy(), pred)


def test_top_reasons_orders_by_size():
    import pandas as pd

    s = pd.DataFrame({"ticker": "A", "feature": ["mom_12_1", "bm", "size"], "shap": [0.004, -0.009, 0.001]})
    r = ex.top_reasons(s, "A", k=2)
    assert len(r) == 2 and r[0].startswith("Book-to-market") and "lowers" in r[0]
