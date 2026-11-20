"""Current holdings, sector mix and the reasons behind each pick."""
import pandas as pd
import streamlit as st

from app import charts as ch
from app.common import footer, latest_holdings, setup, table
from factorml import explain

setup("Current portfolio")
m, h = latest_holdings()
st.title("Current portfolio", icon=":material/list_alt:")
src = "live run" if (h["source"] == "live").any() else "backtest (the live record starts with the next scheduled run)"
st.caption(f"Formed at the close of {m}, held through {m + 1}. 50 stocks, 2% each. Source: {src}.")

mem = table("fact_membership")
dim = table("dim_security").set_index("ticker")
idx = mem[mem["month"] == m]["ticker"].map(dim["sector"]).value_counts(normalize=True)
port = h["sector"].value_counts(normalize=True)
mix = pd.DataFrame({"portfolio": port, "index": idx}).fillna(0).rename_axis("sector").reset_index()
left, right = st.columns([3, 2])
with right:
    st.plotly_chart(ch.sector_mix(mix, "Sector weights"), width="stretch")
shap = table("fact_shap")
shap_m = shap[(shap["month"] == m) & (shap["ticker"] != "ALL")]
with left:
    rows = h.assign(reasons=[" · ".join(explain.top_reasons(shap_m, t, 2)) for t in h["ticker"]])
    st.dataframe(rows[["rank", "ticker", "name", "sector", "score", "reasons"]], hide_index=True, height=520,
                 column_config={"rank": "Rank", "ticker": "Ticker", "name": "Company", "sector": "Sector",
                                "score": st.column_config.NumberColumn("Score", help="Predicted return vs the median "
                                                                       "stock next month", format="%.4f"),
                                "reasons": st.column_config.TextColumn("Main reasons (SHAP)", width="large")})

st.subheader("Why one stock was picked")
pick = st.selectbox("Stock", h["ticker"], format_func=lambda t: f"{t} - {dim.at[t, 'name'] if t in dim.index else t}")
one = shap_m[shap_m["ticker"] == pick].set_index("feature")["shap"]
one.index = [explain.LABELS.get(f, f) for f in one.index]
st.plotly_chart(ch.signed_bars(one, f"{pick}: contribution of each characteristic to the score"), width="stretch")
st.caption("SHAP values from the model of this month: how much each characteristic moves the predicted return "
           "relative to the median stock, in percentage points. They add up to the score.")
footer()
