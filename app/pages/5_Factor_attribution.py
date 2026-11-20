"""Fama-French 5 + momentum attribution."""
import streamlit as st

from app import charts as ch
from app.common import footer, pct, setup, summary

setup("Factor attribution")
s = summary()
st.title("Factor attribution", icon=":material/functions:")
st.markdown("Is the return skill or known risk? Monthly excess returns are regressed on the five Fama-French factors "
            "and momentum, with Newey-West standard errors. **Alpha** is what the factors do not explain; the "
            "**loadings** show the tilts.")
choice = st.segmented_control("Strategy", ["model", "factor_rule", "sp500tr"], default="model",
                              format_func=lambda k: ch.NAMES[k])
a = s["attribution"][choice or "model"]
c1, c2, c3 = st.columns(3, border=True)
c1.metric("Annual alpha", pct(a["alpha_annual"], True), f"t = {a['alpha_t']:.1f}", delta_color="off")
c2.metric("R squared", f"{a['r2']:.2f}")
c3.metric("Months", a["n"])
st.info(a["reading"], icon=":material/lightbulb:")
st.plotly_chart(ch.loadings(a, "Factor loadings with 95% intervals"), width="stretch")
st.caption("A loading of 1.2 on the market means the portfolio moves about 1.2% when the market moves 1%. "
           "Intervals that cross zero are not significant.")
footer()
