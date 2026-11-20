"""S&P 500 factor ML portfolio: landing page."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app import charts as ch
from app.common import footer, net_wide, pct, setup, summary

setup("Home")
s = summary()
st.title("S&P 500 factor ML portfolio", icon=":material/insights:")
st.markdown(
    "A **machine-learning stock ranker** for the S&P 500: 14 classic equity characteristics, a LightGBM model "
    "retrained every month on data that was public at the time, and a **long-only portfolio of the top 50** "
    "stocks. It is tested against the index and two simple rules, explained with SHAP and Fama-French "
    "attribution, and **refreshed automatically each month** by GitHub Actions, with an alert if a refresh fails."
)
m, bt = s["metrics"], s["backtest"]
c1, c2, c3, c4 = st.columns(4, border=True)
c1.metric("Model CAGR, net", pct(m["model"]["cagr"]),
          f"{(m['model']['cagr'] - m['sp500tr']['cagr']) * 100:+.1f} pp vs S&P 500", delta_color="normal")
c2.metric("S&P 500 CAGR", pct(m["sp500tr"]["cagr"]))
c3.metric("Mean IC", f"{s['ic']['mean']:.3f}", f"t = {s['ic']['t']:.1f}", delta_color="off")
c4.metric("Alpha after factors", pct(s["attribution"]["model"]["alpha_annual"], True),
          f"t = {s['attribution']['model']['alpha_t']:.1f}", delta_color="off")
st.caption(f"Backtest {bt['first_month']} to {bt['last_month']} ({bt['months']} months), 10 bps per side. "
           f"Data through {s['data_through']}.")

st.info("Out of sample, the model does not beat the S&P 500. Its ranking skill is indistinguishable from "
        "zero, and its returns are explained by a market beta of 1.2 and a value tilt. Over these years a "
        "cap-weighted index led by a few very large growth companies was hard to beat. The project shows how "
        "to run that test without look-ahead, and how to keep the portfolio running live.",
        icon=":material/balance:")
st.plotly_chart(ch.cumulative(net_wide(), "Growth of $1, net of costs"), width="stretch")

st.subheader("Views")
v1, v2 = st.columns(2, border=True)
with v1:
    st.page_link("pages/1_Current_portfolio.py", label="Current portfolio", icon=":material/list_alt:")
    st.caption("The 50 holdings, their sectors and why the model picked each one.")
    st.page_link("pages/2_Live_track_record.py", label="Live track record", icon=":material/schedule:")
    st.caption("One row per automated month, never rewritten.")
    st.page_link("pages/3_Backtest.py", label="Backtest", icon=":material/show_chart:")
    st.caption("Model against the S&P 500, a factor rule and equal weight; drawdowns, costs, ranking skill.")
    st.page_link("pages/4_What_drives_the_model.py", label="What drives the model", icon=":material/psychology:")
    st.caption("SHAP importance of each characteristic over time.")
with v2:
    st.page_link("pages/5_Factor_attribution.py", label="Factor attribution", icon=":material/functions:")
    st.caption("Alpha and factor loadings (Fama-French 5 + momentum, Newey-West).")
    st.page_link("pages/6_Data_quality.py", label="Data quality", icon=":material/fact_check:")
    st.caption("Quality gates of the last refresh, survivorship, excluded series.")
    st.page_link("pages/7_About.py", label="About", icon=":material/info:")
    st.caption("Method, limits and how the monthly automation works.")
footer()
