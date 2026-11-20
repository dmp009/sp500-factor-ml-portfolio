"""Pure plotly figure builders (no Streamlit imports). One y-axis per chart; each strategy keeps its colour."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from factorml.explain import LABELS

# Sober portfolio palette, shared with .streamlit/config.toml (validated with the dataviz palette checker).
BLUE, GOLD, GREEN, PURPLE, RED, INK, GREY, GRID = ("#2558A8", "#B7791F", "#1F9D55", "#7C3AED", "#C2362B", "#0B0D10",
                                                   "#9AA5B4", "#E5E7EB")
COLOURS = {"model": BLUE, "sp500tr": GOLD, "factor_rule": GREEN, "equal_weight": PURPLE}
NAMES = {"model": "LightGBM model", "sp500tr": "S&P 500 TR", "factor_rule": "Factor rule",
         "equal_weight": "Equal-weight universe"}
FACTOR_NAMES = {"mkt_rf": "Market", "smb": "Size (small)", "hml": "Value", "rmw": "Profitability",
                "cma": "Investment (conservative)", "mom": "Momentum"}
_LAYOUT = {
    "margin": {"l": 10, "r": 10, "t": 50, "b": 10},
    "template": "plotly_white",
    "colorway": [BLUE, GOLD, GREEN, PURPLE, RED, "#0E9AA7", "#E8590C", "#DB2777"],
    "font": {"family": "Inter, Arial, sans-serif", "color": INK, "size": 13},
    "title_x": 0, "title_xanchor": "left", "title_font_size": 16,
    "legend": {"orientation": "h", "y": -0.12, "yanchor": "top", "x": 0, "xanchor": "left"},
    "xaxis": {"gridcolor": GRID, "zeroline": False},
    "yaxis": {"gridcolor": GRID, "zeroline": False},
    "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
    "hovermode": "x unified",
}


def _x(index) -> list:
    return [p.to_timestamp() for p in index]


def cumulative(wide: pd.DataFrame, title: str) -> go.Figure:
    """Growth of 1 dollar, one line per strategy (columns of `wide`: monthly net returns)."""
    fig = go.Figure()
    for s in wide.columns:
        g = (1 + wide[s].fillna(0)).cumprod()
        fig.add_trace(go.Scatter(x=_x(wide.index), y=g, name=NAMES.get(s, s), mode="lines",
                                 line={"color": COLOURS.get(s, GREY), "width": 2},
                                 hovertemplate="$%{y:.2f}"))
    fig.update_layout(title=title, **_LAYOUT)
    fig.update_yaxes(tickprefix="$")
    return fig


def drawdown(wide: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    for s in wide.columns:
        w = (1 + wide[s].fillna(0)).cumprod()
        dd = w / w.cummax().clip(lower=1.0) - 1
        fig.add_trace(go.Scatter(x=_x(wide.index), y=dd, name=NAMES.get(s, s), mode="lines",
                                 line={"color": COLOURS.get(s, GREY), "width": 2}, hovertemplate="%{y:.1%}"))
    fig.update_layout(title=title, **_LAYOUT)
    fig.update_yaxes(tickformat=".0%")
    return fig


def sector_mix(df: pd.DataFrame, title: str) -> go.Figure:
    """df: sector, portfolio, index (weights). Horizontal bars, portfolio next to the index."""
    d = df.sort_values("portfolio")
    fig = go.Figure()
    for col, name, colour in (("index", "S&P 500 members (equal count)", GREY), ("portfolio", "Portfolio", BLUE)):
        fig.add_trace(go.Bar(y=d["sector"], x=d[col], name=name, orientation="h", marker_color=colour,
                             hovertemplate="%{y}: %{x:.0%}<extra>" + name + "</extra>"))
    fig.update_layout(title=title, barmode="group", bargap=0.25, bargroupgap=0.1,
                      **{**_LAYOUT, "hovermode": "closest"})
    fig.update_xaxes(tickformat=".0%")
    return fig


def signed_bars(values: pd.Series, title: str, unit: str = "pp") -> go.Figure:
    """Horizontal bars of signed contributions (index = label), blue positive, gold negative."""
    v = values.sort_values()
    fig = go.Figure(go.Bar(y=v.index, x=v.to_numpy() * (100 if unit == "pp" else 1), orientation="h",
                           marker_color=[BLUE if x > 0 else GOLD for x in v],
                           hovertemplate="%{y}: %{x:+.2f} " + unit + "<extra></extra>"))
    fig.update_layout(title=title, showlegend=False, **{**_LAYOUT, "hovermode": "closest"})
    fig.update_xaxes(ticksuffix=f" {unit}", zeroline=True, zerolinecolor=GREY)
    return fig


def importance(rows: pd.DataFrame, title: str, top: int = 5) -> go.Figure:
    """rows: month, feature, shap (mean |SHAP|). 12-month average of the `top` features over time."""
    wide = rows.pivot_table(index="month", columns="feature", values="shap").sort_index()
    keep = wide.mean().sort_values(ascending=False).head(top).index
    smooth = wide[keep].rolling(12, min_periods=1).mean() * 100
    fig = go.Figure()
    for f in keep:
        fig.add_trace(go.Scatter(x=_x(smooth.index), y=smooth[f], name=LABELS.get(f, f), mode="lines",
                                 line={"width": 2}, hovertemplate="%{y:.2f} pp"))
    fig.update_layout(title=title, **_LAYOUT)
    fig.update_yaxes(ticksuffix=" pp", rangemode="tozero")
    return fig


def loadings(result: dict, title: str) -> go.Figure:
    """Factor loadings with 95% intervals (standard error = beta / t)."""
    betas, t = result["betas"], result["t_values"]
    names = list(betas)[::-1]
    b = np.array([betas[k] for k in names])
    se = np.array([abs(betas[k] / t[k]) if t[k] else 0.0 for k in names])
    fig = go.Figure(go.Scatter(
        x=b, y=[FACTOR_NAMES.get(k, k) for k in names], mode="markers", marker={"size": 11, "color": BLUE},
        error_x={"type": "data", "array": 1.96 * se, "color": GREY, "thickness": 2, "width": 6},
        hovertemplate="%{y}: %{x:.2f}<extra></extra>"))
    fig.add_vline(x=0, line={"color": GREY, "width": 1})
    fig.update_layout(title=title, showlegend=False, **{**_LAYOUT, "hovermode": "closest"})
    return fig


def ic_bars(ic: pd.Series, title: str) -> go.Figure:
    """Monthly information coefficient (bars) and its 12-month average (line)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=_x(ic.index), y=ic, name="Monthly IC", marker_color=[BLUE if v > 0 else GOLD for v in ic],
                         hovertemplate="%{y:.3f}"))
    fig.add_trace(go.Scatter(x=_x(ic.index), y=ic.rolling(12, min_periods=6).mean(), name="12-month average",
                             mode="lines", line={"color": INK, "width": 2}, hovertemplate="%{y:.3f}"))
    fig.update_layout(title=title, bargap=0.1, **_LAYOUT)
    return fig
