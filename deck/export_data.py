"""Write deck/deck_data.json from the committed snapshot, so the deck script needs no Python."""
import json
from pathlib import Path

from factorml.explain import LABELS
from factorml.warehouse import load

ROOT = Path(__file__).resolve().parent.parent
s = json.loads((ROOT / "data/snapshot/summary.json").read_text())

perf = load("fact_performance").pivot_table(index="month", columns="strategy", values="net").sort_index()
growth = (1 + perf.fillna(0)).cumprod()
year_end = growth.groupby(growth.index.year).last()

shap = load("fact_shap")
shap = shap[shap["ticker"] == "ALL"].groupby("feature")["shap"].mean().sort_values(ascending=False)

out = {
    "summary": {k: s[k] for k in ("metrics", "ic", "backtest", "survivorship", "coverage", "universe", "gates")},
    "attribution": s["attribution"]["model"],
    "growth": {"years": [str(y) for y in year_end.index],
               **{c: [round(v, 3) for v in year_end[c]] for c in year_end.columns}},
    "shap": [{"label": LABELS.get(f, f), "value": round(v * 100, 3)} for f, v in shap.head(8).items()],
}
for m in out["summary"]["metrics"].values():  # JSON has no NaN (e.g. index turnover)
    for k, v in m.items():
        if v != v:
            m[k] = None
(ROOT / "deck/deck_data.json").write_text(json.dumps(out, indent=1))
print("wrote deck/deck_data.json")
