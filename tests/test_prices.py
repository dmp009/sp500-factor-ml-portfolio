import numpy as np
import pandas as pd

from factorml import prices as p


def fake_frame(tickers, start="2016-01-01", end="2016-06-30"):
    idx = pd.bdate_range(start, end)
    cols = pd.MultiIndex.from_product([["Adj Close", "Close", "Stock Splits"], tickers])
    return pd.DataFrame(100.0, index=idx, columns=cols)


def test_batches_and_retries():
    calls, slept = [], []

    def fetch(tickers, **kw):
        calls.append(list(tickers))
        if len(calls) == 1:
            raise ConnectionError("rate limited")
        return fake_frame(tickers)

    out = p.download([f"T{i}" for i in range(250)] + ["BRK.B"], "2016-01-01", "2016-06-30",
                     fetch=fetch, sleep=slept.append)
    assert len(calls) == 4  # 251 tickers in batches of 100 = 3 calls, plus one retry
    assert slept == [2]
    assert set(out) == {"adj", "close", "splits"}
    assert "BRK.B" in out["adj"].columns  # fetched as BRK-B, returned under the index ticker
    assert out["adj"].shape[1] == 251 and out["splits"].shape[1] == 251


def test_empty_batch_is_retried_then_fails():
    slept = []
    try:
        p.download(["A"], "2016-01-01", "2016-02-01", fetch=lambda t, **kw: pd.DataFrame(), sleep=slept.append)
        raise AssertionError("expected failure")
    except RuntimeError:
        pass
    assert slept == [2, 4, 8, 16]


def daily(values, months):
    idx = pd.DatetimeIndex([pd.Period(m, "M").to_timestamp(how="end").normalize() for m in months])
    return pd.DataFrame({"X": values}, index=idx)


def test_monthly_return_math():
    r = p.monthly_returns(daily([100, 110, 99], ["2016-01", "2016-02", "2016-03"]))
    got = r.set_index("month")["ret"]
    assert np.isclose(got[pd.Period("2016-02", "M")], 0.10)
    assert np.isclose(got[pd.Period("2016-03", "M")], -0.10)


def test_delisted_not_filled():
    d = pd.DataFrame({"X": [10.0] * 3 + [np.nan] * 3, "Y": [20.0] * 6},
                     index=pd.DatetimeIndex(["2016-02-29", "2016-03-31", "2016-04-29", "2016-05-31",
                                             "2016-06-30", "2016-07-29"]))
    r = p.monthly_returns(d)
    assert r.loc[r["ticker"] == "X", "month"].max() == pd.Period("2016-04", "M")
    assert len(r[r["ticker"] == "Y"]) == 6


def test_coverage():
    m = pd.Period("2016-04", "M")
    members = pd.DataFrame({"month": m, "ticker": [f"T{i}" for i in range(50)]})
    rets = pd.DataFrame({"month": m, "ticker": [f"T{i}" for i in range(49)], "ret": 0.01})
    assert p.coverage(rets, members, m) == 0.98


def test_survivorship():
    m = pd.Period("2016-04", "M")
    members = pd.DataFrame({"month": m, "ticker": ["A", "B", "C", "D"]})
    rets = pd.DataFrame({"month": m, "ticker": ["A", "B", "C"], "ret": 0.0})
    assert p.survivorship(members, rets) == {"n_missing": 1, "share_missing": 0.25}


def test_market_cap_restates_shares_for_later_splits():
    # 1,000 shares reported at 2020-06-27; 4:1 split on 2020-08-31; Yahoo close is split-adjusted (125 ~ 500/4)
    splits = pd.DataFrame({"AAPL": [0.0, 4.0, 0.0]},
                          index=pd.DatetimeIndex(["2020-06-30", "2020-08-31", "2021-06-30"]))
    shares = pd.DataFrame({"ticker": ["AAPL"], "value": [1000.0], "period_end": [pd.Timestamp("2020-06-27")]})
    close = pd.Series({"AAPL": 125.0})
    assert p.market_cap(close, shares, splits)["AAPL"] == 500_000  # 125 * 1,000 * 4
