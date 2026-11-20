"""Method, limits and automation."""
import streamlit as st

from app.common import footer, setup, summary

setup("About")
s = summary()
p = s["params"]
st.title("About", icon=":material/info:")
st.markdown(f"""
**Question.** Can a machine-learning model, using only information public at the time, pick S&P 500 stocks that
beat the index after costs? And can that be run as a live, self-updating process?

**Universe.** S&P 500 members month by month since June 2010, including companies that later left the index
(history from the fja05680/sp500 dataset, current list from Wikipedia).

**Characteristics (14, ranked within each month).** Momentum (12-1 and 6-1 months), last-month reversal,
12-month volatility and beta, size, book-to-market, earnings yield, sales-to-price, return on equity, gross
profitability, accruals, leverage, asset growth, plus the sector. Accounting values come from SEC XBRL filings and
are used only from the date they were filed, so a restatement never leaks into the past. Market value restates
reported share counts for later stock splits.

**Model.** LightGBM regression on next month's return minus the median stock. Retrained every month on all earlier
months (one month left out as a buffer); the training target is clipped at the 1st and 99th percentiles of each
month. Hyper-parameters were chosen once on 2010-2012 and frozen: {p['num_leaves']} leaves, at least
{p['min_child_samples']} stocks per leaf, {p['n_estimators']} trees, learning rate {p['learning_rate']}.

**Portfolio.** Top 50 by predicted return, equal weight, rebalanced monthly, 10 bps cost per side on turnover.
Baselines: S&P 500 total return, the equal-weight universe, and a factor rule (average rank of momentum, gross
profitability and book-to-market).

**Automation.** A GitHub Actions job runs on the first days of each month. It refreshes membership, prices,
filings and factors, checks five quality gates, retrains, picks the portfolio, appends the live record, writes a
report and commits the new snapshot; Streamlit redeploys from that commit. If anything fails, nothing is written
and a GitHub issue is opened, which reaches the owner by e-mail.

**Limits.**
- *Survivorship.* {s['survivorship']['n_missing']} of {s['universe']['securities']} securities have no price on
  Yahoo (mostly old delistings). They cannot be held, so early backtest years cover fewer stocks, and delisting
  losses are missing.
- *Data sources.* Free sources (Yahoo, SEC, Wikipedia) without the corrections of a commercial database; two
  Yahoo series that belong to other instruments were excluded after review.
- *One market, one period.* US large caps, 2013-2026, a period in which the index was hard to beat.
- The live record is short at first and says little until it has years of months.
""")
footer()
