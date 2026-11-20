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


FIELDS = {"adj": "Adj Close", "close": "Close", "splits": "Stock Splits"}


def _fields(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """adj (dividend+split adjusted, for returns), close (split adjusted only), splits (ratio on split days)."""
    if frame is None or frame.empty or not isinstance(frame.columns, pd.MultiIndex) or "Adj Close" not in frame:
        return {}
    adj = frame["Adj Close"].dropna(how="all", axis=1)
    if adj.empty:
        return {}
    out = {"adj": adj, "close": frame["Close"][adj.columns]}
    splits = frame["Stock Splits"] if "Stock Splits" in frame else pd.DataFrame(index=adj.index)
    out["splits"] = splits.reindex(columns=adj.columns).fillna(0.0)
    return out


def download(tickers: list[str], start: str, end: str, fetch=_yf_download, batch: int = 100,
             retries: int = 4, sleep=time.sleep) -> dict[str, pd.DataFrame]:
    """{'adj', 'close', 'splits'}: daily frames, one column per index ticker (fetched under its Yahoo symbol)."""
    back = {yahoo_symbol(t): t for t in tickers}
    symbols = list(back)
    parts: dict[str, list] = {k: [] for k in FIELDS}
    for i in range(0, len(symbols), batch):
        chunk = symbols[i:i + batch]
        for attempt in range(retries + 1):
            try:
                got = _fields(fetch(chunk, start=start, end=end, auto_adjust=False, actions=True, progress=False,
                                    threads=True))
            except Exception:  # noqa: BLE001 - network errors and Yahoo rate limits look alike here
                got = {}
            if got:
                for k in FIELDS:
                    parts[k].append(got[k])
                break
            if attempt == retries:
                raise RuntimeError(f"Yahoo returned nothing for batch {i // batch + 1} after {retries} retries")
            sleep(2 ** (attempt + 1))
    out = {}
    for k in FIELDS:
        df = pd.concat(parts[k], axis=1).rename(columns=back)
        df.index = pd.DatetimeIndex(df.index).tz_localize(None)
        out[k] = df.sort_index()
    return out


def market_cap(close: pd.Series, shares: pd.DataFrame, splits: pd.DataFrame) -> pd.Series:
    """Market value per ticker: split-adjusted close x reported shares x every split after the share-count date.

    SEC share counts are as reported, Yahoo closes are restated for all later splits; the split product puts
    both on the same basis (without it, Apple before its 2020 4:1 split would look 4x smaller).
    """
    out = {}
    for t, n, d in shares[["ticker", "value", "period_end"]].itertuples(index=False):
        if t not in close.index or pd.isna(close[t]):
            continue
        s = splits[t] if t in splits else pd.Series(dtype=float)
        later = s[(s.index > d) & (s > 0)]
        out[t] = float(close[t]) * n * float(later.prod() if len(later) else 1.0)
    return pd.Series(out, dtype=float)


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
    r = monthly_returns(daily["adj"])
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
