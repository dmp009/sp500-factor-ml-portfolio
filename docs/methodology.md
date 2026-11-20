# Methodology

This note explains what the model does, how it is tested and what the results mean, for a reader who knows
finance but not necessarily machine learning. Numbers refer to the committed snapshot (backtest February 2013
to October 2026, 165 months).

## 1. The question

Can a model that only sees information public at the time pick S&P 500 stocks that beat the index after
trading costs? The test has to be fair: no knowledge of future index changes, no accounting figures before
they were filed, no parameters tuned on the period being judged.

## 2. Universe

Each month the universe is the set of S&P 500 members at that month's end, rebuilt from the
fja05680/sp500 history of index changes (MIT licence) and, after its last date, from the current Wikipedia
list. Companies that later left the index stay in the months when they were members. A stock is investable in
a month only if it has a price that month: 190 of the 835 securities that were members since June 2010 have no
price on Yahoo Finance, so early years cover fewer stocks (66% of members in June 2010, 100% in October 2026).

## 3. Characteristics

Fourteen characteristics from the asset-pricing literature, each ranked from 0 to 1 across stocks within the
month so the model compares stocks with each other, not with history:

| Group | Characteristics | Literature |
|---|---|---|
| Price | 12-1 and 6-1 month momentum, last-month return, 12-month volatility, 12-month beta | Jegadeesh and Titman (1993); Carhart (1997) |
| Size and value | market value, book-to-market, earnings yield, sales-to-price | Fama and French (2015) |
| Quality | return on equity, gross profitability, accruals, leverage | Novy-Marx (2013); Sloan (1996) |
| Investment | asset growth | Cooper, Gulen and Schill (2008); Fama and French (2015) |

Plus the sector (GICS from Wikipedia, or SEC SIC codes mapped to eleven sectors for former members).

**No look-ahead.** Accounting values come from SEC XBRL company facts. Each value carries the date its filing
reached EDGAR and is used only from that date; if a figure is restated later, the restated value appears only
from the restatement's filing date. A test perturbs every return after month M and every filing after M and
checks that the features at M do not change.

**Market value.** SEC share counts are as reported, while Yahoo prices are restated for all later splits.
Market value multiplies the split-adjusted price by the reported shares and by every split after the share-count
date; without this, Apple before its 2020 four-for-one split would look four times smaller.

## 4. Model

- **Target:** next month's return minus the median stock's return that month. The model learns to rank stocks,
  not to forecast the market.
- **Algorithm:** LightGBM gradient-boosted trees, the family that performed best among simple learners in
  Gu, Kelly and Xiu (2020).
- **Walk-forward:** the model for month M is trained on all months up to M-2 (the target of M-1 needs the
  return of M, so one month is left out as a buffer), and retrained every month.
- **Training target clipped** at the 1st and 99th percentile within each month, so one extreme move cannot
  dominate a squared-error loss. Evaluation always uses raw returns.
- **Hyper-parameters** chosen once on 2010-2012 by mean information coefficient over a nine-point grid, then
  frozen (31 leaves, at least 100 stocks per leaf, 300 trees, learning rate 0.03). The validation IC was
  already negative (-0.03), a warning that turned out to hold out of sample.

## 5. Portfolio and baselines

Top 50 stocks by predicted return, equal weight, rebalanced at each month's close, held through the next month.
Costs: 10 bps per side on traded value. Three baselines, judged on the same months:

1. S&P 500 total return index (`^SP500TR`);
2. equal-weight universe: every investable member;
3. a factor rule: average rank of momentum, gross profitability and book-to-market, top 50.

## 6. Evaluation

- **Information coefficient (IC):** the Spearman rank correlation between scores and next-month returns,
  per month; its mean and t-statistic.
- **Top-minus-bottom decile spread** of next-month returns.
- **Performance:** CAGR, volatility, Sharpe (with the Fama-French risk-free rate), maximum drawdown, tracking
  error and information ratio against the S&P 500, share of months beating it, turnover.
- **Attribution:** monthly excess returns regressed on the five Fama-French factors and momentum (Fama and
  French, 2015; Carhart, 1997), with Newey and West (1987) standard errors (6 lags). |t| >= 2 counts as
  significant.
- **Explanation:** SHAP values (Lundberg and Lee, 2017), computed with LightGBM's own TreeSHAP for every
  monthly model.

## 7. Results

| Strategy, net of costs | CAGR | Volatility | Sharpe | Max drawdown | Info ratio |
|---|---:|---:|---:|---:|---:|
| LightGBM model | 12.4% | 19.6% | 0.61 | 31.2% | -0.11 |
| Factor rule | 11.4% | 15.8% | 0.66 | 28.7% | -0.27 |
| Equal-weight universe | 13.1% | 15.3% | 0.77 | 26.9% | -0.19 |
| S&P 500 total return | 14.5% | 14.2% | 0.91 | 23.9% | |

- Mean IC 0.001 (t = 0.1), positive in 51% of months; top decile beats bottom decile by 0.14 pp a month.
- Attribution of the model: annual alpha -2.5% (t = -1.6), not significant; market beta 1.2 and a significant
  value tilt; R squared 0.88.
- Monthly turnover around 61%, so costs take about 1.5% a year.

**Reading.** The model has no measurable skill at ranking S&P 500 stocks in this period. Its returns are a
leveraged-beta, value-tilted version of the market, which lagged a cap-weighted index led by a few very large
growth companies. This is consistent with McLean and Pontiff (2016), who find that anomaly returns shrink after
publication, and with the gains in Gu, Kelly and Xiu (2020) coming mostly from smaller stocks rather than the
largest ones. The results were not re-tuned after the backtest was seen: doing so would fit the test period.

## 8. Limits

- Survivorship: stocks without prices cannot be held, and delisting returns are missing.
- Free sources without the corrections of a commercial database; two Yahoo series that belong to other
  instruments were excluded after review (see the data-quality report).
- One market and one period; a single model family; no transaction-cost model beyond a flat rate.

## References

- Carhart, M. M. (1997). On persistence in mutual fund performance. *Journal of Finance*, 52(1), 57-82. https://doi.org/10.1111/j.1540-6261.1997.tb03808.x
- Cooper, M. J., Gulen, H., & Schill, M. J. (2008). Asset growth and the cross-section of stock returns. *Journal of Finance*, 63(4), 1609-1651. https://doi.org/10.1111/j.1540-6261.2008.01370.x
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics*, 116(1), 1-22. https://doi.org/10.1016/j.jfineco.2014.10.010
- Gu, S., Kelly, B., & Xiu, D. (2020). Empirical asset pricing via machine learning. *Review of Financial Studies*, 33(5), 2223-2273. https://doi.org/10.1093/rfs/hhaa009
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers: Implications for stock market efficiency. *Journal of Finance*, 48(1), 65-91. https://doi.org/10.1111/j.1540-6261.1993.tb04702.x
- Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems 30*. https://arxiv.org/abs/1705.07874
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance*, 71(1), 5-32. https://doi.org/10.1111/jofi.12365
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708. https://doi.org/10.2307/1913610
- Novy-Marx, R. (2013). The other side of value: The gross profitability premium. *Journal of Financial Economics*, 108(1), 1-28. https://doi.org/10.1016/j.jfineco.2013.01.003
- Sloan, R. G. (1996). Do stock prices fully reflect information in accruals and cash flows about future earnings? *The Accounting Review*, 71(3), 289-315.
