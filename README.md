# S&P 500 Factor ML Portfolio

[![CI](https://github.com/dmp009/sp500-factor-ml-portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/dmp009/sp500-factor-ml-portfolio/actions/workflows/ci.yml)
[![Monthly refresh](https://github.com/dmp009/sp500-factor-ml-portfolio/actions/workflows/monthly.yml/badge.svg)](https://github.com/dmp009/sp500-factor-ml-portfolio/actions/workflows/monthly.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

**Live demo:** coming soon (Streamlit Community Cloud)

A machine-learning stock ranker for the S&P 500, tested the way a quant team would test it: point-in-time
index membership, accounting data used only from its SEC filing date, a model retrained every month on the
past only, trading costs, three simple baselines, factor attribution and SHAP explanations. A GitHub Actions
job rebuilds the portfolio every month, checks the data before it writes anything, appends to a live record
that cannot be rewritten, and opens an issue when a refresh fails.

## The business problem

Asset managers keep being asked whether machine learning can improve stock selection. A convincing answer
needs three things: a fair test with no information from the future, an explanation of what the model is
really betting on, and a process that keeps running every month without anyone rebuilding it by hand.

## What the backtest says

February 2013 to October 2026, 165 months, top 50 stocks in equal weight, net of 10 bps per side:

| Strategy | CAGR | Volatility | Sharpe | Max drawdown |
|---|---:|---:|---:|---:|
| LightGBM model | 12.4% | 19.6% | 0.61 | 31.2% |
| Factor rule (momentum, profitability, value) | 11.4% | 15.8% | 0.66 | 28.7% |
| Equal-weight universe | 13.1% | 15.3% | 0.77 | 26.9% |
| **S&P 500 total return** | **14.5%** | **14.2%** | **0.91** | **23.9%** |

**The model does not beat the index.** Its ranking skill is indistinguishable from zero (mean information
coefficient 0.001, t = 0.1). After the five Fama-French factors and momentum, its annual alpha is -2.5%
(t = -1.6, not significant); what it earns comes from a market beta of 1.2 and a value tilt. Published
characteristics tend to lose much of their return after publication (McLean and Pontiff, 2016), and over
these years a cap-weighted index led by a few very large growth companies was hard to beat. The parameters were frozen on 2010-2012 and not re-tuned after the backtest was
seen, because re-tuning would only fit the test period. The live record, which starts with the first
scheduled run, will show whether this holds.

## The solution

```
S&P 500 history + Wikipedia ─┐
Yahoo Finance prices ────────┤                      quality gates ──fail──> GitHub issue (alert)
SEC XBRL filings ────────────┼─> point-in-time ─> 14 ranked ─> LightGBM ─> top 50 ─> live record
Fama-French factors ─────────┘    panel           features     walk-forward  portfolio  + report
                                                                    │
                                            SHAP, attribution, IC ──┴──> DuckDB star schema ─> Streamlit
```

- **Universe:** members at each month end, including companies that later left the index
  (`factorml/universe.py`).
- **Features:** momentum, reversal, volatility, beta, size, value, earnings and sales yield, ROE, gross
  profitability, accruals, leverage, asset growth, sector; ranked within each month (`features.py`).
  Filings are used only from the date they reached EDGAR; share counts are restated for later splits.
- **Model:** LightGBM on next-month return relative to the median stock; the model for month M is trained on
  months up to M-2 (`model.py`).
- **Portfolio and tests:** costs, three baselines, information coefficient, Newey-West factor regression, SHAP
  (`portfolio.py`, `performance.py`, `attribution.py`, `explain.py`).
- **Automation:** `pipeline.py monthly` refreshes the sources, runs five quality gates (closed month, member
  count, price coverage, abnormal moves, feature rows), retrains, and saves only if every step passed. The
  workflow commits the new snapshot, and Streamlit redeploys. On failure it opens or updates an issue labelled
  `refresh-failed`, and the next success closes it.
- **App:** current portfolio with the reasons for each pick, live record, backtest, SHAP over time, factor
  attribution, data quality.

Documentation: [methodology](docs/methodology.md) (with references), [business requirements](docs/business_requirements.md),
[data dictionary](docs/data_dictionary.md), [data model](docs/data_model.md),
[latest monthly report](reports/), [data-quality report](data/snapshot/data_quality_report.md).

## Run it

```bash
make install        # Python 3.11+; on macOS LightGBM needs libomp (the Makefile reuses scikit-learn's copy)
make test           # 65 tests, no network
make app            # Streamlit on the committed snapshot
```

The full history is rebuilt with `make backfill` (network, about 10 minutes; set `SEC_CONTACT` in `.env`, the
SEC asks for a contact in the User-Agent). The scheduled job runs `python -m factorml.pipeline monthly`.

## Tech

Python, pandas, LightGBM, statsmodels, DuckDB, Streamlit, Plotly, GitHub Actions; yfinance, SEC EDGAR APIs.

## Limits

- **Survivorship.** 190 of the 835 securities that were members since June 2010 (23%) have no price on Yahoo,
  mostly companies delisted long ago. They cannot be held, so the early years cover fewer stocks (66% of members
  in June 2010, 100% today) and delisting losses are missing.
- **Free data.** Yahoo, SEC and Wikipedia do not carry the corrections of a commercial database. Two Yahoo
  series that belong to other instruments were excluded after review, and others are flagged automatically.
- **Scope.** One market, one period, one model family, a flat trading cost.
- Educational project, not investment advice.

## Résumé en français

Un modèle de machine learning (LightGBM) classe chaque mois les actions du S&P 500 à partir de 14
caractéristiques classiques (momentum, valeur, rentabilité, investissement, risque), en n'utilisant que
l'information publique à la date : composition historique de l'indice, comptes SEC pris à leur date de dépôt,
modèle réentraîné chaque mois sur le passé seulement. Le portefeuille des 50 meilleures actions est comparé,
frais inclus, au S&P 500, à un univers équipondéré et à une règle factorielle simple, puis expliqué par SHAP et
par une régression Fama-French à cinq facteurs plus momentum.

Résultat, présenté sans retouche : de 2013 à 2026, le modèle ne bat pas l'indice (12,4 % par an contre 14,5 %),
son pouvoir de classement est nul (IC moyen 0,001) et son rendement s'explique par un bêta de 1,2 et un biais
value. Le projet montre surtout la méthode : un test sans biais d'anticipation et une chaîne automatisée.
Chaque mois, GitHub Actions met à jour les données, vérifie leur qualité, reconstruit le portefeuille, ajoute
une ligne à un historique en direct non modifiable et ouvre une alerte si la mise à jour échoue.
