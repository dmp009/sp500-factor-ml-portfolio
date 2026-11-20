import pandas as pd

from app import charts as ch

MONTHS = pd.period_range("2020-01", periods=4, freq="M")
WIDE = pd.DataFrame({"model": [0.02, -0.01, 0.03, 0.0], "sp500tr": [0.01, 0.0, 0.02, -0.01]}, index=MONTHS)


def test_figures_build():
    assert len(ch.cumulative(WIDE, "t").data) == 2
    assert len(ch.drawdown(WIDE, "t").data) == 2
    sectors = pd.DataFrame({"sector": ["Energy", "Financials"], "portfolio": [0.6, 0.4], "index": [0.5, 0.5]})
    assert len(ch.sector_mix(sectors, "t").data) == 2
    assert len(ch.signed_bars(pd.Series({"Momentum": 0.01, "Value": -0.02}), "t").data) == 1
    imp = pd.DataFrame({"month": list(MONTHS) * 2, "feature": ["bm"] * 4 + ["size"] * 4, "shap": range(8)})
    assert len(ch.importance(imp, "t", top=2).data) == 2
    att = {"betas": {"mkt_rf": 1.0, "mom": 0.2}, "t_values": {"mkt_rf": 10.0, "mom": 2.0}}
    assert len(ch.loadings(att, "t").data) == 1
    assert len(ch.ic_bars(pd.Series([0.05, -0.02, 0.01, 0.03], index=MONTHS), "t").data) == 2


def test_strategy_colours_are_fixed():
    fig = ch.cumulative(WIDE[["sp500tr"]], "t")
    assert fig.data[0].line.color == ch.COLOURS["sp500tr"]
