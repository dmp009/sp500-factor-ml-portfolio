# Data dictionary

## Sources and lineage

| Source | What | Used in | Refresh |
|---|---|---|---|
| fja05680/sp500 (GitHub, MIT) | S&P 500 member list at each change date since 1996 | fact_membership (history) | backfill only |
| Wikipedia, "List of S&P 500 companies" | current members, CIK, GICS sector | fact_membership (live months), dim_security | monthly |
| Yahoo Finance (yfinance) | daily adjusted close, split-adjusted close, split events | fact_prices | monthly (last 14 months) |
| SEC EDGAR XBRL company facts | annual accounting values and share counts, with filing dates | fact_fundamentals | monthly (current members) |
| SEC EDGAR submissions | company name and SIC code of former members | dim_security | backfill only |
| Kenneth R. French data library | Fama-French 5 factors, momentum, risk-free rate | fact_factors | monthly |

```
sources -> universe.py -> prices.py / fundamentals.py / famafrench.py -> features.py -> model.py
        -> portfolio.py -> performance.py / attribution.py / explain.py -> warehouse (parquet) -> app, reports
```

## Fields

| Table | Field | Meaning |
|---|---|---|
| fact_prices | ret | month-end to month-end total return from the adjusted close (NaN in a security's first month) |
| fact_prices | close | month-end adjusted close |
| fact_prices | mcap | market value in USD at month end (split-consistent; NaN without SEC share count) |
| fact_fundamentals | item | revenue, cost_of_revenue, gross_profit, net_income, operating_cash_flow, total_assets, total_liabilities, equity, shares_outstanding |
| fact_fundamentals | period_end / filed | end of the fiscal period / date the filing reached EDGAR (the value is usable from this date) |
| fact_features | mom_12_1, mom_6_1 | compounded return over months M-11..M-1 and M-5..M-1 |
| fact_features | rev_1 | return of month M |
| fact_features | vol_12, beta_12 | standard deviation of monthly returns and beta to the S&P 500 TR over M-11..M |
| fact_features | size | log market value |
| fact_features | bm, ey, sp | equity, net income and revenue divided by market value |
| fact_features | roe | net income / equity (positive equity only) |
| fact_features | gp | gross profit (or revenue minus cost of revenue) / total assets |
| fact_features | accruals | (net income - operating cash flow) / total assets |
| fact_features | leverage | 1 - equity / total assets |
| fact_features | asset_growth | total assets / total assets known 12 months earlier - 1 |
| fact_features | target | return of M+1 minus the median member's return of M+1 |
| fact_predictions | score, rank | predicted target and its rank within the month (1 = best) |
| fact_performance | gross, cost, net | portfolio return in the month earned, trading cost, gross minus cost |
| fact_performance | n_missing | holdings without a return that month (counted as 0) |
| fact_live | prev_portfolio_return | net return during the month of the live portfolio formed the month before |

All characteristics in fact_features are ranked from 0 to 1 within the month; missing values stay missing.
