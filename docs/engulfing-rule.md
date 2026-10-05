# Engulfing candle rule (proposed)

## Why this rule

In my replay, the signals that coincided with a candle I had tagged "Engulfing"
performed much better than the baseline, and it was the only feature that
survived multiple-comparison control. But I tagged it **by eye**, so I need a
deterministic, codeable definition before I can reproduce it and test it on a
fresh sample.

## Definition

Work on the **signal timeframe** (the timeframe the sweep fires on). For candle
`i`, with `open`/`close` in script coordinates (`[0]` = current):

- `body(i) = |close[i] - open[i]|`
- `bull(i) = close[i] > open[i]`
- `bear(i) = close[i] < open[i]`

**Bullish engulfing (long setup):** the current candle is bullish, the previous
candle is bearish, and the current real body covers the previous real body:

```
bull(0) and bear(1) and open[0] < close[1] and close[0] > open[1]
```

**Bearish engulfing (short setup):** the current candle is bearish, the previous
candle is bullish, and the current real body covers the previous real body:

```
bear(0) and bull(1) and open[0] > close[1] and close[0] < open[1]
```

I use **strict** inequalities so the current body must fully pass the previous
body; equal prices (a doji edge) do not count. The rule is **body-based**, not
wick-based: a long wick on the previous candle does not need to be covered.

## Alignment with the sweep

The sweep is a reversal setup, so I align the pattern with the trade direction:

- **Short setup** (prior-day high swept): require a **bearish engulfing** on the
  signal candle.
- **Long setup** (prior-day low swept): require a **bullish engulfing** on the
  signal candle.

Optionally the pattern could be allowed within `N` bars of the signal (default:
same bar). I would keep the same-bar version as the primary rule and test the
window as a variant.

## Optional strength filters (to test, not assumed)

- **Minimum body:** `body(0) >= k * ATR(14)` with `k` around 0.5–1.0, to reject
  tiny candles.
- **Non-trivial previous candle:** `body(1) >= m * ATR(14)`.
- **Higher-timeframe direction:** already covered by the Supertrend filter in
  the strategy.

I would report the base rule first and add these filters only if they hold up
out of sample.

## Reference implementation (Pine Script v6)

```pine
// Engulfing de cuerpo, evaluado en el timeframe de la señal
bull(i) => close[i] > open[i]
bear(i) => close[i] < open[i]

engulfBull = bull(0) and bear(1) and open[0] < close[1] and close[0] > open[1]
engulfBear = bear(0) and bull(1) and open[0] > close[1] and close[0] < open[1]

// Alineado con el sweep
sellSignal = sweep_high_signal and engulfBear
buySignal  = sweep_low_signal  and engulfBull
```

In the strategy, the entry would be gated on `buySignal` / `sellSignal` instead
of the raw `sweep_low_signal` / `sweep_high_signal`.

## How I will test it

1. Reclassify the historical signals with this rule (instead of my manual tags)
   and compare the Engulfing cohort against its cohort baseline.
2. Chronological split: observe on 2023–2024 and treat 2025 as a holdout.
3. Keep the **strict mechanical cohort** (indicator signal, no manual
   confirmation, no manual stop, no `TOOK` filter).
4. Report sample size, win rate with Wilson intervals, and mean R under 1:1 and
   2:1, before and after realistic costs.
5. Apply Benjamini-Hochberg FDR across the tested dimensions to control false
   positives.
6. Prefer the **broad Engulfing group** over nested combinations (Engulfing +
   session + volume), because nesting breaks the independence assumption.

## What would count as success

- A stable improvement over baseline across years, a holdout that agrees, and a
  positive expectancy after realistic costs — with enough sample. The 2025
  holdout has only around a dozen signals, too few to confirm the rule on its
  own.

## Caveats

- My manual tags may not reproduce exactly under this rule; a lower but honest
  win rate is acceptable.
- This is still a hypothesis until an independent, automated backtest confirms
  it.
- Not trading advice.
