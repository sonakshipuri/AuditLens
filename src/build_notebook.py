"""
Builds auditlens_walkthrough.ipynb using nbformat, so the JSON is always
valid. Run once with: python build_notebook.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

# ---------------------------------------------------------------------------
md("""# AuditLens — Audit Analytics & Anomaly Detection Walkthrough

This notebook walks through the full AuditLens pipeline end to end:
generating synthetic journal entries with planted anomalies, running
rule-based audit tests, layering on ML anomaly detection, scoring risk,
and validating the results against ground truth.

The underlying logic lives in `src/` as standalone modules — this notebook
imports and calls them rather than duplicating logic, so the pipeline stays
runnable both as a script (`python run_pipeline.py`) and interactively here.

**Sections:**
1. Setup & data generation
2. Data profiling
3. Rule-based audit tests
4. Benford's Law analysis
5. ML anomaly detection (Isolation Forest)
6. Combined risk scoring
7. Validation against ground truth
8. Key findings visualizations
""")

# ---------------------------------------------------------------------------
md("## 1. Setup")
code("""import sys, os
sys.path.insert(0, os.path.abspath('../src'))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (10, 5)
pd.set_option('display.max_columns', None)
""")

md("""### Generate (or load) the synthetic dataset

`generate_data.py` builds a synthetic general-ledger-style dataset with
~8,000 normal transactions and ~140 deliberately injected anomalies across
six categories (duplicates, round numbers, off-hours postings, vendor
concentration, statistical outliers, month-end spikes). Ground truth labels
are kept separately so detection performance can be measured honestly.""")
code("""import generate_data  # runs on import if data doesn't already exist
""")

# ---------------------------------------------------------------------------
md("## 2. Load & Profile the Data")
code("""from ingestion import load_raw_csv, clean, profile

raw = load_raw_csv()
df = clean(raw)
df.head()
""")

code("""profile(df)
""")

code("""fig, axes = plt.subplots(1, 2, figsize=(14, 4))

df['amount'].hist(bins=60, ax=axes[0])
axes[0].set_title('Transaction Amount Distribution')
axes[0].set_xlabel('Amount (₹)')

df.groupby('month')['amount'].sum().plot(kind='bar', ax=axes[1])
axes[1].set_title('Total Transaction Value by Month')
axes[1].set_xlabel('Month')
axes[1].set_ylabel('Total Value (₹)')

plt.tight_layout()
plt.show()
""")

# ---------------------------------------------------------------------------
md("""## 3. Rule-Based Audit Tests

Six classic audit analytics tests, each returning the transaction IDs it
flags and why:

- **Duplicates** — same vendor + amount + date appearing more than once
- **Round numbers** — suspiciously clean amounts (exact multiples of 10,000)
- **Off-hours / weekend postings** — entries outside normal business hours
- **Vendor concentration** — vendors representing >8% of total spend
- **Statistical outliers** — IQR-based outliers, computed per account category
- **Month-end spikes** — late-hour postings clustered in the last days of a month
""")
code("""from audit_tests import run_all_tests, benfords_law_check

rule_flags = run_all_tests(df)
print(f"Rule-based tests flagged {len(rule_flags)} unique transactions "
      f"out of {len(df)} total ({len(rule_flags)/len(df)*100:.1f}%)")
rule_flags.head(10)
""")

code("""test_counts = (
    rule_flags['tests_triggered']
    .str.split(', ')
    .explode()
    .value_counts()
)
test_counts.plot(kind='barh')
plt.title('Transactions Flagged per Rule Test')
plt.xlabel('Count')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
""")

# ---------------------------------------------------------------------------
md("""## 4. Benford's Law Analysis

Naturally occurring financial amounts tend to follow Benford's Law — lower
leading digits (1, 2) occur far more often than higher ones (8, 9). A large
deviation from the expected distribution, especially concentrated in one
account, can indicate manual entry, rounding, or manipulation rather than
organic transactions.""")
code("""benford_df = benfords_law_check(df)
benford_df[['account', 'n_transactions', 'max_deviation', 'flag']].sort_values('max_deviation', ascending=False)
""")

code("""# Visualize actual vs expected leading-digit distribution, overall
from collections import Counter

def leading_digit(x):
    s = str(abs(x)).lstrip('0').replace('.', '')
    return int(s[0]) if s else None

digits = df['amount'].apply(leading_digit)
actual_dist = digits.value_counts(normalize=True).sort_index()
expected_dist = pd.Series({d: np.log10(1 + 1/d) for d in range(1, 10)})

comparison = pd.DataFrame({'Actual': actual_dist, 'Expected (Benford)': expected_dist})
comparison.plot(kind='bar')
plt.title("Leading Digit Distribution: Actual vs Benford's Law")
plt.xlabel('Leading Digit')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()
""")

# ---------------------------------------------------------------------------
md("""## 5. ML Anomaly Detection — Isolation Forest

The rule-based tests above only catch what they're explicitly written to
catch. To find anomalies that don't match a predefined rule, an Isolation
Forest is trained on engineered features (amount, timing, vendor frequency,
vendor spend share, deviation from the account median) and assigns every
transaction an anomaly score.""")
code("""from anomaly_detection import run_isolation_forest, engineer_features

ml_scores = run_isolation_forest(df)
n_flagged = (ml_scores['ml_flag'] == 'anomaly').sum()
print(f"Isolation Forest flagged {n_flagged} / {len(ml_scores)} transactions "
      f"({n_flagged/len(ml_scores)*100:.1f}%)")
ml_scores.sort_values('ml_anomaly_score', ascending=False).head(10)
""")

code("""ml_scores['ml_anomaly_score'].hist(bins=50)
plt.title('Distribution of ML Anomaly Scores')
plt.xlabel('Anomaly Score (0 = normal, 1 = most anomalous)')
plt.ylabel('Transaction Count')
plt.show()
""")

# ---------------------------------------------------------------------------
md("""## 6. Combined Risk Scoring

Rule-based flags and the ML anomaly score are combined into one
`risk_score`. Rather than simply counting how many rule tests a transaction
triggered, the score uses the **maximum severity** among triggered tests —
a single strong signal (like an exact duplicate) shouldn't need a second,
weaker signal to register as high risk.

```
risk_score = 0.5 × max(rule test severity) + 0.5 × ML anomaly score
risk_level: High (>0.7)  |  Medium (0.4–0.7)  |  Low (<0.4)
```""")
code("""from risk_scoring import combine_scores, validate_against_ground_truth

risk_df = combine_scores(df, rule_flags, ml_scores)
risk_df['risk_level'].value_counts()
""")

code("""risk_df['risk_level'].value_counts().reindex(['Low', 'Medium', 'High']).plot(
    kind='bar', color=['#2ecc71', '#f39c12', '#e74c3c']
)
plt.title('Transaction Risk Level Distribution')
plt.ylabel('Count')
plt.xticks(rotation=0)
plt.show()
""")

code("""risk_df.sort_values('risk_score', ascending=False).head(10)[
    ['transaction_id', 'n_tests_triggered', 'tests_triggered', 'ml_anomaly_score', 'risk_score', 'risk_level']
]
""")

# ---------------------------------------------------------------------------
md("""## 7. Validation Against Ground Truth

Because the dataset was synthetically generated, the true anomaly labels
are known. This lets us measure recall (what % of planted anomalies the
pipeline actually caught) and precision (what % of flags were real) — a
step that's normally impossible on real unlabeled audit data, and the main
reason this project uses synthetic data in the first place.""")
code("""results = validate_against_ground_truth(risk_df)
""")

code("""gt = pd.read_csv('data/ground_truth.csv')
merged = risk_df.merge(gt, on='transaction_id', how='left')
merged['is_anomaly'] = merged['is_anomaly'].fillna(0).astype(int)

actual_anomalies = merged[merged['is_anomaly'] == 1]
recall_by_type = (
    actual_anomalies.groupby('anomaly_type')
    .apply(lambda g: (g['risk_level'].isin(['High', 'Medium'])).mean() * 100)
    .sort_values()
)

recall_by_type.plot(kind='barh', color='steelblue')
plt.title('Recall by Anomaly Type (% of planted anomalies caught)')
plt.xlabel('Recall (%)')
plt.axvline(x=recall_by_type.mean(), color='red', linestyle='--', label='Average')
plt.legend()
plt.tight_layout()
plt.show()
""")

md("""**Reading this chart:** duplicates, statistical outliers, and month-end
spikes are caught almost perfectly. Vendor concentration is the weakest
category — the 8%-of-total-spend threshold is conservative by design, and
would be tuned differently against a real client's risk appetite and vendor
base size. This kind of gap is worth calling out explicitly rather than
hiding — it shows the validation step is doing its job.""")

# ---------------------------------------------------------------------------
md("## 8. Key Findings Summary")
code("""full = risk_df.merge(df, on='transaction_id', how='left')

print("=== EXECUTIVE SUMMARY ===")
print(f"Total transactions analyzed: {len(full):,}")
print(f"Total transaction value:     ₹{full['amount'].sum():,.2f}")
print(f"High risk transactions:      {(full['risk_level']=='High').sum():,} "
      f"({(full['risk_level']=='High').mean()*100:.1f}%)")
print(f"Medium risk transactions:    {(full['risk_level']=='Medium').sum():,} "
      f"({(full['risk_level']=='Medium').mean()*100:.1f}%)")

print("\\nTop 5 vendors by flagged transaction value:")
top_vendors = (
    full[full['risk_level'].isin(['High', 'Medium'])]
    .groupby('vendor')['amount'].sum()
    .sort_values(ascending=False)
    .head(5)
)
print(top_vendors)
""")

code("""top_vendors.plot(kind='barh', color='darkred')
plt.title('Top 5 Vendors by Flagged Transaction Value')
plt.xlabel('Flagged Value (₹)')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
""")

md("""## Next steps

- Export `risk_df` to `data/dashboard_export.csv` for Power BI / Tableau
  (already produced by `run_pipeline.py`)
- See `reports/audit_findings_report.md` for the full write-up in audit
  report format
- See `sql/audit_tests.sql` for the same tests written directly in SQL

Full pipeline (script form): `python run_pipeline.py`
""")

nb['cells'] = cells
nbf.write(nb, 'auditlens_walkthrough.ipynb')
print("Notebook written.")
