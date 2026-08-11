"""
AuditLens -- Audit Analytics Findings Report

Turns the final risk-scored transaction table into a readable audit
findings report (Markdown), the kind of deliverable an audit analytics
associate would actually hand to a senior/manager -- not just a notebook
of numbers.
"""

import os
from datetime import date

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def generate_report():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # ---------------------------------------------------------
    # Load pipeline outputs
    # ---------------------------------------------------------
    risk_df = pd.read_csv(
        os.path.join(DATA_DIR, "final_risk_scores.csv")
    )

    journal_df = pd.read_csv(
        os.path.join(DATA_DIR, "journal_entries.csv")
    )

    benford_df = pd.read_csv(
        os.path.join(DATA_DIR, "benford_analysis.csv")
    )

    ground_truth_df = pd.read_csv(
        os.path.join(DATA_DIR, "ground_truth.csv")
    )

    # ---------------------------------------------------------
    # Combine transaction-level data
    # ---------------------------------------------------------
    full = risk_df.merge(
        journal_df,
        on="transaction_id",
        how="left"
    )

    validation_df = risk_df.merge(
        ground_truth_df,
        on="transaction_id",
        how="left"
    )

    # ---------------------------------------------------------
    # Basic scope metrics
    # ---------------------------------------------------------
    total_txns = len(full)
    total_value = full["amount"].sum()

    high_risk = full[
        full["risk_level"] == "High"
    ]

    medium_risk = full[
        full["risk_level"] == "Medium"
    ]

    low_risk_count = (
        total_txns
        - len(high_risk)
        - len(medium_risk)
    )

    # ---------------------------------------------------------
    # Validation against synthetic ground truth
    # ---------------------------------------------------------
    planted = validation_df[
        validation_df["is_anomaly"] == 1
    ]

    flagged = validation_df[
        validation_df["risk_level"].isin(["High", "Medium"])
    ]

    true_positives = len(
        validation_df[
            (validation_df["is_anomaly"] == 1)
            & (
                validation_df["risk_level"].isin(
                    ["High", "Medium"]
                )
            )
        ]
    )

    overall_recall = (
        true_positives / len(planted) * 100
        if len(planted) > 0
        else 0
    )

    precision = (
        true_positives / len(flagged) * 100
        if len(flagged) > 0
        else 0
    )

    # ---------------------------------------------------------
    # Vendor concentration validation
    # ---------------------------------------------------------
    vendor_gt = validation_df[
        validation_df["anomaly_type"] == "vendor_concentration"
    ]

    vendor_recall = (
        vendor_gt[
            vendor_gt["risk_level"].isin(["High", "Medium"])
        ].shape[0]
        / len(vendor_gt)
        * 100
        if len(vendor_gt) > 0
        else 0
    )

    # ---------------------------------------------------------
    # Recall by anomaly type
    # ---------------------------------------------------------
    recall_by_type = (
        planted
        .groupby("anomaly_type")["risk_level"]
        .apply(
            lambda x: x.isin(["High", "Medium"]).mean() * 100
        )
        .sort_values()
    )

    weakest_test = (
        recall_by_type.idxmin()
        if not recall_by_type.empty
        else "N/A"
    )

    weakest_recall = (
        recall_by_type.min()
        if not recall_by_type.empty
        else 0
    )

    # ---------------------------------------------------------
    # Top vendors by flagged transaction value
    # ---------------------------------------------------------
    top_vendors_at_risk = (
        full[
            full["risk_level"].isin(["High", "Medium"])
        ]
        .groupby("vendor")["amount"]
        .agg(["count", "sum"])
        .sort_values("sum", ascending=False)
        .head(5)
    )

    # ---------------------------------------------------------
    # Top 10 highest-risk transactions
    # ---------------------------------------------------------
    top_10_flagged = (
        full
        .sort_values("risk_score", ascending=False)
        .head(10)
    )

    # ---------------------------------------------------------
    # Build report
    # ---------------------------------------------------------
    lines = []

    lines.append("# AuditLens -- Audit Analytics Findings Report\n")

    lines.append(
        f"**Generated:** {date.today().isoformat()}"
    )

    lines.append(
        f"**Scope:** Full-year journal entries, "
        f"{total_txns:,} transactions, "
        f"total value ₹{total_value:,.2f}\n"
    )

    # ---------------------------------------------------------
    # 1. Executive Summary
    # ---------------------------------------------------------
    lines.append("## 1. Executive Summary\n")

    lines.append(
        f"A combined rule-based and machine-learning audit analytics "
        f"pipeline was run across {total_txns:,} journal entries. "
        f"**{len(high_risk)} transactions "
        f"({len(high_risk) / total_txns * 100:.1f}%)** were classified "
        f"as **High risk** and **{len(medium_risk)} "
        f"({len(medium_risk) / total_txns * 100:.1f}%)** as "
        f"**Medium risk**, and are recommended for manual review. "
        f"The remaining {low_risk_count:,} transactions were classified "
        f"as **Low risk** and were not prioritized for manual review "
        f"by the current screening framework "
        f"(this reflects the screening thresholds used, not a "
        f"confirmation that those transactions are clean).\n"
    )

    # ---------------------------------------------------------
    # 2. Validation
    # ---------------------------------------------------------
    lines.append(
        "## 2. Validation Against Synthetic Ground Truth\n"
    )

    lines.append(
        f"The framework detected **{overall_recall:.1f}% of planted "
        f"anomalies** and achieved **{precision:.1f}% precision** "
        f"when High and Medium risk transactions were treated as "
        f"the review population. These results evaluate screening "
        f"performance on the synthetic validation set and should "
        f"not be interpreted as fraud-detection accuracy.\n"
    )

    # ---------------------------------------------------------
    # 3. Methodology
    # ---------------------------------------------------------
    lines.append("## 3. Methodology\n")

    lines.append(
        "Two complementary detection approaches were combined into "
        "a single risk score:\n\n"
        "- **Rule-based audit tests**: duplicate transactions, "
        "round-number amounts, off-hours/weekend postings, vendor "
        "spend concentration, statistical (IQR) outliers per "
        "account, and month-end late-hour postings (entries posted "
        "on/after day 28 of the month, at/after 18:00 -- a fixed "
        "date/time rule, not a comparison against a volume baseline).\n"
        "- **Machine learning**: an Isolation Forest model trained "
        "on engineered features (amount, timing, vendor frequency, "
        "vendor spend share, and deviation from account median) to "
        "catch anomalies that do not match a predefined rule. Its "
        "output (`ml_anomaly_score`) is a normalized 0-1 relative "
        "anomaly score, not a probability of fraud.\n\n"
        "Each transaction's final `risk_score` (0-1) is a weighted "
        "combination of the highest-severity rule triggered and the "
        "normalized ML anomaly score, bucketed into Low / Medium / High.\n"
    )

    # ---------------------------------------------------------
    # 4. Benford's Law
    # ---------------------------------------------------------
    lines.append("## 4. Benford's Law Analysis\n")

    lines.append(
        "Leading-digit distribution of transaction amounts was "
        "compared against Benford's Law expected frequencies, by "
        "account category, as a population-level screening technique. "
        "This is a simple maximum-absolute-deviation screen, not a "
        "formal chi-square goodness-of-fit test. Accounts with a "
        "maximum deviation above 0.08 are flagged below. A deviation "
        "from the expected distribution may warrant further "
        "investigation, but does not by itself indicate fraud or "
        "manipulation:\n"
    )

    lines.append(
        benford_df[
            [
                "account",
                "n_transactions",
                "max_deviation",
                "flag",
            ]
        ].to_markdown(index=False)
    )

    lines.append("")

    # ---------------------------------------------------------
    # 5. Top vendors
    # ---------------------------------------------------------
    lines.append(
        "## 5. Top 5 Vendors by Flagged Transaction Value\n"
    )

    vendor_table = (
        top_vendors_at_risk
        .reset_index()
        .rename(
            columns={
                "count": "flagged_transactions",
                "sum": "flagged_value",
            }
        )
    )

    lines.append(
        vendor_table.to_markdown(index=False)
    )

    lines.append("")

    # ---------------------------------------------------------
    # 6. Top 10 highest-risk transactions
    # ---------------------------------------------------------
    lines.append(
        "## 6. Top 10 Highest-Risk Transactions\n"
    )

    display_cols = [
        "transaction_id",
        "date",
        "vendor",
        "account",
        "amount",
        "risk_score",
        "risk_level",
        "reasons",
    ]

    lines.append(
        top_10_flagged[
            display_cols
        ].to_markdown(index=False)
    )

    lines.append("")

    # ---------------------------------------------------------
    # 7. Recommendations
    # ---------------------------------------------------------
    lines.append("## 7. Recommendations\n")

    lines.append(
        "- Prioritize manual review of the **High risk** transaction "
        "population first, given limited audit hours.\n"
        "- Follow up directly with vendors flagged under **vendor "
        "concentration** to confirm legitimacy of the relationship "
        "and check for related-party indicators.\n"
        "- Use **Benford's Law** deviations as a supplementary "
        "population-level diagnostic, and combine them with "
        "transaction-level evidence before initiating further "
        "investigation, rather than treating a deviation alone as "
        "evidence of an issue.\n"
        f"- Recalibrate the vendor-concentration threshold "
        f"(currently a fixed 8% of total spend): validation testing "
        f"showed this test caught only **{vendor_recall:.1f}%** of "
        f"planted vendor-concentration anomalies, the lowest of all "
        f"rule-based tests. As a fixed proof-of-concept parameter "
        f"it would need tuning against a real client's vendor "
        f"distribution, materiality thresholds, and historical "
        f"risk patterns.\n"
    )

    # ---------------------------------------------------------
    # 8. Known limitations
    # ---------------------------------------------------------
    lines.append("## 8. Known Limitations\n")

    benford_all_flagged = (
        (benford_df["flag"] == "REVIEW").all()
    )

    benford_note = ""

    if benford_all_flagged:
        benford_note = (
            "- In this run, **every account population exceeded the "
            "Benford deviation threshold** (all flagged `REVIEW`), "
            "which limits the test's discriminatory value here -- "
            "it isn't distinguishing higher-risk accounts from "
            "lower-risk ones. In production this would call for "
            "population-suitability checks and a calibrated "
            "statistical threshold rather than a fixed 0.08 cutoff.\n"
        )

    lines.append(
        "- This analysis is a proof-of-concept run on synthetic data "
        "with known injected anomalies; thresholds (contamination "
        "rate, concentration %, IQR multiplier) would need tuning "
        "against real client risk appetite and historical fraud "
        "patterns.\n"
        "- Duplicate detection uses exact vendor+amount+date matches; "
        "near-duplicates (off by a few rupees, or split into two "
        "entries) would require fuzzy matching.\n"
        "- The month-end late-hour posting test is a fixed date/time "
        "rule (day >= 28, hour >= 18), not a comparison against a "
        "historical volume baseline -- it does not detect an actual "
        "spike in posting volume.\n"
        f"{benford_note}"
        "- The ML model is unsupervised and re-trained fresh each run; "
        "in production it would benefit from feedback loops based "
        "on which flagged transactions auditors confirm vs. dismiss.\n"
    )

    # ---------------------------------------------------------
    # Write report
    # ---------------------------------------------------------
    report_text = "\n".join(lines)

    out_path = os.path.join(
        REPORTS_DIR,
        "audit_findings_report.md"
    )

    with open(
        out_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(report_text)

    print(f"Report saved to {out_path}")

    return out_path


if __name__ == "__main__":
    generate_report()