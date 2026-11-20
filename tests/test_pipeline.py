"""End-to-end: backfill then the monthly job on synthetic sources (no network)."""
import hashlib

import numpy as np
import pandas as pd
import pytest

from factorml import pipeline as pl
from factorml import quality
from factorml import warehouse as wh
from tests.test_model import FAST

N = 500
TICKERS = [f"T{i}" for i in range(N)]
SECTORS = ["Energy", "Financials", "Health Care", "Industrials", "Utilities"]
CAL = {"price_start": "2009-01-01", "first_feature_month": "2010-03", "first_oos_month": "2011-01",
       "tuning_until": "2010-12"}
MONTH_ENDS = pd.date_range("2009-01-01", "2012-12-31", freq="BME")


def _seed(t):
    return int(hashlib.md5(t.encode()).hexdigest()[:8], 16)


def _path(t):
    r = np.random.default_rng(_seed(t)).normal(0.008, 0.06, len(MONTH_ENDS))
    return pd.Series(100 * np.exp(np.cumsum(r)), index=MONTH_ENDS)


class Fake:
    def __init__(self, priced=None):
        self.priced = priced  # tickers Yahoo "returns" (None = all)

    def components(self):
        return pd.DataFrame({"date": pd.Timestamp("2009-01-02"), "ticker": TICKERS})

    def current(self):
        return pd.DataFrame({"ticker": TICKERS, "name": TICKERS, "cik": [f"{i + 1:010d}" for i in range(N)],
                             "gics_sector": [SECTORS[i % 5] for i in range(N)]})

    def sec_tickers(self):
        return {}

    def company(self, cik):
        return ("X", 3571)

    def companyfacts(self, cik):
        i = int(cik)
        rows = lambda base: [{"start": f"{y}-01-01", "end": f"{y}-12-31", "val": base * (1 + 0.05 * (y - 2008)),
                              "fy": y, "fp": "FY", "form": "10-K", "filed": f"{y + 1}-02-15"} for y in range(2008, 2012)]
        inst = lambda base: [{k: v for k, v in r.items() if k != "start"} for r in rows(base)]
        return {"facts": {"us-gaap": {
            "Revenues": {"units": {"USD": rows(1000 + i)}}, "NetIncomeLoss": {"units": {"USD": rows(50 + i % 40)}},
            "Assets": {"units": {"USD": inst(3000 + 3 * i)}}, "StockholdersEquity": {"units": {"USD": inst(900 + i)}},
            "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": rows(70)}}},
            "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": inst(10 + i)}}}}}

    def prices(self, tickers, start, end):
        idx = MONTH_ENDS[(MONTH_ENDS >= pd.Timestamp(start)) & (MONTH_ENDS <= pd.Timestamp(end))]
        keep = [t for t in tickers if self.priced is None or t in self.priced or t.startswith("^")]
        adj = pd.DataFrame({t: _path(t)[idx] for t in keep})
        return {"adj": adj, "close": adj.copy(), "splits": adj * 0.0}

    def french(self):
        months = pd.period_range("2009-01", "2012-12", freq="M")
        v = np.random.default_rng(7).normal(0, 2, (len(months), 6)).round(2)
        ff5 = ",Mkt-RF,SMB,HML,RMW,CMA,RF\n" + "\n".join(
            f"{m.strftime('%Y%m')}, {', '.join(str(x) for x in r[:5])}, 0.01" for m, r in zip(months, v, strict=True))
        mom = ",Mom\n" + "\n".join(f"{m.strftime('%Y%m')}, {r[5]}" for m, r in zip(months, v, strict=True))
        return ff5, mom


@pytest.fixture(scope="module")
def snap(tmp_path_factory):
    d = tmp_path_factory.mktemp("snapshot")
    pl.backfill(Fake(), snapshot=d, today=pd.Timestamp("2011-07-05"), params=FAST, cal=CAL)
    return d


def test_backfill_writes_all_tables(snap):
    con = wh.connect(snap)
    for t in wh.TABLES:
        con.execute(f"SELECT count(*) FROM {t}")
    hold = wh.load("fact_holdings", snap)
    assert hold["month"].max() == pd.Period("2011-06", "M") and (hold["source"] == "backtest").all()
    assert len(wh.load("fact_live", snap)) == 0


def test_rerun_is_noop(snap):
    today = pd.Timestamp("2011-08-02")
    assert pl.monthly(Fake(), snapshot=snap, today=today) == "done"
    assert pl.monthly(Fake(), snapshot=snap, today=today) == "skipped"
    lv = wh.load("fact_live", snap)
    assert list(lv["month"]) == [pd.Period("2011-07", "M")]
    assert (wh.load("fact_holdings", snap).query("source == 'live'")["month"] == pd.Period("2011-07", "M")).all()


def test_backtest_months_are_skipped(snap):
    assert pl.monthly(Fake(), month="2011-05", snapshot=snap, today=pd.Timestamp("2011-08-02")) == "skipped"


def test_gate_failure_writes_nothing(snap):
    files = lambda: {p: p.read_bytes() for p in snap.rglob("*") if p.is_file()}
    before = files()
    with pytest.raises(quality.GateError) as e:
        pl.monthly(Fake(priced=TICKERS[:400]), snapshot=snap, today=pd.Timestamp("2011-09-02"))
    assert e.value.gate == "price_coverage"
    assert files() == before
