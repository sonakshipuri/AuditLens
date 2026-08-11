"""
anomaly_detection.py
---------------------
Adds a machine-learning layer on top of the rule-based audit tests.
Uses Isolation Forest to assign every transaction an anomaly score based on
engineered numeric features, independent of the hand-written rules above.
This lets AuditLens catch anomalies that don't match a predefined rule.
"""

import os

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def engineer_features(df):
    """Build a numeric feature matrix for the model."""
    features = pd.DataFrame(index=df.index)
    # Raw amount / log_amount deliberately excluded. IsolationForest ranks
    # points relative to the whole dataset, so raw scale features make the
    # anomaly ranking sensitive to shifts in the *overall* amount distribution
    # (e.g. from generate_data.py changes) even when nothing about a specific
    # transaction's actual risk changed. amount_vs_account_median below is
    # scale-invariant per account and is what should drive this signal.
    features["hour"] = df["hour"]
    features["is_weekend"] = df["is_weekend"].astype(int)
    features["day"] = df["day"]

    # vendor transaction frequency (how often this vendor appears overall)
    vendor_freq = df["vendor"].value_counts()
    features["vendor_frequency"] = df["vendor"].map(vendor_freq)

    # vendor's share of total spend
    vendor_spend_share = df.groupby("vendor")["amount"].sum() / df["amount"].sum()
    features["vendor_spend_share"] = df["vendor"].map(vendor_spend_share)

    # amount relative to the median for that account (captures per-account outliers)
    account_median = df.groupby("account")["amount"].transform("median")
    features["amount_vs_account_median"] = df["amount"] / account_median

    # One-hot encode department/account/entry_type. These are categorical,
    # not ordinal -- label-encoding them as integers (0, 1, 2, ...) would
    # imply a numeric ordering between categories (e.g. "Payroll > Marketing")
    # that doesn't exist and that Isolation Forest's split logic would treat
    # as real. Vendor is intentionally excluded here (40 distinct values)
    # and represented instead via the frequency/spend-share features above,
    # to avoid a very wide, sparse one-hot block.
    categorical_cols = ["department", "account", "entry_type"]
    categorical = pd.get_dummies(df[categorical_cols], prefix=categorical_cols, dtype=int)
    features = pd.concat([features, categorical], axis=1)

    return features


def run_isolation_forest(df, contamination=0.05, random_state=42):
    """
    Fit Isolation Forest and attach ml_anomaly_score + ml_flag to the dataframe.
    contamination=0.05 assumes roughly 5% of transactions are anomalous --
    tune this based on the audit's risk appetite / sample size.
    """
    features = engineer_features(df)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(features)

    # decision_function: higher = more normal, lower/negative = more anomalous.
    # We invert and min-max rescale to a 0-1 "normalized anomaly score" where
    # 1 = most anomalous *relative to the rest of this dataset*. This is NOT
    # a probability of fraud, and is not comparable across different runs or
    # datasets -- it's a relative ranking signal, not a calibrated likelihood.
    raw_score = model.decision_function(features)
    anomaly_score = (raw_score.max() - raw_score) / (raw_score.max() - raw_score.min())

    result = df.copy()
    result["ml_anomaly_score"] = anomaly_score.round(4)
    result["ml_flag"] = model.predict(features)  # -1 = anomaly, 1 = normal
    result["ml_flag"] = result["ml_flag"].map({-1: "anomaly", 1: "normal"})

    return result[["transaction_id", "ml_anomaly_score", "ml_flag"]]


if __name__ == "__main__":
    from ingestion import load_raw_csv, clean

    raw = load_raw_csv()
    df = clean(raw)

    ml_results = run_isolation_forest(df)
    n_flagged = (ml_results["ml_flag"] == "anomaly").sum()
    print(f"Isolation Forest flagged {n_flagged} / {len(ml_results)} transactions "
          f"({n_flagged/len(ml_results)*100:.1f}%)")

    ml_results.to_csv(os.path.join(DATA_DIR, "ml_anomaly_scores.csv"), index=False)
    print(f"Saved to {DATA_DIR}/ml_anomaly_scores.csv")

    print("\nTop 10 highest-risk transactions by normalized ML anomaly score:")
    print(ml_results.sort_values("ml_anomaly_score", ascending=False).head(10))