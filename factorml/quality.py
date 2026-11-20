"""Quality gates for the monthly run. A failed gate stops the run before anything is written,
and the GitHub Actions job turns the failure into an issue (the alert)."""
from __future__ import annotations

import pandas as pd

from factorml.config import SNAPSHOT, load, settings
from factorml.prices import coverage


class GateError(Exception):
    def __init__(self, gate: str, detail: str):
        super().__init__(f"quality gate '{gate}' failed: {detail}")
        self.gate = gate


def gates(month: pd.Period, members: pd.DataFrame, returns: pd.DataFrame, features: pd.DataFrame,
          today: pd.Timestamp | None = None) -> list[tuple[str, bool, str]]:
    """[(gate, passed, detail)] in the order they are enforced."""
    g = settings()["gates"]
    today = today or pd.Timestamp.today()
    n = int((members["month"] == month).sum())
    cov = coverage(returns, members, month)
    mem = set(members.loc[members["month"] == month, "ticker"])
    r = returns[(returns["month"] == month) & returns["ticker"].isin(mem)].set_index("ticker")["ret"].dropna()
    big = r[r.abs() > g["max_abs_monthly_return"]].sort_values(key=abs, ascending=False)
    worst = float(r.abs().max()) if len(r) else 0.0
    nf = int((features["month"] == month).sum())
    return [
        ("month_closed", today.normalize() > month.to_timestamp(how="end").normalize(),
         f"{month} ends {month.to_timestamp(how='end').date()}, today is {today.date()}"),
        ("member_count", g["members_min"] <= n <= g["members_max"],
         f"{n} members (allowed {g['members_min']}-{g['members_max']})"),
        ("price_coverage", cov >= g["min_price_coverage"], f"{cov:.1%} of members priced (min {g['min_price_coverage']:.0%})"),
        # real moves beyond 80% happen (SNDK +143%, Jan 2026); a data error is one absurd value or many at once
        ("max_abs_return", worst <= g["hard_max_abs_monthly_return"] and len(big) <= g["max_big_moves"],
         f"{len(big)} members beyond {g['max_abs_monthly_return']:.0%} (max {g['max_big_moves']}), largest "
         f"{worst:.0%} (max {g['hard_max_abs_monthly_return']:.0%})"
         + (": " + ", ".join(f"{t} {v:+.0%}" for t, v in big.head(5).items()) if len(big) else "")),
        ("features_built", nf == n, f"{nf} feature rows for {n} members"),
    ]


def enforce(month, members, returns, features, today=None) -> list[tuple[str, bool, str]]:
    rows = gates(month, members, returns, features, today)
    for gate, ok, detail in rows:
        if not ok:
            raise GateError(gate, detail)
    return rows


def report(tables: dict[str, pd.DataFrame], gate_rows: list[tuple[str, bool, str]], survivorship: dict,
           snapshot=SNAPSHOT, flagged: pd.DataFrame | None = None) -> str:
    """Markdown data-quality report, also written to data/snapshot/data_quality_report.md."""
    lines = ["# Data quality report", "", "## Gates (latest month)", "", "| Gate | Result | Detail |", "|---|---|---|"]
    lines += [f"| {g} | {'pass' if ok else 'FAIL'} | {d} |" for g, ok, d in gate_rows]
    lines += ["", "## Tables", "", "| Table | Rows |", "|---|---:|"]
    lines += [f"| {t} | {len(df):,} |" for t, df in tables.items()]
    lines += ["", "## Survivorship", "",
              (f"{survivorship['n_missing']} of the tickers that were ever index members since the start have no "
              f"price on Yahoo ({survivorship['share_missing']:.1%}); they are mostly companies acquired or delisted "
              "years ago. Months where a held stock has no return are counted, not filled.")]
    excluded = load("ticker_overrides").get("bad_yahoo_series") or {}
    if excluded:
        lines += ["", "## Excluded price series", "", "| Ticker | Reason |", "|---|---|"]
        lines += [f"| {t} | {why} |" for t, why in excluded.items()]
    if flagged is not None and len(flagged):
        lines += ["", "## Series flagged for review", "",
                  ("Monthly volatility over member months above 40% with repeated +/-80% months, or long runs of "
                  "unchanged prices."), "", "| Ticker | Member months | Volatility | Moves beyond 80% |",
                  "|---|---:|---:|---:|"]
        lines += [f"| {r.ticker} | {r.n} | {r.std:.0%} | {r.big_moves} |" for r in flagged.itertuples()]
    text = "\n".join(lines) + "\n"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "data_quality_report.md").write_text(text, encoding="utf-8")
    return text
