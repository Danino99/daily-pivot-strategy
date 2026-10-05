"""Fit a small, honest predictive model on the published signal sample.

A logistic regression that estimates P(win) from the setup features, evaluated
with stratified 5-fold cross-validation and a chronological holdout (train 2023,
test 2024). This is illustrative: the sample is small, hand-labelled and
non-random, so read the metrics as exploratory, not as a trading edge.

    python analysis/predict_win.py

Outputs: data/model_metrics.json and analysis/model_report.md
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[0] / "data" / "signals-2023-2024.csv"
OUT_JSON = HERE.parents[0] / "data" / "model_metrics.json"
OUT_REPORT = HERE / "model_report.md"

CATEGORICAL = ["asset", "weekday", "session", "volume", "pattern"]
NUMERIC = ["sl_pct"]
FEATURES = CATEGORICAL + NUMERIC


def session_of(hour: int) -> str:
    if 0 <= hour <= 6:
        return "00-06_asia"
    if 7 <= hour <= 11:
        return "07-11_london"
    if 12 <= hour <= 16:
        return "12-16_ny_am"
    return "17-23_ny_pm"


def load() -> pd.DataFrame:
    frame = pd.read_csv(DATA, keep_default_na=False)
    frame["sl_pct"] = pd.to_numeric(frame["sl_pct"], errors="coerce")
    frame["hour"] = frame["hour"].astype(int)
    frame["session"] = frame["hour"].map(session_of)
    frame["year"] = frame["date"].str.slice(0, 4)
    frame = frame[(frame["weekday"].str.strip() != "") & frame["sl_pct"].notna()]
    frame["win"] = (frame["result"] == "W").astype(int)
    return frame


def make_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("num", StandardScaler(), NUMERIC),
        ]
    )
    return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])


def main() -> None:
    frame = load()
    X, y = frame[FEATURES], frame["win"]
    base_rate = float(y.mean())
    baseline_accuracy = max(base_rate, 1 - base_rate)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    auc_scores = cross_val_score(make_pipeline(), X, y, cv=cv, scoring="roc_auc")
    acc_scores = cross_val_score(make_pipeline(), X, y, cv=cv, scoring="accuracy")

    pattern_only = Pipeline(
        [
            ("enc", OneHotEncoder(handle_unknown="ignore")),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pattern_auc = cross_val_score(pattern_only, frame[["pattern"]], y, cv=cv, scoring="roc_auc")

    train = frame[frame["year"] == "2023"]
    test = frame[frame["year"] == "2024"]
    holdout = make_pipeline().fit(train[FEATURES], train["win"])
    proba = holdout.predict_proba(test[FEATURES])[:, 1]
    holdout_auc = float(roc_auc_score(test["win"], proba))
    holdout_accuracy = float(accuracy_score(test["win"], (proba >= 0.5).astype(int)))
    holdout_baseline = float(max(test["win"].mean(), 1 - test["win"].mean()))

    full = make_pipeline().fit(X, y)
    encoder = full.named_steps["pre"].named_transformers_["cat"]
    names = encoder.get_feature_names_out(CATEGORICAL).tolist() + NUMERIC
    coefs = full.named_steps["clf"].coef_[0]
    odds = np.exp(coefs)
    order = np.argsort(-np.abs(coefs))
    top = [
        {
            "feature": names[i],
            "odds_ratio": round(float(odds[i]), 3),
            "coef": round(float(coefs[i]), 3),
        }
        for i in order[:8]
    ]

    metrics = {
        "generated_at": date.today().isoformat(),
        "model": "logistic regression",
        "n": int(len(frame)),
        "base_rate": round(base_rate, 4),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "cv_folds": 5,
        "cv_auc_mean": round(float(auc_scores.mean()), 4),
        "cv_auc_std": round(float(auc_scores.std()), 4),
        "cv_accuracy_mean": round(float(acc_scores.mean()), 4),
        "pattern_only_cv_auc_mean": round(float(pattern_auc.mean()), 4),
        "holdout": "trained on 2023, tested on 2024",
        "holdout_auc": round(holdout_auc, 4),
        "holdout_accuracy": round(holdout_accuracy, 4),
        "holdout_baseline_accuracy": round(holdout_baseline, 4),
        "features": FEATURES,
        "top_features": top,
    }
    OUT_JSON.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Predictive model — exploratory logistic regression",
        "",
        "I fit a logistic regression that estimates the probability that a signal is",
        "a winner from the setup features. It is **illustrative**: the sample is small,",
        "hand-labelled and non-random, so the metrics are exploratory, not a trading edge.",
        "",
        f"- Records: {metrics['n']} (2023–2024, indicator signals only)",
        f"- Base win rate: {metrics['base_rate'] * 100:.2f}%",
        f"- Baseline accuracy (majority class): {metrics['baseline_accuracy'] * 100:.2f}%",
        f"- 5-fold CV AUC: {metrics['cv_auc_mean']:.3f} (± {metrics['cv_auc_std']:.3f})",
        f"- 5-fold CV accuracy: {metrics['cv_accuracy_mean'] * 100:.2f}%",
        f"- For comparison, a model using only the candle pattern: "
        f"CV AUC {metrics['pattern_only_cv_auc_mean']:.3f}",
        f"- Chronological holdout ({metrics['holdout']}): "
        f"AUC {metrics['holdout_auc']:.3f}, accuracy {metrics['holdout_accuracy'] * 100:.2f}% "
        f"(baseline {metrics['holdout_baseline_accuracy'] * 100:.2f}%)",
        "",
        "## Largest coefficients (odds ratios)",
        "",
        "| Feature | Odds ratio |",
        "| --- | ---: |",
    ]
    for item in top:
        lines.append(f"| {item['feature']} | {item['odds_ratio']:.3f} |")
    lines += [
        "",
        "## Caveats",
        "",
        "- Manual chart-replay labels, not broker fills; no costs or slippage.",
        "- Small, non-random sample; hand-recorded features.",
        "- The candle pattern is the strongest driver; its tags are subjective and the",
        "  deterministic rule is a proposal (`docs/engulfing-rule.md`).",
        "- Adding every feature barely beats the majority-class baseline, and a pattern-only",
        "  model is close: the setup features have little multivariate predictive power on",
        "  this sample. Reported as-is.",
        "- AUC near 0.5 would mean the model adds little over a coin toss; that is the",
        "  honest result here.",
        "",
    ]
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_REPORT}")
    print(f"CV AUC {metrics['cv_auc_mean']:.3f} | holdout AUC {metrics['holdout_auc']:.3f}")


if __name__ == "__main__":
    main()
