"""Shared helpers for the Streamlit pages. Reads only the committed snapshot: no network, no keys."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from factorml import model as md
from factorml import warehouse as wh
from factorml.config import SNAPSHOT, settings


def setup(title: str) -> None:
    st.set_page_config(page_title=f"S&P 500 factor ML - {title}", page_icon=":material/insights:", layout="wide")


@st.cache_data
def table(name: str) -> pd.DataFrame:
    return wh.load(name)


@st.cache_data
def summary() -> dict:
    return json.loads((SNAPSHOT / "summary.json").read_text())


@st.cache_data
def net_wide() -> pd.DataFrame:
    """Backtest monthly net returns, one column per strategy."""
    p = table("fact_performance")
    return p.pivot(index="month", columns="strategy", values="net")[["model", "sp500tr", "factor_rule", "equal_weight"]]


@st.cache_data
def ic_series() -> pd.Series:
    return md.information_coefficient(table("fact_predictions"), table("fact_features")).dropna()


def latest_holdings() -> tuple[pd.Period, pd.DataFrame]:
    h = table("fact_holdings")
    m = h["month"].max()
    pred = table("fact_predictions")
    dim = table("dim_security")
    out = (h[h["month"] == m].merge(pred[pred["month"] == m][["ticker", "score", "rank"]], on="ticker")
           .merge(dim, on="ticker", how="left").sort_values("rank"))
    return m, out


def pct(x: float, signed: bool = False) -> str:
    return "n/a" if x is None or pd.isna(x) else (f"{x:+.1%}" if signed else f"{x:.1%}")


def footer() -> None:
    st.space("medium")
    st.caption(settings()["disclaimer"])
    st.caption("Data: S&P 500 membership (fja05680/sp500, Wikipedia), prices (Yahoo Finance), fundamentals "
               "(SEC EDGAR XBRL), factors (Kenneth R. French data library).")
