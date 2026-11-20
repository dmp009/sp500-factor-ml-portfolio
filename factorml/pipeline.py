"""Orchestration: `backfill` (full history, run once locally) and `monthly` (the scheduled job).

    python -m factorml.pipeline backfill          # sources -> snapshot, tuning, walk-forward backtest
    python -m factorml.pipeline monthly [--month YYYY-MM]
    python -m factorml.pipeline report            # rewrite the latest monthly report

The monthly job writes nothing until every step and quality gate has passed. If a step fails, its
name and the error go to data/raw/run_error.json for the alert step of the workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yaml

from factorml import attribution, explain, famafrench, live, quality, report
from factorml import features as ft
from factorml import fundamentals as fu
from factorml import model as md
from factorml import performance as pm
from factorml import portfolio as pf
from factorml import prices as px
from factorml import universe as un
from factorml import warehouse as wh
from factorml.config import RAW, ROOT, SNAPSHOT, load, model_params, settings

ERROR_FILE = RAW / "run_error.json"
STRATEGIES = ("model", "factor_rule", "equal_weight", "sp500tr")


# ---------------------------------------------------------------- sources

class RealSources:
    """Network sources. With cache=True (local backfill) raw downloads are kept in data/raw/ (git-ignored)."""

    def __init__(self, cache: bool = False):
        self.cache, self._edgar = cache, None

    def _sec(self) -> fu.EdgarClient:
        if self._edgar is None:
            self._edgar = fu.EdgarClient(fu.resolve_user_agent())
        return self._edgar

    def _cached_json(self, path: Path, fetch):
        if self.cache and path.exists():
            return json.loads(path.read_text())
        data = fetch()
        if self.cache:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
        return data

    def components(self) -> pd.DataFrame:
        return un.parse_components((RAW / "sp500_components.csv").read_text())

    def current(self) -> pd.DataFrame:
        s = settings()
        r = requests.get(s["sources"]["wikipedia"], headers={"User-Agent": s["user_agent_default"]}, timeout=30)
        r.raise_for_status()
        return un.parse_current(r.text)

    def sec_tickers(self) -> dict[str, str]:
        d = self._cached_json(RAW / "sec" / "company_tickers.json",
                              lambda: self._sec().get_json(settings()["sources"]["sec_tickers"])) or {}
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in d.values()}

    def company(self, cik: str) -> tuple[str | None, int | None]:
        d = self._cached_json(RAW / "sec" / f"sub_{cik}.json", lambda: self._sec().get_json(
            f"https://data.sec.gov/submissions/CIK{cik}.json")) or {}
        sic = d.get("sic")
        return d.get("name"), int(sic) if sic else None

    def companyfacts(self, cik: str) -> dict | None:
        return self._cached_json(RAW / "sec" / f"CIK{cik}.json", lambda: self._sec().companyfacts(cik))

    def prices(self, tickers: list[str], start: str, end: str) -> dict[str, pd.DataFrame]:
        key = hashlib.sha256(json.dumps([sorted(tickers), start, end]).encode()).hexdigest()[:12]
        path = RAW / f"yahoo_{key}.pkl"
        if self.cache and path.exists():
            return pickle.loads(path.read_bytes())
        data = px.download(tickers, start, end)
        if self.cache:
            path.write_bytes(pickle.dumps(data))
        return data

    def french(self) -> tuple[str, str]:
        return famafrench.download()


# ---------------------------------------------------------------- building blocks

def last_closed(today: pd.Timestamp) -> pd.Period:
    return today.to_period("M") - 1


def _bench() -> str:
    return settings()["sources"]["benchmark"]


def _dim_security(ids: list[str], current: pd.DataFrame, src) -> pd.DataFrame:
    """ticker (security id), cik, name, sector: GICS from Wikipedia for current members, SEC SIC otherwise."""
    cur = current.assign(ticker=current["ticker"].map(un.security_ids(current["ticker"])))
    cur = cur.drop_duplicates("ticker").set_index("ticker")
    sec = None
    rows = []
    for t in ids:
        if t in cur.index:
            c = cur.loc[t]
            rows.append((t, c["cik"], c["name"], c["gics_sector"]))
            continue
        sec = sec if sec is not None else src.sec_tickers()
        cik = sec.get(t) or sec.get(t.replace(".", "-"))
        name, sic = src.company(cik) if cik else (None, None)
        rows.append((t, cik, name or t, un.sector_of(sic) if sic else "Other"))
    return pd.DataFrame(rows, columns=["ticker", "cik", "name", "sector"])


def _fund_panel(ciks, src) -> pd.DataFrame:
    parts = []
    for cik in sorted({c for c in ciks if isinstance(c, str)}):
        facts = src.companyfacts(cik)
        if facts:
            parts.append(fu.facts_panel(facts, cik))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["cik", "item", "period_end", "value", "filed"])


def _by_ticker(asof: pd.DataFrame, dim: pd.DataFrame) -> pd.DataFrame:
    """as_of rows are per CIK; one CIK can have several tickers (GOOG, GOOGL)."""
    return asof.merge(dim[["ticker", "cik"]].dropna(), on="cik")[["ticker", "item", "value", "period_end"]]


def _price_table(daily: dict, members: pd.DataFrame, fund: pd.DataFrame, dim: pd.DataFrame,
                 upto: pd.Period) -> pd.DataFrame:
    """[month, ticker, ret, close, mcap] up to `upto`; mcap only where the ticker is a member that month.
    Series listed under bad_yahoo_series in config/ticker_overrides.yaml are dropped (treated as missing)."""
    bad = list(load("ticker_overrides").get("bad_yahoo_series") or {})
    daily = {k: v.drop(columns=bad, errors="ignore") for k, v in daily.items()}
    rets = px.monthly_returns(daily["adj"])
    rets = rets[rets["month"] <= upto]
    close = daily["close"].resample("ME").last()
    close.index = close.index.to_period("M")
    shares_panel = fund[fund["item"] == "shares_outstanding"]
    caps = []
    for m in sorted(members["month"].unique()):
        if m not in close.index:
            continue
        sh = _by_ticker(fu.as_of(shares_panel, m), dim)
        sh = sh[sh["ticker"].isin(set(members.loc[members["month"] == m, "ticker"]))]
        mc = px.market_cap(close.loc[m], sh, daily["splits"])
        caps.append(pd.DataFrame({"month": m, "ticker": mc.index, "mcap": mc.to_numpy()}))
    cap = pd.concat(caps, ignore_index=True) if caps else pd.DataFrame(columns=["month", "ticker", "mcap"])
    return rets.merge(cap, on=["month", "ticker"], how="left")


def _features(months, members: pd.DataFrame, prices: pd.DataFrame, fund: pd.DataFrame,
              dim: pd.DataFrame) -> pd.DataFrame:
    """Feature rows for `months`, with the target column (NaN where the next month is not known yet)."""
    market = prices[prices["ticker"] == _bench()].set_index("month")["ret"]
    stocks = prices[prices["ticker"] != _bench()]
    sector = dim.set_index("ticker")["sector"]
    out = []
    for m in months:
        mem = members[members["month"] == m].assign(sector=lambda d: d["ticker"].map(sector))
        window = stocks[(stocks["month"] > m - 12) & (stocks["month"] <= m)]
        mcap = stocks[stocks["month"] == m].set_index("ticker")["mcap"]
        f = ft.build(m, mem, window, _by_ticker(fu.as_of(fund, m), dim), market, mcap,
                     _by_ticker(fu.as_of(fund, m - 12), dim))
        y = ft.target(stocks, m, tickers=mem["ticker"])
        out.append(f.assign(target=f["ticker"].map(y)))
    return pd.concat(out, ignore_index=True)


def _refresh_targets(panel: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Fill targets that became known (the month after them has closed since they were built)."""
    stocks = prices[prices["ticker"] != _bench()]
    panel = panel.copy()
    for m in panel.loc[panel["target"].isna(), "month"].unique():
        y = ft.target(stocks, m, tickers=panel.loc[panel["month"] == m, "ticker"])
        if len(y):
            idx = panel["month"] == m
            panel.loc[idx, "target"] = panel.loc[idx, "ticker"].map(y)
    return panel


def _shap_rows(m, model, X, keep_stocks: bool) -> pd.DataFrame:
    s = explain.shap_month(model, X)
    g = s.assign(shap=s["shap"].abs()).groupby("feature", as_index=False)["shap"].mean().assign(ticker="ALL")
    rows = pd.concat([g, s], ignore_index=True) if keep_stocks else g
    return rows.assign(month=m, expected_value=s.attrs["expected_value"])[
        ["month", "ticker", "feature", "shap", "expected_value"]]


def _bench_returns(prices: pd.DataFrame, months) -> pd.Series:
    return prices[prices["ticker"] == _bench()].set_index("month")["ret"].reindex(months)


def _ic_stats(scores: pd.DataFrame, panel: pd.DataFrame) -> dict:
    ic = md.information_coefficient(scores, panel).dropna()
    j = scores.merge(panel[["month", "ticker", "target"]], on=["month", "ticker"]).dropna(subset=["target"])
    j["decile"] = j.groupby("month")["score"].transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    spread = j.groupby("month").apply(lambda g: g.loc[g["decile"] == 9, "target"].mean()
                                      - g.loc[g["decile"] == 0, "target"].mean(), include_groups=False)
    return {"mean": float(ic.mean()), "t": float(ic.mean() / ic.std() * np.sqrt(len(ic))), "months": len(ic),
            "share_positive": float((ic > 0).mean()), "top_minus_bottom_decile_monthly": float(spread.mean())}


def _write_params(params: dict, validation_ic: float, until: str) -> None:
    text = (f"# LightGBM hyper-parameters. Chosen once by factorml.model.tune on months up to {until}\n"
            f"# (mean validation IC {validation_ic:.4f}) and frozen for the backtest and the live runs.\n")
    (ROOT / "config" / "model.yaml").write_text(text + yaml.safe_dump({"params": params}, sort_keys=False))


def _summary(perf: pd.DataFrame, factors: pd.DataFrame, ic: dict, params: dict, extra: dict) -> dict:
    wide = perf.pivot(index="month", columns="strategy", values="net")
    turn = perf.pivot(index="month", columns="strategy", values="turnover")
    f = factors.set_index("month")
    rf = f["rf"]
    out = {"metrics": {}, "attribution": {}}
    for s in STRATEGIES:
        if s in wide:
            out["metrics"][s] = pm.metrics(wide[s], wide["sp500tr"], rf, turn.get(s))
    for s in ("model", "factor_rule", "sp500tr"):
        r = attribution.regress(wide[s] - rf.reindex(wide.index), f)
        out["attribution"][s] = {**r, "reading": attribution.reading(r)}
    out.update({"ic": ic, "params": params, "model_version": md.version(params),
                "backtest": {"first_month": str(wide.index.min()), "last_month": str(wide.index.max()),
                             "months": len(wide)}, **extra})
    return out


def _save(tables: dict, summary: dict, snapshot: Path) -> None:
    wh.save(tables, snapshot)
    (snapshot / "summary.json").write_text(json.dumps(summary, indent=2, default=str))


# ---------------------------------------------------------------- backfill

STATE = RAW / "backfill_state.pkl"


def backfill(src=None, snapshot: Path = SNAPSHOT, today: pd.Timestamp | None = None, params: dict | None = None,
             cal: dict | None = None, stage: str = "all") -> dict | None:
    """stage 'data' builds the feature panel and keeps it in data/raw/; 'model' tunes, backtests and saves
    the snapshot from it; 'all' does both (each stage alone stays well under ten minutes)."""
    s = settings()
    cal, today = cal or s["calendar"], today or pd.Timestamp.today()
    last = last_closed(today)
    months = pd.period_range(cal["first_feature_month"], last, freq="M")
    if stage == "model":
        st = pickle.loads(STATE.read_bytes())
        members, dim, prices, fund, factors, panel = (st[k] for k in ("members", "dim", "prices", "fund", "factors",
                                                                        "panel"))
        return _backfill_model(members, dim, prices, fund, factors, panel, snapshot, today, params, cal, months, last)
    src = src or RealSources(cache=True)
    print(f"backfill {months[0]}..{last}", flush=True)

    current = src.current()
    raw = un.membership(src.components(), months, current=current)
    ids = un.security_ids(set(raw["ticker"]) | set(current["ticker"]))
    members = raw.assign(ticker=raw["ticker"].map(ids)).drop_duplicates(["month", "ticker"]).reset_index(drop=True)
    dim = _dim_security(sorted(members["ticker"].unique()), current, src)
    print(f"  {members['ticker'].nunique()} securities, {dim['cik'].notna().sum()} with a CIK", flush=True)

    daily = src.prices(sorted(dim["ticker"]) + [_bench()], cal["price_start"], str(today.date()))
    fund = _fund_panel(dim["cik"], src)
    factors = famafrench.factors(*src.french())
    prices = _price_table(daily, members, fund, dim, last)
    print(f"  prices {len(prices):,} rows, fundamentals {len(fund):,} rows", flush=True)

    panel = _features(months, members, prices, fund, dim)
    print(f"  features {len(panel):,} rows", flush=True)
    if stage == "data":
        RAW.mkdir(parents=True, exist_ok=True)
        STATE.write_bytes(pickle.dumps({"members": members, "dim": dim, "prices": prices, "fund": fund,
                                        "factors": factors, "panel": panel}))
        print(f"  data stage kept in {STATE.relative_to(ROOT)}", flush=True)
        return None
    return _backfill_model(members, dim, prices, fund, factors, panel, snapshot, today, params, cal, months, last)


def _backfill_model(members, dim, prices, fund, factors, panel, snapshot, today, params, cal, months, last) -> dict:
    s = settings()
    validation_ic = None
    if params is None:
        tuned = md.tune(ft.investable(panel), cal["tuning_until"])
        params, validation_ic = tuned["params"], tuned["validation_ic"]
        _write_params(params, validation_ic, cal["tuning_until"])
        print(f"  tuned: {params} (validation IC {validation_ic})", flush=True)

    shap_parts = []
    oos_last = panel["month"].max()
    scores = md.walk_forward(ft.investable(panel), cal["first_oos_month"], params, on_fit=lambda m, mod, X: shap_parts.append(
        _shap_rows(m, mod, X, keep_stocks=(m == oos_last))))
    oos = ft.investable(panel[panel["month"] >= pd.Period(cal["first_oos_month"], "M")])
    rule = md.factor_rule(oos)
    top_n, bps = s["portfolio"]["top_n"], s["portfolio"]["cost_bps_per_side"]
    hold = pf.weights(scores, top_n)
    stocks = prices[prices["ticker"] != _bench()]
    perf = []
    for name, w in (("model", hold), ("factor_rule", pf.weights(rule, top_n))):
        perf.append(pf.strategy_returns(w, stocks, bps).assign(strategy=name))
    earned = perf[0]["month"]
    priced = ft.investable(oos)[["month", "ticker"]]
    ew = pf.equal_weight_universe(priced, stocks)
    for name, r in (("equal_weight", ew.reindex(earned)), ("sp500tr", _bench_returns(prices, earned))):
        perf.append(pd.DataFrame({"month": earned.to_numpy(), "gross": r.to_numpy(), "cost": 0.0,
                                  "net": r.to_numpy(), "turnover": np.nan, "n_missing": 0, "strategy": name}))
    perf = pd.concat(perf, ignore_index=True)[["month", "strategy", "gross", "cost", "net", "turnover", "n_missing"]]

    surv = px.survivorship(members, stocks)
    flagged = px.flag_implausible(stocks, members)
    tables = {
        "dim_month": pd.DataFrame({"month": months, "year": months.year, "quarter": months.quarter}),
        "dim_security": dim,
        "dim_sector": pd.DataFrame({"sector": md.SECTORS}),
        "fact_membership": members,
        "fact_prices": prices,
        "fact_fundamentals": fund,
        "fact_features": panel,
        "fact_predictions": scores,
        "fact_holdings": hold.assign(source="backtest"),
        "fact_performance": perf,
        "fact_factors": factors[factors["month"] >= months[0] - 12],
        "fact_shap": pd.concat(shap_parts, ignore_index=True),
        "fact_live": pd.DataFrame(columns=["month", "model_version", "n_holdings", "turnover", "cost",
                                           "prev_portfolio_return", "sp500tr_return", "equal_weight_return",
                                           "factor_rule_return"]),
    }
    gate_rows = quality.gates(last, members, stocks, panel, today)
    coverage = {str(m): round(px.coverage(stocks, members, m), 4) for m in (months[0], months[len(months) // 2], last)}
    summary = _summary(perf, factors, _ic_stats(scores, panel), params, {
        "validation_ic": validation_ic, "survivorship": surv, "coverage": coverage, "data_through": str(last),
        "universe": {"securities": int(members["ticker"].nunique()), "with_cik": int(dim["cik"].notna().sum())},
        "live": {}, "gates": [list(r) for r in gate_rows], "flagged_series": flagged.round(4).to_dict("records")})
    _save(tables, summary, snapshot)
    quality.report(tables, gate_rows, surv, snapshot, flagged)
    print(f"  saved snapshot: backtest {summary['backtest']}, mean IC {summary['ic']['mean']:.4f}", flush=True)
    return summary


# ---------------------------------------------------------------- monthly

_step = {"name": "start"}


@contextmanager
def step(name: str):
    _step["name"] = name
    print(f"- {name}", flush=True)
    yield


def monthly(src=None, month: str | None = None, snapshot: Path = SNAPSHOT, today: pd.Timestamp | None = None) -> str:
    """Run one month. Returns 'done', or 'skipped' when the month is already covered."""
    src = src or RealSources(cache=False)
    s = settings()
    today = today or pd.Timestamp.today()
    m = pd.Period(month, "M") if month else last_closed(today)
    t = {name: wh.load(name, snapshot) for name in wh.TABLES}
    summary = json.loads((snapshot / "summary.json").read_text())
    backtest_end = t["fact_holdings"].loc[t["fact_holdings"]["source"] == "backtest", "month"].max()
    if m <= backtest_end or m in set(t["fact_live"]["month"]):
        print(f"{m} is already in the {'backtest' if m <= backtest_end else 'live record'}: nothing to do")
        return "skipped"

    with step("membership"):
        current = src.current()
        ids = un.security_ids(current["ticker"])
        mem_m = pd.DataFrame({"month": m, "ticker": current["ticker"].map(ids)}).drop_duplicates()
        members = pd.concat([t["fact_membership"], mem_m], ignore_index=True)
        new_ids = sorted(set(mem_m["ticker"]) - set(t["dim_security"]["ticker"]))
        dim = pd.concat([t["dim_security"], _dim_security(new_ids, current, src)], ignore_index=True)
    with step("fundamentals"):
        cur_ciks = dim.loc[dim["ticker"].isin(mem_m["ticker"]), "cik"]
        fresh = _fund_panel(cur_ciks, src)
        fund = pd.concat([t["fact_fundamentals"], fresh], ignore_index=True).drop_duplicates(
            ["cik", "item", "period_end", "filed"], keep="first").reset_index(drop=True)
    with step("prices"):
        daily = src.prices(sorted(mem_m["ticker"]) + [_bench()], str((m - 13).start_time.date()), str(today.date()))
        new = _price_table(daily, members[members["month"] >= m - 13], fund, dim, m)
        old = t["fact_prices"]
        known = set(zip(old["month"], old["ticker"], strict=True))
        add = new[[(a, b) not in known for a, b in zip(new["month"], new["ticker"], strict=True)]]
        prices = pd.concat([old, add], ignore_index=True)
    with step("factors"):
        factors = famafrench.factors(*src.french())
    with step("features"):
        feats = _features([m], members, prices, fund, dim)
        panel = _refresh_targets(pd.concat([t["fact_features"], feats], ignore_index=True), prices)
    with step("quality"):
        stocks = prices[prices["ticker"] != _bench()]
        gate_rows = quality.enforce(m, members, stocks, panel, today)
    with step("model"):
        params = model_params()
        shap_parts = []
        scores = md.walk_forward(ft.investable(panel), str(m), params,
                                 on_fit=lambda mm, mod, X: shap_parts.append(_shap_rows(mm, mod, X, True)))
    with step("portfolio"):
        top_n, bps = s["portfolio"]["top_n"], s["portfolio"]["cost_bps_per_side"]
        w = pf.weights(scores, top_n)
        hold_all = t["fact_holdings"]
        prev = hold_all[hold_all["month"] == m - 1]
        to = pf.turnover(prev.set_index("ticker")["weight"], w.set_index("ticker")["weight"])
        ret_m = stocks[stocks["month"] == m].set_index("ticker")["ret"]
        lv = t["fact_live"]
        prev_live = lv[lv["month"] == m - 1]
        prev_ret = np.nan
        if len(prev_live):
            gross = float((prev.set_index("ticker")["weight"] * ret_m.reindex(prev["ticker"]).fillna(0).to_numpy()).sum())
            prev_ret = gross - float(prev_live["cost"].iat[0])
        prev_panel = ft.investable(panel[panel["month"] == m - 1])
        rule_prev = pf.weights(md.factor_rule(prev_panel), top_n)
        mem_prev = prev_panel["ticker"]
        row = pd.DataFrame([{
            "month": m, "model_version": md.version(params), "n_holdings": len(w), "turnover": to,
            "cost": 2 * to * bps / 1e4, "prev_portfolio_return": prev_ret,
            "sp500tr_return": float(prices.loc[(prices["ticker"] == _bench()) & (prices["month"] == m), "ret"].iat[0]),
            "equal_weight_return": float(ret_m.reindex(mem_prev).fillna(0).mean()),
            "factor_rule_return": float(ret_m.reindex(rule_prev["ticker"]).fillna(0).mean()),
        }])
        live_tbl = live.append(lv if len(lv) else None, row)
    with step("report"):
        tables = {**t, "dim_security": dim, "fact_membership": members, "fact_prices": prices,
                  "fact_fundamentals": fund, "fact_features": panel,
                  "fact_predictions": pd.concat([t["fact_predictions"], scores], ignore_index=True),
                  "fact_holdings": pd.concat([hold_all, w.assign(source="live")], ignore_index=True),
                  "fact_factors": factors[factors["month"] >= t["dim_month"]["month"].min() - 12],
                  "fact_shap": pd.concat([t["fact_shap"][t["fact_shap"]["ticker"] == "ALL"], *shap_parts],
                                         ignore_index=True),
                  "fact_live": live_tbl,
                  "dim_month": pd.concat([t["dim_month"], pd.DataFrame(
                      {"month": [m], "year": [m.year], "quarter": [m.quarter]})], ignore_index=True)}
        summary["live"] = _live_summary(live_tbl)
        summary["data_through"] = str(m)
        summary["gates"] = [list(r) for r in gate_rows]
    with step("save"):
        _save(tables, summary, snapshot)
        quality.report(tables, gate_rows, px.survivorship(members, stocks), snapshot,
                       px.flag_implausible(stocks, members))
        report.monthly(m, snapshot)
    return "done"


def _live_summary(lv: pd.DataFrame) -> dict:
    r = lv.dropna(subset=["prev_portfolio_return"])
    if r.empty:
        return {"first_month": str(lv["month"].min()), "months_with_returns": 0}
    cum = lambda x: float((1 + x).prod() - 1)
    return {"first_month": str(lv["month"].min()), "months_with_returns": len(r),
            "cumulative": {"model": cum(r["prev_portfolio_return"]), "sp500tr": cum(r["sp500tr_return"]),
                           "equal_weight": cum(r["equal_weight_return"]), "factor_rule": cum(r["factor_rule_return"])}}


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="factorml.pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    bf = sub.add_parser("backfill")
    bf.add_argument("--stage", choices=["all", "data", "model"], default="all")
    mo = sub.add_parser("monthly")
    mo.add_argument("--month", help="YYYY-MM (default: last closed month)")
    sub.add_parser("report")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "backfill":
            backfill(stage=a.stage)
        elif a.cmd == "monthly":
            ERROR_FILE.unlink(missing_ok=True)
            print(monthly(month=a.month))
        else:
            print(report.monthly(None))
        return 0
    except Exception as e:
        RAW.mkdir(parents=True, exist_ok=True)
        ERROR_FILE.write_text(json.dumps({
            "step": _step["name"], "month": a.month if a.cmd == "monthly" and a.month else None,
            "error": f"{type(e).__name__}: {e}\n\n{traceback.format_exc()[-2500:]}"}))
        raise


if __name__ == "__main__":
    sys.exit(main())
