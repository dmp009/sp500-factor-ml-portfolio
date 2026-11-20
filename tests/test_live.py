import pandas as pd
import pytest

from factorml import live


def rows(months, value=0.01):
    return pd.DataFrame({"month": pd.PeriodIndex(months, freq="M"), "prev_portfolio_return": value})


def test_live_append_only():
    old = rows(["2026-11", "2026-12"])
    with pytest.raises(ValueError):
        live.append(old, rows(["2026-12"], value=0.05))  # rewriting history
    out = live.append(old, rows(["2027-01"]))
    assert list(out["month"].astype(str)) == ["2026-11", "2026-12", "2027-01"]
    pd.testing.assert_frame_equal(out.iloc[:2].reset_index(drop=True), old)  # history is a prefix


def test_identical_reappend_is_noop():
    old = rows(["2026-11"])
    pd.testing.assert_frame_equal(live.append(old, rows(["2026-11"])), old)


def test_append_to_empty():
    assert len(live.append(pd.DataFrame(), rows(["2026-11"]))) == 1
