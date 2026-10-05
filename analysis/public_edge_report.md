# Exploratory edge scan — clean public subset

This report helps build the interactive dashboard in `dashboard/`.
It is **not** a validated strategy and uses manually replayed outcomes.

- Records: 2370 (2023-2024, indicator signals only)
- Baseline win rate: 59.16%
- Baseline mean R (1:1): +0.1831
- Indicator-generated signals only; manual entries are excluded.
- The table still drops the execution flags and the 2:1 outcome, so mean R
  is 1:1 only and manual confirmations/stop changes are not separated out.
- FDR is Benjamini-Hochberg across all tested cells.

### Cells with n>=30, sorted by q_win

| cell | n | win% | Wilson95 | mean R | q_win | stable | per-year (n,win%) |
| --- | ---: | ---: | --- | ---: | ---: | :---: | --- |
| pattern=Engulfing | 186 | 78.0 | 71.5-83.3 | +0.559 | 0.000 | yes | 2023:104/75.0, 2024:82/81.7 |
| volume=Asc | pattern=Engulfing | 83 | 81.9 | 72.3-88.7 | +0.639 | 0.001 | yes | 2023:48/85.4, 2024:35/77.1 |
| session=17-23_ny_pm | pattern=Engulfing | 49 | 85.7 | 73.3-92.9 | +0.714 | 0.005 | yes | 2023:25/80.0, 2024:24/91.7 |
| session=07-11_london | pattern=Engulfing | 65 | 81.5 | 70.5-89.1 | +0.631 | 0.006 | yes | 2023:33/78.8, 2024:32/84.4 |
| asset=EURUSD | volume=Flat | 31 | 29.0 | 16.1-46.6 | -0.419 | 0.013 | no | 2023:13/38.5, 2024:18/22.2 |
| volume=Desc | pattern=Engulfing | 75 | 76.0 | 65.2-84.2 | +0.520 | 0.049 | yes | 2023:41/68.3, 2024:34/85.3 |
| pattern=None | 1648 | 56.1 | 53.7-58.5 | +0.123 | 0.172 | no | 2023:795/56.6, 2024:853/55.7 |
| volume=Asc | pattern=None | 724 | 55.1 | 51.5-58.7 | +0.102 | 0.325 | no | 2023:350/55.4, 2024:374/54.8 |
| volume=Flat | pattern=None | 179 | 51.4 | 44.1-58.6 | +0.028 | 0.374 | no | 2023:51/51.0, 2024:128/51.6 |
| session=00-06_asia | pattern=None | 374 | 54.0 | 48.9-59.0 | +0.080 | 0.416 | no | 2023:196/56.6, 2024:178/51.1 |
| asset=USDCHF | volume=Asc | 116 | 67.2 | 58.3-75.1 | +0.345 | 0.576 | yes | 2023:71/66.2, 2024:45/68.9 |
| session=00-06_asia | pattern=Engulfing | 49 | 71.4 | 57.6-82.2 | +0.429 | 0.576 | yes | 2023:29/75.9, 2024:20/65.0 |
| session=17-23_ny_pm | pattern=None | 572 | 55.6 | 51.5-59.6 | +0.112 | 0.576 | no | 2023:262/54.2, 2024:310/56.8 |
| asset=GBPCHF | volume=Flat | 34 | 44.1 | 28.9-60.5 | -0.118 | 0.576 | no | 2023:9/44.4, 2024:25/44.0 |
| volume=Flat | 245 | 54.3 | 48.0-60.4 | +0.086 | 0.782 | no | 2023:76/53.9, 2024:169/54.4 |
| asset=GBPCHF | volume=Desc | 133 | 65.4 | 57.0-73.0 | +0.308 | 0.861 | yes | 2023:75/65.3, 2024:58/65.5 |
| asset=NZDUSD | session=17-23_ny_pm | 137 | 65.0 | 56.7-72.5 | +0.299 | 0.869 | no | 2023:68/58.8, 2024:69/71.0 |
| asset=AUDCHF | volume=Desc | 124 | 65.3 | 56.6-73.1 | +0.306 | 0.869 | yes | 2023:67/64.2, 2024:57/66.7 |
| asset=USDCAD | volume=Spike | 34 | 70.6 | 53.8-83.2 | +0.412 | 0.869 | no | 2023:13/76.9, 2024:21/66.7 |
| asset=NZDUSD | session=00-06_asia | 52 | 50.0 | 36.9-63.1 | +0.000 | 0.869 | no | 2023:28/50.0, 2024:24/50.0 |
| session=00-06_asia | 545 | 56.5 | 52.3-60.6 | +0.130 | 0.894 | no | 2023:282/58.9, 2024:263/54.0 |
| session=07-11_london | pattern=None | 551 | 56.4 | 52.3-60.5 | +0.129 | 0.894 | no | 2023:263/56.7, 2024:288/56.2 |
| asset=AUDCHF | volume=Asc | 169 | 54.4 | 46.9-61.8 | +0.089 | 0.894 | no | 2023:64/59.4, 2024:105/51.4 |
| asset=EURUSD | session=00-06_asia | 105 | 53.3 | 43.8-62.6 | +0.067 | 0.909 | no | 2023:53/50.9, 2024:52/55.8 |
| weekday=Thursday | 464 | 56.5 | 51.9-60.9 | +0.129 | 0.925 | no | 2023:233/54.5, 2024:231/58.4 |

## Caveats

- Manual chart-replay labels, not broker fills; no costs, slippage, or exit times.
- Candle-pattern tags were recorded by hand; the deterministic rule is in
  `docs/engulfing-rule.md`.
- `pattern=None` means no candle pattern was recorded for that signal.
- A low q-value on a small cell is a hypothesis to test, not an edge.
- Nested pair cells violate the independence assumption of FDR; prefer the
  broad single-dimension cells.
