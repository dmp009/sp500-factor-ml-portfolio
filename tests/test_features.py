import numpy as np
import pandas as pd

from factorml import features as ft
from factorml import fundamentals as fu

M = pd.Period("2016-12", "M")
MONTHS = pd.period_range("2015-01", "2017-06", freq="M")
TICKERS = [f"T{i}" for i in range(20)]
rng = np.random.default_rng(0)


def returns_frame():
    rows = [(m, t, rng.normal(0.01, 0.05)) for m in MONTHS for t in TICKERS]
    return pd.DataFrame(rows, columns=["month", "ticker", "ret"])


def panel():
    rows = []
    for i, t in enumerate(TICKERS):
        for fy, filed in [(2014, "2015-02-20"), (2015, "2016-02-20"), (2016, "2017-02-20")]:
            end = pd.Timestamp(f"{fy}-12-31")
            for item, v in {"revenue": 100 + i, "net_income": 10 + i, "total_assets": 500 + 10 * i + fy,
                            "equity": 200 + i, "operating_cash_flow": 12 + i, "cost_of_revenue": 60}.items():
                rows.append((t, item, end, float(v), pd.Timestamp(filed)))
    return pd.DataFrame(rows, columns=["cik", "item", "period_end", "value", "filed"])


def build(rets, pan, month=M):
    members = pd.DataFrame({"month": month, "ticker": TICKERS, "sector": "Industrials"})
    fund = fu.as_of(pan, month).rename(columns={"cik": "ticker"})
    prev = fu.as_of(pan, month - 12).rename(columns={"cik": "ticker"})
    mkt = rets.groupby("month")["ret"].mean()
    mcap = pd.Series({t: 1e9 * (i + 1) for i, t in enumerate(TICKERS)})
    return ft.build(month, members, rets, fund, mkt, mcap, prev)


def test_no_look_ahead():
    rets, pan = returns_frame(), panel()
    base = build(rets, pan)
    rets2 = rets.copy()
    rets2.loc[rets2["month"] > M, "ret"] = 9.9
    pan2 = pan.copy()
    pan2.loc[pan2["filed"] > M.to_timestamp(how="end"), "value"] = -1e6
    pd.testing.assert_frame_equal(base, build(rets2, pan2))


def test_mom_12_1_skips_last_month():
    rets = returns_frame()
    base = build(rets, panel()).set_index("ticker")["mom_12_1"]
    bumped = rets.copy()
    bumped.loc[(bumped["month"] == M) & (bumped["ticker"] == "T0"), "ret"] = 5.0  # month M itself
    assert build(bumped, panel()).set_index("ticker")["mom_12_1"].equals(base)
    bumped.loc[(bumped["month"] == M - 1) & (bumped["ticker"] == "T0"), "ret"] = 5.0  # month M-1 counts
    assert build(bumped, panel()).set_index("ticker").loc["T0", "mom_12_1"] == 1.0


def test_ranks_in_unit_interval():
    out = build(returns_frame(), panel())
    assert list(out.columns) == ["month", "ticker", *ft.FEATURES, "sector"]
    v = out[ft.FEATURES].to_numpy()
    assert np.nanmin(v) > 0 and np.nanmax(v) <= 1


def test_target_is_next_month_minus_median():
    rets = pd.DataFrame({"month": [M + 1] * 3 + [M] * 3, "ticker": ["A", "B", "C"] * 2,
                         "ret": [0.10, 0.02, -0.04, 0.5, 0.5, 0.5]})
    y = ft.target(rets, M)
    assert np.allclose(y[["A", "B", "C"]], [0.08, 0.0, -0.06])


def test_investable_needs_a_price_at_formation():
    p = pd.DataFrame({"month": M, "ticker": ["A", "B"], "rev_1": [0.5, np.nan]})
    assert list(ft.investable(p)["ticker"]) == ["A"]
