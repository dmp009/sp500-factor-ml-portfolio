"""Point-in-time fundamentals from SEC XBRL companyfacts.

Every value carries the date its filing reached EDGAR (`filed`). `as_of(month)` only sees filings
made on or before the month's last day, so a restatement filed later never leaks backwards.
Client and User-Agent rules are adapted from sec-filings-ai-analyst (SEC asks for a contact, max 10 req/s).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

from factorml.config import ROOT, settings

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
TIMEOUT, MAX_RETRIES = 30, 3

# item -> ("taxonomy:Tag" in order of preference, kind). Flow items need a ~1-year duration.
ITEMS = {
    "revenue": (["us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                 "us-gaap:SalesRevenueNet", "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax"], "flow"),
    "cost_of_revenue": (["us-gaap:CostOfRevenue", "us-gaap:CostOfGoodsAndServicesSold", "us-gaap:CostOfGoodsSold"],
                        "flow"),
    "gross_profit": (["us-gaap:GrossProfit"], "flow"),
    "net_income": (["us-gaap:NetIncomeLoss"], "flow"),
    "operating_cash_flow": (["us-gaap:NetCashProvidedByUsedInOperatingActivities"], "flow"),
    "total_assets": (["us-gaap:Assets"], "stock"),
    "total_liabilities": (["us-gaap:Liabilities"], "stock"),
    "equity": (["us-gaap:StockholdersEquity",
                "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], "stock"),
    # dei cover-page count is missing for multi-class issuers (e.g. Alphabet), hence the us-gaap fallbacks
    "shares_outstanding": (["dei:EntityCommonStockSharesOutstanding", "us-gaap:CommonStockSharesOutstanding",
                            "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"], "shares"),
}
ANNUAL = {"10-K", "10-K/A", "10-KT"}
QUARTERLY = {"10-Q", "10-Q/A"}


def _rows(facts: dict, name: str) -> list[dict]:
    taxonomy, tag = name.split(":")
    units = facts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {})
    return units.get("USD") or units.get("shares") or []


def facts_panel(companyfacts: dict, cik: str) -> pd.DataFrame:
    """Long frame [cik, item, period_end, value, filed]: annual values (shares: also quarterly cover pages)."""
    out = []
    for item, (tags, kind) in ITEMS.items():
        seen: set[tuple] = set()
        for tag in tags:  # earlier tags win for the same (period_end, filed)
            for r in _rows(companyfacts, tag):
                form = r.get("form", "")
                if kind == "shares":
                    if form not in ANNUAL | QUARTERLY:
                        continue
                elif form not in ANNUAL or r.get("fp") != "FY":
                    continue
                if kind == "flow":
                    if "start" not in r:
                        continue
                    days = (pd.Timestamp(r["end"]) - pd.Timestamp(r["start"])).days
                    if not 330 <= days <= 400:
                        continue
                key = (r["end"], r["filed"])
                if key in seen:
                    continue
                seen.add(key)
                out.append((cik, item, r["end"], float(r["val"]), r["filed"]))
    df = pd.DataFrame(out, columns=["cik", "item", "period_end", "value", "filed"])
    df["period_end"] = pd.to_datetime(df["period_end"])
    df["filed"] = pd.to_datetime(df["filed"])
    return df


def as_of(panel: pd.DataFrame, month: pd.Period) -> pd.DataFrame:
    """[cik, item, value]: latest period known at month end; for that period, the latest filing of it."""
    known = panel[panel["filed"] <= month.to_timestamp(how="end")]
    if known.empty:
        return pd.DataFrame(columns=["cik", "item", "value"])
    last = known.sort_values(["period_end", "filed"]).groupby(["cik", "item"]).tail(1)
    return last[["cik", "item", "value"]].reset_index(drop=True)


def _read_env_file(path: Path, key: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip().strip("'\"") or None
    return None


def resolve_user_agent(env_file: Path | None = None) -> str:
    """SEC_USER_AGENT verbatim, else '<default> <SEC_CONTACT>' (env or .env), else error."""
    ua = os.environ.get("SEC_USER_AGENT")
    if ua:
        return ua
    contact = os.environ.get("SEC_CONTACT") or _read_env_file(env_file or ROOT / ".env", "SEC_CONTACT")
    if not contact:
        raise RuntimeError("Set SEC_CONTACT (env or .env): the SEC requires a contact in the User-Agent")
    return f"{settings()['user_agent_default']} {contact}"


class RateLimiter:
    """Minimum spacing of 1/max_rps between calls."""

    def __init__(self, max_rps: float = 8, clock=time.monotonic, sleep=time.sleep):
        self.interval, self._clock, self._sleep, self._last = 1.0 / max_rps, clock, sleep, None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None and (delay := self._last + self.interval - now) > 0:
            self._sleep(delay)
            now = self._clock()
        self._last = now


class EdgarClient:
    def __init__(self, user_agent: str, max_rps: float = 8, session=None, sleep=time.sleep):
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._limiter, self._sleep = RateLimiter(max_rps, sleep=sleep), sleep

    def get_json(self, url: str) -> dict | None:
        """Parsed JSON; None on 404 (company without XBRL facts). Retries 429/5xx with back-off."""
        for attempt in range(MAX_RETRIES + 1):
            self._limiter.wait()
            resp = self.session.get(url, timeout=TIMEOUT)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                self._sleep(2.0 ** attempt)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        return None

    def companyfacts(self, cik: str) -> dict | None:
        return self.get_json(FACTS_URL.format(cik=cik))
