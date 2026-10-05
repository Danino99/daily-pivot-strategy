# Predictive model — exploratory logistic regression

I fit a logistic regression that estimates the probability that a signal is
a winner from the setup features. It is **illustrative**: the sample is small,
hand-labelled and non-random, so the metrics are exploratory, not a trading edge.

- Records: 2368 (2023–2024, indicator signals only)
- Base win rate: 59.16%
- Baseline accuracy (majority class): 59.16%
- 5-fold CV AUC: 0.523 (± 0.016)
- 5-fold CV accuracy: 58.11%
- For comparison, a model using only the candle pattern: CV AUC 0.551
- Chronological holdout (trained on 2023, tested on 2024): AUC 0.534, accuracy 58.20% (baseline 58.37%)

## Largest coefficients (odds ratios)

| Feature | Odds ratio |
| --- | ---: |
| pattern_Both | 3.891 |
| pattern_None | 0.426 |
| pattern_Pinbar | 0.519 |
| pattern_Engulfing | 1.163 |
| volume_Flat | 0.860 |
| session_00-06_asia | 0.875 |
| asset_USDCHF | 1.135 |
| asset_EURUSD | 0.888 |

## Caveats

- Manual chart-replay labels, not broker fills; no costs or slippage.
- Small, non-random sample; hand-recorded features.
- The candle pattern is the strongest driver; its tags are subjective and the
  deterministic rule is a proposal (`docs/engulfing-rule.md`).
- Adding every feature barely beats the majority-class baseline, and a pattern-only
  model is close: the setup features have little multivariate predictive power on
  this sample. Reported as-is.
- AUC near 0.5 would mean the model adds little over a coin toss; that is the
  honest result here.
