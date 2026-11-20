"""Point-in-time S&P 500 membership.

History: fja05680/sp500 (MIT), one row per date the list changed, tickers comma-joined.
After the last dated row, the live job uses the current Wikipedia list (fetched at run time).
A ticker is a member in month M if it is in the last list dated on or before M's last day.
"""
from __future__ import annotations

import io

import pandas as pd

from factorml.config import load


def parse_components(csv_text: str) -> pd.DataFrame:
    raw = pd.read_csv(io.StringIO(csv_text))
    raw["date"] = pd.to_datetime(raw["date"])
    out = raw.assign(ticker=raw["tickers"].str.split(",")).explode("ticker")[["date", "ticker"]]
    out["ticker"] = out["ticker"].str.strip()
    return out.sort_values(["date", "ticker"]).reset_index(drop=True)


def parse_current(html: str) -> pd.DataFrame:
    t = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})[0]
    return pd.DataFrame({
        "ticker": t["Symbol"].astype(str).str.strip(),
        "name": t["Security"],
        "cik": t["CIK"].astype(int).astype(str).str.zfill(10),
        "gics_sector": t["GICS Sector"],
    })


def membership(components: pd.DataFrame, months: pd.PeriodIndex, current: pd.DataFrame | None = None) -> pd.DataFrame:
    lists = components.groupby("date")["ticker"].apply(list)
    dates, last = lists.index, lists.index.max()
    rows = []
    for m in months:
        end = m.to_timestamp(how="end")
        if current is not None and end > last:
            tickers = list(current["ticker"])
        else:
            i = dates.searchsorted(end, side="right") - 1
            if i < 0:
                continue
            tickers = lists.iloc[i]
        rows += [(m, t) for t in tickers]
    return pd.DataFrame(rows, columns=["month", "ticker"])


def security_ids(tickers, overrides: dict | None = None) -> dict[str, str]:
    """ticker -> security id; renamed tickers map to the current ticker so one company keeps one id."""
    renames = overrides if overrides is not None else load("ticker_overrides")["renames"]
    return {t: renames.get(t, t) for t in tickers}


def yahoo_symbol(ticker: str) -> str:
    return ticker.replace(".", "-")


def sector_of(sic: int) -> str:
    for row in load("sectors"):
        if any(lo <= sic <= hi for lo, hi in row["ranges"]):
            return row["sector"]
    return "Other"
