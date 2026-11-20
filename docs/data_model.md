# Data model

Star schema stored as parquet in `data/snapshot/` and read through DuckDB (`factorml.warehouse.connect()`
creates one view per table). Months are stored as the first day of the month.

```
                     dim_month (month, year, quarter)
                          | 1:*  month
     +--------------------+---------------------+---------------------+
     v                    v                     v                     v
fact_membership     fact_prices           fact_features         fact_predictions
(month, ticker)     (month, ticker:       (month, ticker:       (month, ticker: score,
     |               ret, close, mcap)     14 ranks, sector,      rank, model_version)
     |                    |                target)                    |
     +---------*:1--------+------*:1-------+-------------------*:1----+
                          v
                    dim_security (ticker, cik, name, sector) --*:1-- dim_sector (sector)
                          | 1:* cik
                          v
                  fact_fundamentals (cik, item, period_end, value, filed)

fact_holdings (month, ticker, weight, source = backtest | live)       --> dim_month, dim_security
fact_performance (month, strategy, gross, cost, net, turnover, n_missing)  --> dim_month
fact_factors (month, mkt_rf, smb, hml, rmw, cma, mom, rf)              --> dim_month
fact_shap (month, ticker | "ALL", feature, shap, expected_value)       --> dim_month, dim_security
fact_live (month, model_version, ..., prev_portfolio_return, benchmark returns)  --> dim_month
```

- `ticker` is the security id: renamed tickers map to the current one (FB -> META), so a company keeps one id.
- `fact_fundamentals` is keyed by CIK, not ticker: share classes of one company (GOOG, GOOGL) share its filings.
- `fact_shap` keeps per-stock values for the latest backtest month and every live month, and a global
  mean |SHAP| per feature for every month (`ticker = "ALL"`).
- `fact_live` is append-only; `summary.json` holds the derived statistics (metrics, IC, attribution, gates).
