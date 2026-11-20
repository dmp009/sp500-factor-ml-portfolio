"""Daily adjusted closes from Yahoo Finance, turned into month-end total returns.

Yahoo throttles by IP, so downloads go in batches with exponential back-off; a batch that still
fails after the retries raises, and the monthly job's quality gate stops the run.
Missing prices are never filled: a delisted stock simply has no rows after its last month.
"""
from __future__ import annotations

import time

import pandas as pd

from factorml.config import settings
from factorml.universe import yahoo_symbol


def _yf_download(tickers, **kw):
    import yfinance as yf

    return yf.download(tickers, **kw)


def _closes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    closes = frame["Close"] if isinstance(frame.columns, pd.MultiIndex) else frame[["Close"]]
    return closes.dropna(how="all", axis=1)


def download(tickers: list[str], start: str, end: str, fetch=_yf_download, batch: int = 100,
             retries: int = 4, sleep=time.sleep) -> pd.DataFrame:
    """Daily adjusted close, one column per index ticker (fetched under its Yahoo symbol)."""
    back = {yahoo_symbol(t): t for t in tickers}
    symbols = list(back)
    parts = []
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        for attempt in range(retries + 1):
            try:
                closes = _closes(fetch(chunk, start=start, end=end, auto_adjust=True, progress=False, threads=True))
            except Exception:  # noqa: BLE001 - network errors and Yahoo rate limits look alike here
                closes = pd.DataFrame()
            if not closes.empty:
                parts.append(closes)
                break
            if attempt == retries:
                raise RuntimeError(f"Yahoo returned nothing for batch {i // batch + 1} after {retries} retries")
            sleep(2 ** (attempt + 1))
    out = pd.concat(parts, axis=1).rename(columns=back)
    out.index = pd.DatetimeIndex(out.index).tz_localize(None)
    return out.sort_index()


def monthly_returns(daily: pd.DataFrame) -> pd.DataFrame:
    """Long frame [month, ticker, ret, close]; ret is NaN for a ticker's first month."""
    close = daily.resample("ME").last()
    ret = close.pct_change(fill_method=None)
    out = pd.concat({"close": close.stack(), "ret": ret.stack(future_stack=True)}, axis=1).dropna(subset=["close"])
    out.index.names = ["date", "ticker"]
    out = out.reset_index()
    out["month"] = out["date"].dt.to_period("M")
    return out[["month", "ticker", "ret", "close"]].sort_values(["month", "ticker"]).reset_index(drop=True)


def benchmark(fetch=_yf_download) -> pd.Series:
    """Monthly total return of the S&P 500 Total Return index, indexed by month."""
    s = settings()
    sym = s["sources"]["benchmark"]
    daily = download([sym], s["calendar"]["price_start"], pd.Timestamp.today().strftime("%Y-%m-%d"), fetch=fetch)
    r = monthly_returns(daily)
    return r.set_index("month")["ret"].dropna().rename("sp500tr")


def coverage(returns: pd.DataFrame, members: pd.DataFrame, month) -> float:
    want = set(members.loc[members["month"] == month, "ticker"])
    have = set(returns.loc[(returns["month"] == month) & returns["ret"].notna(), "ticker"])
    return len(want & have) / len(want) if want else 0.0


def survivorship(members: pd.DataFrame, returns: pd.DataFrame) -> dict:
    """Index members with no price at all on Yahoo (mostly old delistings)."""
    want = set(members["ticker"])
    missing = want - set(returns["ticker"])
    return {"n_missing": len(missing), "share_missing": len(missing) / len(want)}
