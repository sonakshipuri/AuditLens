"""
run_pipeline.py
----------------
End-to-end AuditLens pipeline. Run this single file to regenerate everything:

    python run_pipeline.py

Steps:
  1. Generate synthetic journal entries (skips if data already exists)
  2. Ingest + clean + load into SQLite
  3. Run rule-based audit tests
  4. Run ML anomaly detection (Isolation Forest)
  5. Combine into final risk scores
  6. Validate against planted ground truth
  7. Generate the audit findings report
  8. Export a dashboard-ready CSV for Power BI
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def main():
    print("=" * 60)
    print("AUDITLENS PIPELINE")
    print("=" * 60)

    csv_path = os.path.join(DATA_DIR, "journal_entries.csv")
    if not os.path.exists(csv_path):
        print("\n[1/7] Generating synthetic journal entries...")
        import generate_data  # noqa: F401 (runs on import)
    else:
        print("\n[1/7] journal_entries.csv already exists, skipping generation.")
        print("      (delete data/journal_entries.csv to regenerate)")

    print("\n[2/7] Ingesting and cleaning data...")
    from ingestion import load_raw_csv, clean, load_to_sqlite, profile
    raw = load_raw_csv()
    df = clean(raw)
    profile(df)
    load_to_sqlite(df)

    print("\n[3/7] Running rule-based audit tests...")
    from audit_tests import run_all_tests, benfords_law_check
    rule_flags = run_all_tests(df)
    rule_flags.to_csv(os.path.join(DATA_DIR, "rule_based_flags.csv"), index=False)
    benford_df = benfords_law_check(df)
    benford_df.to_csv(os.path.join(DATA_DIR, "benford_analysis.csv"), index=False)
    print(f"      Flagged {len(rule_flags)} transactions across all rule tests")

    print("\n[4/7] Running ML anomaly detection (Isolation Forest)...")
    from anomaly_detection import run_isolation_forest
    ml_scores = run_isolation_forest(df)
    ml_scores.to_csv(os.path.join(DATA_DIR, "ml_anomaly_scores.csv"), index=False)
    n_ml_flagged = (ml_scores["ml_flag"] == "anomaly").sum()
    print(f"      Flagged {n_ml_flagged} transactions via ML")

    print("\n[5/7] Combining into final risk scores...")
    from risk_scoring import combine_scores, validate_against_ground_truth
    risk_df = combine_scores(df, rule_flags, ml_scores)
    risk_df.to_csv(os.path.join(DATA_DIR, "final_risk_scores.csv"), index=False)
    print(risk_df["risk_level"].value_counts().to_string())

    print("\n[6/7] Validating against ground truth (synthetic data only)...")
    validate_against_ground_truth(risk_df)

    print("\n[7/7] Generating audit findings report...")
    from generate_report import generate_report
    report_path = generate_report()

    # Dashboard-ready export: one flat table with everything Power BI needs
    dashboard_export = risk_df.merge(df, on="transaction_id", how="left")
    dashboard_path = os.path.join(DATA_DIR, "dashboard_export.csv")
    dashboard_export.to_csv(dashboard_path, index=False)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Report:            reports/audit_findings_report.md")
    print(f"  Dashboard export:  data/dashboard_export.csv  (import this into Power BI)")
    print(f"  Risk scores:       data/final_risk_scores.csv")
    print(f"  SQLite DB:         data/auditlens.db")


if __name__ == "__main__":
    main()
