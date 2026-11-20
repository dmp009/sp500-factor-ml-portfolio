"""Walk-forward backtest against three baselines."""
import pandas as pd
import streamlit as st

from app import charts as ch
from app.common import footer, ic_series, net_wide, setup, summary, table

setup("Backtest")
s = summary()
bt = s["backtest"]
st.title("Backtest", icon=":material/show_chart:")
st.caption(f"{bt['first_month']} to {bt['last_month']}, monthly. Each month the model is retrained on earlier "
           "months only, the top 50 stocks are bought in equal weight, and trading costs of 10 bps per side are paid.")
wide = net_wide()
st.plotly_chart(ch.cumulative(wide, "Growth of $1, net of costs"), width="stretch")
st.plotly_chart(ch.drawdown(wide, "Drawdown from the previous peak"), width="stretch")

rows = []
for k, v in s["metrics"].items():
    rows.append({"Strategy": ch.NAMES[k], "CAGR": v["cagr"], "Volatility": v["vol"], "Sharpe": v["sharpe"],
                 "Max drawdown": v["max_dd"], "Tracking error": None if k == "sp500tr" else v["tracking_error"],
                 "Info ratio": None if k == "sp500tr" else v["info_ratio"],
                 "Months beating S&P 500": None if k == "sp500tr" else v["hit_rate"],
                 "Monthly turnover": v["avg_turnover"]})
pc = {"format": "percent"}
st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
    c: st.column_config.NumberColumn(c, **pc) for c in ("CAGR", "Volatility", "Max drawdown", "Tracking error",
                                                         "Months beating S&P 500", "Monthly turnover")}
    | {c: st.column_config.NumberColumn(c, format="%.2f") for c in ("Sharpe", "Info ratio")})
cost = table("fact_performance").query("strategy == 'model'")["cost"]
st.caption(f"Trading costs took {cost.mean() * 12:.2%} a year from the model (monthly turnover around "
           f"{s['metrics']['model']['avg_turnover']:.0%}). Sharpe uses the Fama-French risk-free rate.")

st.subheader("Ranking skill")
ic = s["ic"]
st.markdown(f"The **information coefficient** is the rank correlation between the model's score and the next "
            f"month's return. Its mean is **{ic['mean']:.3f}** (t = {ic['t']:.1f}); it was positive in "
            f"{ic['share_positive']:.0%} of {ic['months']} months. The top decile of scores beat the bottom decile by "
            f"{ic['top_minus_bottom_decile_monthly'] * 100:.2f} pp a month on average. In plain words: no reliable skill.")
st.plotly_chart(ch.ic_bars(ic_series(), "Information coefficient by month"), width="stretch")
footer()
