"""Monthly Markdown report: the portfolio, why each stock is in it, the live record, the backtest."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from factorml import explain
from factorml import warehouse as wh
from factorml.config import ROOT, SNAPSHOT, settings

LABELS = {"model": "LightGBM model", "factor_rule": "Factor rule", "equal_weight": "Equal-weight universe",
          "sp500tr": "S&P 500 TR"}


def _pct(x) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{x:+.2%}"


def monthly(month: str | pd.Period | None = None, snapshot: Path = SNAPSHOT) -> str:
    hold = wh.load("fact_holdings", snapshot)
    m = pd.Period(month, "M") if month else hold["month"].max()
    summary = json.loads((snapshot / "summary.json").read_text())
    dim = wh.load("dim_security", snapshot).set_index("ticker")
    pred = wh.load("fact_predictions", snapshot)
    shap = wh.load("fact_shap", snapshot)
    shap_m = shap[(shap["month"] == m) & (shap["ticker"] != "ALL")]
    live = wh.load("fact_live", snapshot)

    h = hold[hold["month"] == m].merge(pred[pred["month"] == m][["ticker", "score", "rank"]], on="ticker")
    h = h.sort_values("rank")
    lines = [f"# Monthly report: {m}", "",
             (f"Portfolio formed at the close of {m}, held through {m + 1}. Model `{summary['model_version']}`, "
             f"data through {summary['data_through']}. Source: {'live run' if (h['source'] == 'live').any() else 'backtest'}."),
             "", "## Holdings (top 50, equal weight)", "", "| Rank | Ticker | Company | Sector | Main reasons |",
             "|---:|---|---|---|---|"]
    for r in h.itertuples():
        reasons = "; ".join(explain.top_reasons(shap_m, r.ticker, k=2)) if len(shap_m) else ""
        lines.append(f"| {r.rank} | {r.ticker} | {dim.at[r.ticker, 'name'] if r.ticker in dim.index else r.ticker} "
                     f"| {dim.at[r.ticker, 'sector'] if r.ticker in dim.index else ''} | {reasons} |")
    mix = h["ticker"].map(dim["sector"]).value_counts(normalize=True)
    lines += ["", "## Sector mix", "", "| Sector | Weight |", "|---|---:|"]
    lines += [f"| {k} | {v:.0%} |" for k, v in mix.items()]

    lines += ["", "## Live track record", ""]
    if live.empty:
        lines.append("The live record starts with the first scheduled run after the backtest.")
    else:
        lines += ["| Formed | Previous portfolio return | S&P 500 TR | Equal weight | Factor rule | Turnover |",
                  "|---|---:|---:|---:|---:|---:|"]
        lines += [f"| {r.month} | {_pct(r.prev_portfolio_return)} | {_pct(r.sp500tr_return)} | "
                  f"{_pct(r.equal_weight_return)} | {_pct(r.factor_rule_return)} | {r.turnover:.0%} |"
                  for r in live.itertuples()]

    bt = summary["backtest"]
    lines += ["", f"## Backtest ({bt['first_month']} to {bt['last_month']}, net of costs)", "",
              "| Strategy | CAGR | Volatility | Sharpe | Max drawdown | Info ratio vs S&P 500 |",
              "|---|---:|---:|---:|---:|---:|"]
    for k, v in summary["metrics"].items():
        ir = "" if k == "sp500tr" else f"{v['info_ratio']:.2f}"
        lines.append(f"| {LABELS[k]} | {v['cagr']:.1%} | {v['vol']:.1%} | {v['sharpe']:.2f} | {v['max_dd']:.1%} | {ir} |")
    ic = summary["ic"]
    lines += ["", (f"Mean monthly information coefficient {ic['mean']:.3f} (t = {ic['t']:.1f}, positive in "
              f"{ic['share_positive']:.0%} of {ic['months']} months)."), "",
              "**Attribution.** " + summary["attribution"]["model"]["reading"], "", f"_{settings()['disclaimer']}_", ""]
    text = "\n".join(lines)
    out_dir = ROOT / "reports" if snapshot == SNAPSHOT else snapshot / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{m}.md").write_text(text, encoding="utf-8")
    return text
