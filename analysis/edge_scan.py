"""Exploratory subgroup scan on the published, clean signal table.

Runs on data/signals-2023-2024.csv, which is a minimal public subset: it does not
carry the execution flags (signal / confirmation / manual stop) or the 2:1
outcome, so this scan cannot rebuild the strict mechanical cohort or the 2:1
expectancy. It reports win-rate subgroups with false-positive control only.

Method per subgroup cell: sample size, win rate, Wilson 95% interval, mean R
under +1R/-1R, a normal-approximation test of the cell win rate versus the
dataset baseline, a one-sample t-test that mean R differs from zero,
Benjamini-Hochberg FDR across cells, and a per-year stability check.

    python analysis/edge_scan.py
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data" / "signals-2023-2024.csv"
OUT_REPORT = HERE / "public_edge_report.md"

MIN_N = 30

SINGLE_DIMENSIONS = ["asset", "weekday", "session", "volume", "pattern", "sl_bucket"]
PAIR_DIMENSIONS = [
    ("asset", "session"),
    ("volume", "pattern"),
    ("session", "pattern"),
    ("asset", "volume"),
]


def session_of(hour: int) -> str:
    if 0 <= hour <= 6:
        return "00-06_asia"
    if 7 <= hour <= 11:
        return "07-11_london"
    if 12 <= hour <= 16:
        return "12-16_ny_am"
    return "17-23_ny_pm"


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round((center - half) * 100, 2), round((center + half) * 100, 2))


def proportion_p(wins: int, n: int, p0: float) -> float:
    if n == 0:
        return float("nan")
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return float("nan")
    z = (wins / n - p0) / se
    return float(2 * stats.norm.sf(abs(z)))


def load() -> pd.DataFrame:
    frame = pd.read_csv(DATA, keep_default_na=False)
    frame["sl_pct"] = pd.to_numeric(frame["sl_pct"], errors="coerce")
    frame["session"] = frame["hour"].astype(int).map(session_of)
    frame["year"] = frame["date"].str.slice(0, 4)
    frame["win"] = (frame["result"] == "W").astype(int)
    frame["R"] = frame["win"].map({1: 1.0, 0: -1.0})
    frame["sl_bucket"] = pd.qcut(
        frame["sl_pct"], 4, labels=["Q1_smallest", "Q2", "Q3", "Q4_widest"]
    )
    return frame


def mean_r(values: pd.Series) -> tuple[float, float]:
    clean = values.dropna()
    if len(clean) < 3:
        return (float("nan"), float("nan"))
    return (round(float(clean.mean()), 4), float(stats.ttest_1samp(clean, 0.0).pvalue))


def scan(frame: pd.DataFrame, baseline_p: float) -> pd.DataFrame:
    rows: list[dict] = []
    dimensions = [(d,) for d in SINGLE_DIMENSIONS] + PAIR_DIMENSIONS
    for dims in dimensions:
        grouped = frame.dropna(subset=list(dims)).groupby(list(dims), dropna=True)
        for key, group in grouped:
            if not isinstance(key, tuple):
                key = (key,)
            n = len(group)
            if n < MIN_N:
                continue
            wins = int(group["win"].sum())
            mean_r_value, p_r = mean_r(group["R"])
            per_year = {
                year: (len(g), round(100 * g["win"].mean(), 1))
                for year, g in group.groupby("year")
            }
            rows.append(
                {
                    "cell": " | ".join(f"{d}={v}" for d, v in zip(dims, key)),
                    "n": n,
                    "wins": wins,
                    "winrate": round(100 * wins / n, 2),
                    "wilson_low": wilson(wins, n)[0],
                    "wilson_high": wilson(wins, n)[1],
                    "mean_R": mean_r_value,
                    "p_win": proportion_p(wins, n, baseline_p),
                    "p_R": p_r,
                    "per_year": per_year,
                }
            )
    result = pd.DataFrame(rows)
    for column, out in [("p_win", "q_win"), ("p_R", "q_R")]:
        mask = result[column].notna()
        q = pd.Series(np.nan, index=result.index)
        if mask.any():
            q.loc[mask] = multipletests(result.loc[mask, column], method="fdr_bh")[1]
        result[out] = q
    return result


def main() -> None:
    frame = load()
    baseline_p = frame["win"].mean()
    baseline_r = frame["R"].mean()
    scored = scan(frame, baseline_p).sort_values(["q_win", "q_R"])
    scored["stable"] = scored["per_year"].apply(
        lambda years: len([1 for n, wr in years.values() if n >= 15 and wr > baseline_p * 100])
        >= 2
    )

    lines = [
        "# Exploratory edge scan — clean public subset",
        "",
        "This report helps build the interactive dashboard in `dashboard/`.",
        "It is **not** a validated strategy and uses manually replayed outcomes.",
        "",
        f"- Records: {len(frame)} (2023-2024, indicator signals only)",
        f"- Baseline win rate: {baseline_p * 100:.2f}%",
        f"- Baseline mean R (1:1): {baseline_r:+.4f}",
        "- Indicator-generated signals only; manual entries are excluded.",
        "- The table still drops the execution flags and the 2:1 outcome, so mean R",
        "  is 1:1 only and manual confirmations/stop changes are not separated out.",
        "- FDR is Benjamini-Hochberg across all tested cells.",
        "",
        f"### Cells with n>={MIN_N}, sorted by q_win",
        "",
        "| cell | n | win% | Wilson95 | mean R | q_win | stable | per-year (n,win%) |",
        "| --- | ---: | ---: | --- | ---: | ---: | :---: | --- |",
    ]
    for _, row in scored.head(25).iterrows():
        years = ", ".join(f"{y}:{n}/{wr}" for y, (n, wr) in sorted(row["per_year"].items()))
        lines.append(
            f"| {row['cell']} | {row['n']} | {row['winrate']:.1f} | "
            f"{row['wilson_low']:.1f}-{row['wilson_high']:.1f} | {row['mean_R']:+.3f} | "
            f"{row['q_win']:.3f} | {'yes' if row['stable'] else 'no'} | {years} |"
        )
    lines += [
        "",
        "## Caveats",
        "",
        "- Manual chart-replay labels, not broker fills; no costs, slippage, or exit times.",
        "- Candle-pattern tags were recorded by hand; the deterministic rule is in",
        "  `docs/engulfing-rule.md`.",
        "- `pattern=None` means no candle pattern was recorded for that signal.",
        "- A low q-value on a small cell is a hypothesis to test, not an edge.",
        "- Nested pair cells violate the independence assumption of FDR; prefer the",
        "  broad single-dimension cells.",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_REPORT}")
    print(f"tested cells (n>={MIN_N}): {len(scored)}")


if __name__ == "__main__":
    main()
