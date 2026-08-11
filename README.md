# AuditLens : Automated Audit Analytics & Anomaly Detection

A rule-based + machine-learning pipeline that flags high-risk transactions in
journal entry / general ledger data, built to mirror the kind of analytics
work an Audit & Assurance Data & Analytics associate would actually do:
clean transactional data, run audit tests, score risk, validate the screening
logic, and communicate findings, not just train a model in a notebook.

## Why this project exists

Most "fraud detection" student projects stop at an ML model and an AUC score.
AuditLens is built the other way around: it starts from audit testing
techniques (duplicate detection, Benford's Law, vendor concentration,
statistical outliers) and adds machine learning as a *complementary* layer.

The complete pipeline is then validated against known planted anomalies and
used to generate an audit findings report, making the output useful for
**risk prioritization and investigation**, rather than claiming that an
anomalous transaction is automatically fraudulent.

## Architecture

```text
Synthetic journal entries (CSV)
            │
            ▼
   Ingestion & Cleaning (pandas)
            │
            ▼
      SQLite database  ──────────────► SQL audit tests (sql/audit_tests.sql)
            │
            ▼
   Rule-Based Audit Test Engine (src/audit_tests.py)
   • Duplicates                    • Vendor concentration
   • Round numbers                 • Statistical outliers (IQR)
   • Off-hours/weekend             • Month-end late-hour postings
   • Benford's Law digit analysis  (max-deviation screen)
            │
            ▼
   ML Anomaly Detection, Isolation Forest (src/anomaly_detection.py)
   (normalized 0-1 relative anomaly score, not a probability of fraud)
            │
            ▼
   Risk Scoring & Consolidation (src/risk_scoring.py)
   risk_score = 0.5 × rule severity + 0.5 × ML anomaly score
   → Low / Medium / High risk level
            │
            ▼
   Validation against planted ground truth (recall / precision)
            │
     ┌──────┴──────┐
     ▼             ▼
 Power BI      Audit Findings Report
 Dashboard      (reports/audit_findings_report.md)
```

## Results (on the included synthetic dataset)

- **8,140** journal entries processed, with **140** anomalies deliberately
  planted across 6 categories: duplicates, round numbers, off-hours
  postings, vendor concentration, statistical outliers, and month-end
  late-hour postings.
- **50 (0.6%)** transactions were classified as High risk and **561 (6.9%)**
  as Medium risk.
- **611 (7.5%)** transactions were prioritized for manual review as
  High/Medium risk.
- The remaining **7,529 (92.5%)** transactions were classified as Low risk
  under the current screening thresholds. Low risk means *not prioritized by
  the framework*, it does not mean confirmed clean.
- **76.4% recall / 17.5% precision** against the planted anomalies when the
  High + Medium population is treated as the review population.
- Recall by anomaly type:
  - **100.0%**, duplicate transactions
  - **100.0%**, statistical outliers
  - **100.0%**, month-end late-hour postings
  - **95.0%**, round-number amounts
  - **72.2%**, off-hours/weekend postings
  - **22.9%**, vendor concentration

The pipeline is intentionally designed as a broad **risk-screening tool**:
cast a useful net for an auditor to review rather than act as a precise
fraud classifier.

These metrics are measured against **synthetic planted anomalies** and should
not be interpreted as real-world fraud-detection accuracy.

The weakest rule-based category is **vendor concentration (22.9% recall)**.
The current 8%-of-total-spend threshold is a fixed proof-of-concept parameter
and would need calibration against a real client's vendor distribution,
materiality thresholds, and historical risk patterns.

These numbers exist because the anomalies are synthetically labeled, the
point is that the pipeline can be evaluated against known ground truth rather
than simply assuming that its flags are correct.

## Project structure

```text
auditlens/
│
├── data/                        # generated at runtime, not checked in
│   ├── journal_entries.csv      # synthetic transactions
│   ├── ground_truth.csv         # planted anomaly labels (validation only)
│   ├── auditlens.db             # SQLite database
│   ├── rule_based_flags.csv
│   ├── ml_anomaly_scores.csv
│   ├── benford_analysis.csv
│   ├── final_risk_scores.csv
│   └── dashboard_export.csv     # import this into Power BI / Tableau
│
├── sql/
│   ├── schema.sql               # table definition
│   └── audit_tests.sql          # SQL versions of the audit tests
│
├── src/
│   ├── generate_data.py         # synthetic data + anomaly injection
│   ├── ingestion.py             # load, clean, profile, push to SQLite
│   ├── audit_tests.py            # rule-based audit test engine
│   ├── anomaly_detection.py      # Isolation Forest ML layer
│   ├── risk_scoring.py           # combine scores + validate vs ground truth
│   └── generate_report.py        # writes reports/audit_findings_report.md
│
├── dashboard/
│   ├── README.md                 # Power BI build instructions
│   └── streamlit_app.py          # code-based dashboard alternative
│
├── reports/
│   └── audit_findings_report.md  # generated findings report
│
├── auditlens_walkthrough.ipynb   # entire pipeline, narrated, with inline charts
├── requirements.txt
└── README.md
```

## How to run

**`auditlens_walkthrough.ipynb`** is the single end-to-end entry point,
step-by-step pipeline cells with inline charts and explanations (Benford's
Law analysis, risk distribution, recall by anomaly type, and validation
results). Run it top to bottom to regenerate the project's output files.

```bash
pip install -r requirements.txt
jupyter notebook auditlens_walkthrough.ipynb   # then Run All
```

This produces:

- `reports/audit_findings_report.md`, the audit findings write-up
- `data/dashboard_export.csv`, ready to import into Power BI / Tableau
- `data/final_risk_scores.csv`, every transaction with its risk score
- `data/auditlens.db`, the SQLite database

To explore individual stages instead, each module also runs standalone:

```bash
python src/generate_data.py        # regenerate synthetic data
python src/ingestion.py            # clean + load + profile
python src/audit_tests.py          # rule-based tests only
python src/anomaly_detection.py    # ML layer only
python src/risk_scoring.py         # combine + validate
python src/generate_report.py      # report only (needs prior steps run)
```

Or query directly:

```bash
sqlite3 data/auditlens.db < sql/audit_tests.sql
```

## Tech stack

Python (pandas, scikit-learn, Faker) · SQL (SQLite) · Power BI · Streamlit ·
statistics (IQR, Benford's Law) · Plotly

## About the dataset

The dataset is **synthetically generated** (see `src/generate_data.py`),
not scraped or sourced from a real company. This was a deliberate choice:
it means the schema can be designed around a realistic journal-entry
structure and, more importantly, every planted anomaly can be labeled with
ground truth.

That makes it possible to measure detection performance using recall and
precision rather than assuming that the detected flags are correct.

In a real audit engagement, the same analytics workflow could run against
authorized client ERP / general-ledger exports, but the planted ground-truth
validation step would not be available.

## Audit findings report

The pipeline generates:

`reports/audit_findings_report.md`

The report is designed as a manager-facing audit analytics deliverable and
contains:

- Executive summary
- Validation against synthetic ground truth
- Methodology
- Benford's Law analysis
- Top vendors by flagged transaction value
- Top 10 highest-risk transactions
- Recommendations
- Known limitations

The report explicitly distinguishes between **transactions requiring review**
and **confirmed fraud or control failures**.

## Known limitations

- **Duplicate detection** is exact-match only (vendor + amount + date);
  near-duplicates would require fuzzy matching.
- **Month-end late-hour posting** is a fixed date/time rule (day ≥ 28,
  hour ≥ 18), not a comparison against a historical volume baseline, it
  does not detect an actual spike in posting volume.
- **Benford's Law** is a simple maximum-absolute-deviation screen, not a
  formal chi-square goodness-of-fit test, and a deviation alone does not
  indicate manipulation. On the included dataset every account currently
  crosses the review threshold, which limits how much it discriminates
  between accounts here.
- **Vendor concentration** (8% of total spend) is a fixed proof-of-concept
  threshold with the lowest recall (22.9%) of the rule-based tests; it would
  need calibration against real client data.
- The **ML anomaly score** is a normalized, relative 0–1 score from an
  Isolation Forest run, not a probability of fraud and not directly
  comparable across different runs or datasets.
- The project uses **synthetic data**, so the validation metrics demonstrate
  pipeline performance on the planted test cases rather than production
  fraud-detection performance.

## Key takeaway

AuditLens is not designed to say:

> "This transaction is fraudulent."

It is designed to answer:

> **"Which transactions should an auditor investigate first, and why?"**

The project combines **audit testing, SQL, statistical analysis, machine
learning, risk scoring, visualization, validation, and business reporting**
into one end-to-end workflow.
