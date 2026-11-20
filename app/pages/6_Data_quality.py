"""Gates of the last refresh, survivorship and the full data-quality report."""
import streamlit as st

from app.common import footer, setup, summary
from factorml.config import SNAPSHOT

setup("Data quality")
s = summary()
st.title("Data quality", icon=":material/fact_check:")
st.markdown("The monthly job stops before writing anything if one of these gates fails, and opens a GitHub issue "
            "(the alert). The table shows the gates of the latest month in the snapshot.")
st.dataframe([{"Gate": g, "Result": "pass" if ok else "FAIL", "Detail": d} for g, ok, d in s["gates"]],
             hide_index=True)
sv = s["survivorship"]
c1, c2, c3 = st.columns(3, border=True)
c1.metric("Securities in the index since 2010-06", s["universe"]["securities"])
c2.metric("Without Yahoo prices", sv["n_missing"], f"{sv['share_missing']:.0%}", delta_color="off")
cov = list(s["coverage"].values())
c3.metric("Members priced, first vs last month", f"{cov[0]:.0%} → {cov[-1]:.0%}")
st.caption("Yahoo has no prices for many companies that left the index long ago, so early months cover fewer "
           "members. Stocks without a price at formation are not investable; the bias this leaves is discussed "
           "on the About page.")
with st.expander("Full data-quality report"):
    st.markdown((SNAPSHOT / "data_quality_report.md").read_text())
footer()
