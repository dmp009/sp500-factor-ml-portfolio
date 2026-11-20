"""The live record: one row per automated monthly run, append-only."""
import streamlit as st

from app.common import footer, pct, setup, summary, table

setup("Live track record")
st.title("Live track record", icon=":material/schedule:")
st.markdown("Every month a GitHub Actions job rebuilds the portfolio from fresh data and appends one row here. "
            "Rows are never changed afterwards (a test checks it), and the live record is kept apart from the "
            "backtest.")
lv = table("fact_live")
if lv.empty:
    st.info(f"The live record starts with the first scheduled run after the backtest, which ends in "
            f"{summary()['backtest']['last_month']}. Until then the Current portfolio page shows the last backtest "
            "portfolio.", icon=":material/hourglass_top:")
else:
    live = summary()["live"]
    if live.get("months_with_returns"):
        c = live["cumulative"]
        k1, k2, k3, k4 = st.columns(4, border=True)
        k1.metric("Model since live start", pct(c["model"], True))
        k2.metric("S&P 500 TR", pct(c["sp500tr"], True))
        k3.metric("Factor rule", pct(c["factor_rule"], True))
        k4.metric("Equal weight", pct(c["equal_weight"], True))
    st.dataframe(lv, hide_index=True, column_config={
        "month": "Formed", "model_version": "Model", "n_holdings": "Stocks",
        "turnover": st.column_config.NumberColumn("Turnover", format="percent"),
        "cost": st.column_config.NumberColumn("Cost", format="percent"),
        "prev_portfolio_return": st.column_config.NumberColumn("Previous portfolio, net", format="percent"),
        "sp500tr_return": st.column_config.NumberColumn("S&P 500 TR", format="percent"),
        "equal_weight_return": st.column_config.NumberColumn("Equal weight", format="percent"),
        "factor_rule_return": st.column_config.NumberColumn("Factor rule", format="percent")})
    st.caption("Each row shows the return, during that month, of the portfolio formed the month before.")
footer()
