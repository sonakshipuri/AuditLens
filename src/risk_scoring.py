"""
risk_scoring.py
----------------
Combines rule-based audit test flags with the ML anomaly score into one
consolidated risk_score + risk_level per transaction. Also validates the
pipeline against the synthetic ground truth (data/ground_truth.csv) so you
can quote a concrete precision/recall number in interviews.
"""

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")



# Severity weight per rule test, reflecting how strong a red flag it is on
# its own (an auditor treats a duplicate as high-confidence regardless of
# whether anything else also fired, whereas a single off-hours posting is
# weaker evidence by itself).
TEST_SEVERITY = {
    "duplicate": 0.90,
    "statistical_outlier": 0.80,
    "vendor_concentration": 0.70,
    "round_number": 0.55,
    "month_end_late_hour_posting": 0.50,
    "off_hours_weekend": 0.40,
}


def combine_scores(df, rule_flags_df, ml_scores_df):
    """
    rule_component = MAX severity across all rule tests a transaction triggered
                      (a transaction shouldn't need 2 weak signals to look
                      as risky as one strong one)
    risk_score      = 0.5 * rule_component + 0.5 * ml_anomaly_score
    risk_level:       High (>0.7), Medium (0.4-0.7), Low (<0.4)
    """
    merged = df[["transaction_id"]].copy()

    merged = merged.merge(
        rule_flags_df[["transaction_id", "n_tests_triggered", "tests_triggered", "reasons"]],
        on="transaction_id", how="left"
    )
    merged["n_tests_triggered"] = merged["n_tests_triggered"].fillna(0)
    merged["tests_triggered"] = merged["tests_triggered"].fillna("")
    merged["reasons"] = merged["reasons"].fillna("")

    def max_severity(tests_str):
        if not tests_str:
            return 0.0
        names = [t.strip() for t in tests_str.split(",")]
        return max((TEST_SEVERITY.get(n, 0.3) for n in names), default=0.0)

    rule_component = merged["tests_triggered"].apply(max_severity)

    merged = merged.merge(ml_scores_df, on="transaction_id", how="left")
    merged["ml_anomaly_score"] = merged["ml_anomaly_score"].fillna(0)

    merged["risk_score"] = (0.5 * rule_component + 0.5 * merged["ml_anomaly_score"]).round(4)

    def bucket(score):
        if score > 0.7:
            return "High"
        elif score > 0.4:
            return "Medium"
        return "Low"

    merged["risk_level"] = merged["risk_score"].apply(bucket)
    return merged.sort_values("risk_score", ascending=False)


def validate_against_ground_truth(risk_df, ground_truth_path=None):
    """
    Compares flagged transactions (risk_level in High/Medium) against the
    synthetic ground truth to compute recall: what % of planted anomalies
    did the pipeline actually catch.
    """
    gt_path = ground_truth_path or os.path.join(DATA_DIR, "ground_truth.csv")
    if not os.path.exists(gt_path):
        print("No ground truth file found -- skipping validation (expected for real client data).")
        return None

    gt = pd.read_csv(gt_path)
    merged = risk_df.merge(gt, on="transaction_id", how="left")
    merged["is_anomaly"] = merged["is_anomaly"].fillna(0).astype(int)

    actual_anomalies = merged[merged["is_anomaly"] == 1]
    flagged = merged[merged["risk_level"].isin(["High", "Medium"])]

    true_positives = len(actual_anomalies[actual_anomalies["risk_level"].isin(["High", "Medium"])])
    recall = true_positives / len(actual_anomalies) if len(actual_anomalies) else 0
    precision = true_positives / len(flagged) if len(flagged) else 0

    print("\n--- VALIDATION AGAINST PLANTED GROUND TRUTH ---")
    print(f"Planted anomalies:            {len(actual_anomalies)}")
    print(f"Flagged as High/Medium risk:  {len(flagged)}")
    print(f"True positives caught:        {true_positives}")
    print(f"Recall (of planted anomalies caught):    {recall*100:.1f}%")
    print(f"Precision (of flags that were real):     {precision*100:.1f}%")

    print("\nRecall by anomaly type:")
    print(
        actual_anomalies.groupby("anomaly_type")["risk_level"]
        .apply(lambda s: (s.isin(["High", "Medium"])).mean() * 100)
        .round(1)
    )
    return {"recall": recall, "precision": precision, "true_positives": true_positives}


if __name__ == "__main__":
    from ingestion import load_raw_csv, clean
    from audit_tests import run_all_tests
    from anomaly_detection import run_isolation_forest

    raw = load_raw_csv()
    df = clean(raw)

    rule_flags = run_all_tests(df)
    ml_scores = run_isolation_forest(df)

    risk_df = combine_scores(df, rule_flags, ml_scores)
    risk_df.to_csv(os.path.join(DATA_DIR, "final_risk_scores.csv"), index=False)

    print("Risk level distribution:")
    print(risk_df["risk_level"].value_counts())
    print(f"\nSaved consolidated risk scores to {DATA_DIR}/final_risk_scores.csv")

    validate_against_ground_truth(risk_df)
