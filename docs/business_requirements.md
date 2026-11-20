# Business requirements

## Problem

Quantitative equity teams are asked whether machine learning can improve stock selection. Answering that
needs a fair test (no look-ahead, realistic costs, simple baselines), an explanation of what the model does,
and a process that keeps running every month without manual work.

## Personas

| Persona | Needs | Where in the app |
|---|---|---|
| Portfolio manager | The current 50 holdings, why each was picked, and whether the model adds value over the index and a simple rule | Current portfolio, Backtest |
| Private banker | A short, honest story for clients: what the strategy holds, how it has done live, how it differs from the index | Home, Live track record |
| Risk and compliance | Proof that results are not built on future data, factor exposures, a record that cannot be rewritten, and an alert when data is wrong | Factor attribution, Data quality, Live track record |

## User stories and acceptance criteria

1. **As a portfolio manager, I want this month's top 50 with the reasons for each pick.**
   Holdings, sector weights against the index, and the two largest SHAP contributions per stock are shown;
   the SHAP values of a stock add up to its score (tested).
2. **As a portfolio manager, I want to know whether the model beats simple alternatives after costs.**
   The backtest compares the model with the S&P 500 total return, the equal-weight universe and a factor rule
   on the same months, net of 10 bps per side.
3. **As a risk officer, I want no look-ahead.** A feature at month M never changes when returns after M or
   filings after M are changed (tested); the model for M is trained only on months up to M-2 (tested).
4. **As a risk officer, I want to know which risks drive returns.** A Fama-French 5 + momentum regression with
   Newey-West errors reports alpha, loadings and a plain-English reading.
5. **As a private banker, I want a live record I can trust.** One row per automated month; changing an existing
   row raises an error (tested).
6. **As the owner, I want to be told when a refresh fails.** A failed run writes nothing and opens a GitHub
   issue with the failed step, the error and the run link; the next success closes it.

## KPI definitions

| KPI | Definition |
|---|---|
| CAGR | (product of 1 + monthly net return)^(12 / months) - 1 |
| Sharpe ratio | mean monthly excess return over the risk-free rate / its standard deviation, x sqrt(12) |
| Maximum drawdown | largest fall from a previous peak of cumulative wealth |
| Tracking error | standard deviation of monthly return minus S&P 500 TR, x sqrt(12) |
| Information ratio | annualised mean active return / tracking error |
| Information coefficient | Spearman correlation of score and next-month return, per month |
| Turnover | half the sum of absolute weight changes at a rebalance |
| Price coverage | share of index members with a price in the month |

## Backlog

- Value-weighted and sector-neutral portfolio variants.
- A commercial price source with delisting returns, to remove the survivorship gap.
- More model families (linear with interactions, neural networks) under the same walk-forward test.
- Smaller-cap universe, where the literature finds more predictability.
