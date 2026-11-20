"""Quality gates for the monthly run. A failed gate stops the run before anything is written,
and the GitHub Actions job turns the failure into an issue (the alert)."""
from __future__ import annotations

import pandas as pd

from factorml.config import SNAPSHOT, settings
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
    r = returns.loc[returns["month"] == month, "ret"].dropna()
    worst = float(r.abs().max()) if len(r) else 0.0
    nf = int((features["month"] == month).sum())
    return [
        ("month_closed", today.normalize() > month.to_timestamp(how="end").normalize(),
         f"{month} ends {month.to_timestamp(how='end').date()}, today is {today.date()}"),
        ("member_count", g["members_min"] <= n <= g["members_max"],
         f"{n} members (allowed {g['members_min']}-{g['members_max']})"),
        ("price_coverage", cov >= g["min_price_coverage"], f"{cov:.1%} of members priced (min {g['min_price_coverage']:.0%})"),
        ("max_abs_return", worst <= g["max_abs_monthly_return"],
         f"largest absolute monthly return {worst:.1%} (max {g['max_abs_monthly_return']:.0%})"),
        ("features_built", nf == n, f"{nf} feature rows for {n} members"),
    ]


def enforce(month, members, returns, features, today=None) -> list[tuple[str, bool, str]]:
    rows = gates(month, members, returns, features, today)
    for gate, ok, detail in rows:
        if not ok:
            raise GateError(gate, detail)
    return rows


def report(tables: dict[str, pd.DataFrame], gate_rows: list[tuple[str, bool, str]], survivorship: dict) -> str:
    """Markdown data-quality report, also written to data/snapshot/data_quality_report.md."""
    lines = ["# Data quality report", "", "## Gates (latest month)", "", "| Gate | Result | Detail |", "|---|---|---|"]
    lines += [f"| {g} | {'pass' if ok else 'FAIL'} | {d} |" for g, ok, d in gate_rows]
    lines += ["", "## Tables", "", "| Table | Rows |", "|---|---:|"]
    lines += [f"| {t} | {len(df):,} |" for t, df in tables.items()]
    lines += ["", "## Survivorship", "",
              (f"{survivorship['n_missing']} of the tickers that were ever index members since the start have no "
              f"price on Yahoo ({survivorship['share_missing']:.1%}); they are mostly companies acquired or delisted "
              "years ago. Months where a held stock has no return are counted, not filled.")]
    text = "\n".join(lines) + "\n"
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    (SNAPSHOT / "data_quality_report.md").write_text(text, encoding="utf-8")
    return text
