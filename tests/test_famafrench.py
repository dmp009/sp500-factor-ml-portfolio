from pathlib import Path

import numpy as np
import pandas as pd

from factorml import famafrench as ff

FIX = Path(__file__).parent / "fixtures"
FF5, MOM = (FIX / "ff5_small.csv").read_text(), (FIX / "mom_small.csv").read_text()


def test_parse_monthly_block_only():
    t = ff.parse_french_csv(FF5)
    assert list(t.columns) == ["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]
    assert list(t.index) == list(pd.period_range("2016-01", "2016-03", freq="M"))  # no annual 1964 rows
    assert np.isclose(t.loc[pd.Period("2016-01", "M"), "mkt_rf"], -0.0574)  # -5.74 percent in the file


def test_factors_join():
    f = ff.factors(FF5, MOM)
    assert list(f.columns) == ["month", "mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]
    assert len(f) == 3 and f["mom"].notna().all()
