# Data quality report

## Gates (latest month)

| Gate | Result | Detail |
|---|---|---|
| month_closed | pass | 2026-10 ends 2026-10-31, today is 2026-11-20 |
| member_count | pass | 503 members (allowed 495-510) |
| price_coverage | pass | 99.6% of members priced (min 95%) |
| max_abs_return | pass | 0 members beyond 80% (max 3), largest 45% (max 300%) |
| features_built | pass | 503 feature rows for 503 members |

## Tables

| Table | Rows |
|---|---:|
| dim_month | 197 |
| dim_security | 835 |
| dim_sector | 12 |
| fact_membership | 98,925 |
| fact_prices | 145,827 |
| fact_fundamentals | 298,874 |
| fact_features | 98,925 |
| fact_predictions | 71,553 |
| fact_holdings | 8,300 |
| fact_performance | 660 |
| fact_factors | 208 |
| fact_shap | 10,005 |
| fact_live | 0 |

## Survivorship

190 of the tickers that were ever index members since the start have no price on Yahoo (22.8%); they are mostly companies acquired or delisted years ago. Months where a held stock has no return are counted, not filled.

## Excluded price series

| Ticker | Reason |
|---|---|
| CPWR | Compuware (acquired 2014); Yahoo's CPWR is an illiquid security with stale prices and +300% jumps |
| PARA | Paramount Global (merged into Paramount Skydance, 2025); Yahoo's PARA history is another instrument (level ~3,400, ~0.3% monthly moves) |
