import json
from pathlib import Path

import pandas as pd
import pytest

from factorml import fundamentals as f

FACTS = json.loads((Path(__file__).parent / "fixtures" / "companyfacts_small.json").read_text())
PANEL = f.facts_panel(FACTS, "0000001234")


def at(month, item, panel=PANEL):
    a = f.as_of(panel, pd.Period(month, "M"))
    s = a.loc[a["item"] == item, "value"]
    return None if s.empty else s.iat[0]


def test_panel_annual_only_and_one_year_durations():
    rev = PANEL[PANEL["item"] == "revenue"]
    assert set(rev["value"]) == {400, 500}  # the Q1 10-Q is not annual
    assert set(PANEL["cik"]) == {"0000001234"}


def test_as_of_respects_filed():
    assert at("2015-01", "total_assets") is None  # FY2014 10-K filed 2015-02-20
    assert at("2015-02", "total_assets") == 2000
    assert at("2015-02", "revenue") == 500  # latest period, not the comparative
    a = f.as_of(PANEL, pd.Period("2015-03", "M"))
    assert a.loc[a["item"] == "shares_outstanding", "period_end"].iat[0] == pd.Timestamp("2015-02-10")


def test_restatement_no_leak():
    assert at("2015-06", "net_income") == 100
    panel = PANEL[~((PANEL["item"] == "net_income") & (PANEL["period_end"] == "2015-12-31"))]
    assert at("2016-03", "net_income", panel) == 90  # restated FY2014, known only from 2016-02
    assert at("2016-03", "net_income") == 120  # FY2015 is the latest period by then


def test_shares_use_latest_filing_including_quarterlies():
    assert at("2015-03", "shares_outstanding") == 1000
    assert at("2015-05", "shares_outstanding") == 990


def test_user_agent_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    monkeypatch.setenv("SEC_CONTACT", "x@y.z")
    assert f.resolve_user_agent(tmp_path / ".env").endswith("x@y.z")
    monkeypatch.delenv("SEC_CONTACT")
    with pytest.raises(RuntimeError):
        f.resolve_user_agent(tmp_path / ".env")


class FakeResp:
    def __init__(self, code, body=None):
        self.status_code, self._body = code, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_get_json_retries_429_and_handles_404():
    seq = [FakeResp(429), FakeResp(200, {"ok": 1}), FakeResp(404)]

    class S:
        def __init__(self):
            self.headers = {}

        def get(self, url, timeout):
            return seq.pop(0)

    c = f.EdgarClient("ua x@y.z", session=S(), sleep=lambda s: None)
    assert c.get_json("u1") == {"ok": 1}
    assert c.get_json("u2") is None  # no XBRL facts for this company


def test_fallback_tags_for_shares_and_cost():
    facts = {"facts": {"us-gaap": {
        "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [
            {"start": "2014-01-01", "end": "2014-12-31", "val": 700, "fy": 2014, "fp": "FY", "form": "10-K",
             "filed": "2015-02-20"}]}},
        "CostOfGoodsAndServicesSold": {"units": {"USD": [
            {"start": "2014-01-01", "end": "2014-12-31", "val": 300, "fy": 2014, "fp": "FY", "form": "10-K",
             "filed": "2015-02-20"}]}}}}}
    panel = f.facts_panel(facts, "0000000009")
    assert at("2015-03", "shares_outstanding", panel) == 700
    assert at("2015-03", "cost_of_revenue", panel) == 300
