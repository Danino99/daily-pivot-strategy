# Analysis

Three small scripts reproduce the clean dataset, the exploratory scan and the
predictive model behind the dashboard. The statistical workflow here (pandas,
inference, hypothesis tests, FDR, logistic regression) is the one I've been
learning in the Tecnicatura en Gestión y Análisis de Datos (FCE, UBA); see the
repository README for the course context.

## What each script does

- `build_dataset.py` — reads the private replay workbooks (`ATR 20xx.xlsx`) and
  writes `data/signals-2023-2024.csv`. It keeps only the "current" sheet layout,
  only indicator-generated signals (`SIGNAL=Sí`), and a minimal, anonymized
  column set: no account values, no position sizes, and no personal execution
  flags.
- `edge_scan.py` — runs on the public CSV and reports win-rate subgroups with
  false-positive control. It writes `public_edge_report.md`.
- `predict_win.py` — fits a logistic regression for P(win), with cross-validation
  and a chronological holdout. It writes `data/model_metrics.json` (used by the
  dashboard) and `model_report.md`.

## Run

```bash
python -m pip install pandas scipy statsmodels scikit-learn

# Point at the folder that holds the private workbooks:
TRADING_SOURCE_DIR=/path/to/workbooks python analysis/build_dataset.py
python analysis/edge_scan.py
python analysis/predict_win.py
```

The workbooks are not distributed with this repository.

## Method

For every subgroup cell the scan reports:

- **Sample size** and **win rate**.
- **Wilson 95% interval** on the win rate.
- **Mean R** under `+1R / -1R` (the base 1:1 plan), before costs.
- A **normal-approximation test** of the cell win rate against the dataset
  baseline.
- A **one-sample t-test** that mean R differs from zero.
- **Benjamini-Hochberg FDR** across all tested cells, to control false positives.
- A **per-year stability** flag (above the baseline in both 2023 and 2024, with
  n ≥ 15 each).

Dimensions: `asset`, `weekday`, `session` (derived from the entry hour),
`volume`, `pattern`, a stop-size quartile, plus a few pairs.

## Predictive model

`predict_win.py` fits a logistic regression for P(win) from one-hot encoded
categorical features (asset, weekday, session, volume, pattern) plus the
standardized stop size. It reports 5-fold stratified cross-validation AUC and
accuracy, a chronological holdout (train 2023, test 2024), and the largest odds
ratios. A single-feature (pattern-only) model is included for comparison.

Result: the model barely beats a coin toss (CV AUC ≈ 0.52; pattern-only ≈ 0.55;
holdout ≈ 0.53), so the features do not form a reliable predictor on this small,
hand-labelled sample. I report it as-is instead of tuning it to look better.

## Important limitation

The published table keeps only **indicator-generated signals** (`SIGNAL=Sí`);
manual entries are excluded. It is also the **minimal** column set, so it drops
the execution flags (`confirm`, `manual SL`) and the 2:1 outcome. This scan
therefore cannot separate my delayed manual confirmations or manual stop changes,
and reports 1:1 expectancy only. The baseline here (~59%) is the indicator-signal
baseline; the stricter mechanical cohort was about 54%. The full private scan,
which separates cohorts and reports 2:1 expectancy, lives outside this
repository.

Any candidate here is a hypothesis for an independent, automated backtest, not a
validated edge.
