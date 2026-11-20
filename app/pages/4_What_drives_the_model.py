"""Global SHAP importance over time."""
import pandas as pd
import streamlit as st

from app import charts as ch
from app.common import footer, setup, table
from factorml import explain

setup("What drives the model")
st.title("What drives the model", icon=":material/psychology:")
st.markdown("For every monthly model, the mean absolute SHAP value of each characteristic: how much, on average, it "
            "moves a stock's predicted return. Larger means the model leans on it more.")
g = table("fact_shap").query("ticker == 'ALL'")
st.plotly_chart(ch.importance(g, "Five most used characteristics, 12-month average", top=5), width="stretch")
avg = g.groupby("feature")["shap"].mean().sort_values()
avg.index = [explain.LABELS.get(f, f) for f in avg.index]
st.plotly_chart(ch.signed_bars(avg, "Average importance over the whole backtest"), width="stretch")
recent = g[g["month"] >= g["month"].max() - 11].groupby("feature")["shap"].mean()
older = g[g["month"] < g["month"].max() - 11].groupby("feature")["shap"].mean()
chg = (recent / older - 1).sort_values()
st.caption("Change in the last 12 months vs before: " + ", ".join(
    f"{explain.LABELS.get(f, f)} {v:+.0%}" for f, v in pd.concat([chg.head(2), chg.tail(2)]).items()) + ".")
footer()
