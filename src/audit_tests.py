"""
audit_tests.py
--------------
Rule-based audit tests, mirroring techniques real audit analytics teams use:
  1. Duplicate transactions
  2. Round-number transactions
  3. Off-hours / weekend postings
  4. Vendor concentration
  5. Statistical outliers (IQR per account)
  6. Month-end late-hour postings
  7. Benford's Law leading-digit test

Each test function takes the cleaned dataframe and returns a set of
transaction_ids it flags, plus a short reason string per flag.
"""

import os
from collections import Counter

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def test_duplicates(df):
    """Flag transactions that share vendor + amount + date with another entry."""
    subset = ["vendor", "amount", "date"]
    dup_mask = df.duplicated(subset=subset, keep=False)
    flagged = df.loc[dup_mask, "transaction_id"]
    return {tid: "Duplicate vendor+amount+date combination" for tid in flagged}


def test_round_numbers(df):
    """Flag suspiciously round amounts (e.g., exactly 50000, 100000)."""
    is_round = (df["amount"] % 10000 == 0) & (df["amount"] >= 10000)
    flagged = df.loc[is_round, "transaction_id"]
    return {tid: "Round-number amount" for tid in flagged}


def test_off_hours_weekend(df):
    """Flag weekend postings or postings outside 7am-8pm."""
    off = df["is_weekend"] | (df["hour"] < 7) | (df["hour"] > 20)
    flagged = df.loc[off, "transaction_id"]
    return {tid: "Posted on weekend or outside business hours" for tid in flagged}


def test_vendor_concentration(df, threshold_pct=8.0):
    """Flag transactions from vendors whose total spend exceeds threshold% of overall spend."""
    total_spend = df["amount"].sum()
    vendor_spend = df.groupby("vendor")["amount"].sum()
    risky_vendors = vendor_spend[vendor_spend / total_spend * 100 > threshold_pct].index
    flagged = df.loc[df["vendor"].isin(risky_vendors), "transaction_id"]
    return {tid: f"Vendor concentration risk (>{threshold_pct}% of total spend)" for tid in flagged}


def test_statistical_outliers(df):
    """Flag amounts that are IQR outliers WITHIN their own account category."""
    flagged = {}
    for account, group in df.groupby("account"):
        q1, q3 = group["amount"].quantile([0.25, 0.75])
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        outliers = group.loc[group["amount"] > upper, "transaction_id"]
        for tid in outliers:
            flagged[tid] = f"Statistical outlier for account '{account}' (IQR method)"
    return flagged


def test_month_end_late_hour_posting(df):
    """
    Flag entries in the last 3 days of a month posted late in the day (18:00+).

    Note: this is a fixed date/time rule, not a comparison against a volume
    baseline -- it does NOT detect an actual "spike" in posting volume
    relative to normal month-end activity, just entries that match this
    time window.
    """
    is_month_end = df["day"] >= 28
    is_late = df["hour"] >= 18
    flagged = df.loc[is_month_end & is_late, "transaction_id"]
    return {tid: "Month-end late-hour posting" for tid in flagged}


def benfords_law_check(df):
    """
    Compare the leading-digit distribution of amounts against Benford's Law.
    Returns a dataframe of expected vs actual frequency, plus flagged accounts
    whose maximum absolute deviation from the expected frequency exceeds a
    threshold. This is a simple maximum-absolute-deviation screen, NOT a
    formal chi-square goodness-of-fit test -- no chi-square statistic or
    p-value is computed here.
    Note: this flags PATTERNS (by account), not individual transactions.
    """
    benford_expected = {d: np.log10(1 + 1 / d) for d in range(1, 10)}

    def leading_digit(x):
        s = str(abs(x)).lstrip("0").replace(".", "")
        return int(s[0]) if s else None

    df = df.copy()
    df["leading_digit"] = df["amount"].apply(leading_digit)

    results = []
    for account, group in df.groupby("account"):
        n = len(group)
        counts = Counter(group["leading_digit"])
        row = {"account": account, "n_transactions": n}
        max_deviation = 0
        for d in range(1, 10):
            actual_pct = counts.get(d, 0) / n
            expected_pct = benford_expected[d]
            row[f"digit_{d}_actual"] = round(actual_pct, 3)
            row[f"digit_{d}_expected"] = round(expected_pct, 3)
            max_deviation = max(max_deviation, abs(actual_pct - expected_pct))
        row["max_deviation"] = round(max_deviation, 3)
        row["flag"] = "REVIEW" if max_deviation > 0.08 else "OK"
        results.append(row)

    return pd.DataFrame(results).sort_values("max_deviation", ascending=False)


def run_all_tests(df):
    """Run every transaction-level test and merge results into one flags table."""
    tests = {
        "duplicate": test_duplicates,
        "round_number": test_round_numbers,
        "off_hours_weekend": test_off_hours_weekend,
        "vendor_concentration": test_vendor_concentration,
        "statistical_outlier": test_statistical_outliers,
        "month_end_late_hour_posting": test_month_end_late_hour_posting,
    }

    all_flags = {}  # transaction_id -> {test_name: reason}
    for test_name, fn in tests.items():
        result = fn(df)
        for tid, reason in result.items():
            all_flags.setdefault(tid, {})[test_name] = reason

    rows = []
    for tid, tests_hit in all_flags.items():
        rows.append({
            "transaction_id": tid,
            "n_tests_triggered": len(tests_hit),
            "tests_triggered": ", ".join(tests_hit.keys()),
            "reasons": " | ".join(tests_hit.values()),
        })

    flags_df = pd.DataFrame(rows)
    return flags_df


if __name__ == "__main__":
    from ingestion import load_raw_csv, clean

    raw = load_raw_csv()
    df = clean(raw)

    flags_df = run_all_tests(df)
    print(f"\nRule-based tests flagged {len(flags_df)} unique transactions "
          f"out of {len(df)} total ({len(flags_df)/len(df)*100:.1f}%)")
    print(flags_df["n_tests_triggered"].value_counts().sort_index())

    flags_df.to_csv(os.path.join(DATA_DIR, "rule_based_flags.csv"), index=False)
    print(f"Saved to {DATA_DIR}/rule_based_flags.csv")

    benford_df = benfords_law_check(df)
    benford_df.to_csv(os.path.join(DATA_DIR, "benford_analysis.csv"), index=False)
    print(f"\nBenford's Law analysis saved to {DATA_DIR}/benford_analysis.csv")
    print(benford_df[["account", "n_transactions", "max_deviation", "flag"]])
