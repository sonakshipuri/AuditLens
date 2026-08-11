# AuditLens -- Audit Analytics Findings Report

**Generated:** 2026-08-11
**Scope:** Full-year journal entries, 8,140 transactions, total value ₹337,178,531.87

## 1. Executive Summary

A combined rule-based and machine-learning audit analytics pipeline was run across 8,140 journal entries. **50 transactions (0.6%)** were classified as **High risk** and **561 (6.9%)** as **Medium risk**, and are recommended for manual review. The remaining 7,529 transactions were classified as **Low risk** and were not prioritized for manual review by the current screening framework (this reflects the screening thresholds used, not a confirmation that those transactions are clean).

## 2. Validation Against Synthetic Ground Truth

The framework detected **76.4% of planted anomalies** and achieved **17.5% precision** when High and Medium risk transactions were treated as the review population. These results evaluate screening performance on the synthetic validation set and should not be interpreted as fraud-detection accuracy.

## 3. Methodology

Two complementary detection approaches were combined into a single risk score:

- **Rule-based audit tests**: duplicate transactions, round-number amounts, off-hours/weekend postings, vendor spend concentration, statistical (IQR) outliers per account, and month-end late-hour postings (entries posted on/after day 28 of the month, at/after 18:00 -- a fixed date/time rule, not a comparison against a volume baseline).
- **Machine learning**: an Isolation Forest model trained on engineered features (amount, timing, vendor frequency, vendor spend share, and deviation from account median) to catch anomalies that do not match a predefined rule. Its output (`ml_anomaly_score`) is a normalized 0-1 relative anomaly score, not a probability of fraud.

Each transaction's final `risk_score` (0-1) is a weighted combination of the highest-severity rule triggered and the normalized ML anomaly score, bucketed into Low / Medium / High.

## 4. Benford's Law Analysis

Leading-digit distribution of transaction amounts was compared against Benford's Law expected frequencies, by account category, as a population-level screening technique. This is a simple maximum-absolute-deviation screen, not a formal chi-square goodness-of-fit test. Accounts with a maximum deviation above 0.08 are flagged below. A deviation from the expected distribution may warrant further investigation, but does not by itself indicate fraud or manipulation:

| account             |   n_transactions |   max_deviation | flag   |
|:--------------------|-----------------:|----------------:|:-------|
| Accounts Receivable |              829 |           0.226 | REVIEW |
| Travel & Expense    |              804 |           0.221 | REVIEW |
| Utilities           |              841 |           0.217 | REVIEW |
| Marketing Spend     |              790 |           0.213 | REVIEW |
| Accounts Payable    |              817 |           0.197 | REVIEW |
| Office Supplies     |              775 |           0.179 | REVIEW |
| Payroll             |              856 |           0.177 | REVIEW |
| Rent                |              799 |           0.163 | REVIEW |
| Inventory           |              812 |           0.161 | REVIEW |
| Consulting Fees     |              817 |           0.11  | REVIEW |

## 5. Top 5 Vendors by Flagged Transaction Value

| vendor                        |   flagged_transactions |   flagged_value |
|:------------------------------|-----------------------:|----------------:|
| Morales-Jones                 |                     29 |     3.46698e+06 |
| Snyder, Campos and Callahan   |                     28 |     2.84192e+06 |
| Mcclain, Miller and Henderson |                     13 |     2.71385e+06 |
| Doyle Ltd                     |                     21 |     2.33556e+06 |
| Dudley Group                  |                     23 |     2.22902e+06 |

## 6. Top 10 Highest-Risk Transactions

| transaction_id   | date       | vendor                      | account             |   amount |   risk_score | risk_level   | reasons                                                                                                                                        |
|:-----------------|:-----------|:----------------------------|:--------------------|---------:|-------------:|:-------------|:-----------------------------------------------------------------------------------------------------------------------------------------------|
| JE108117         | 2025-06-28 | Perez Inc                   | Accounts Receivable |   288844 |       0.9    | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Accounts Receivable' (IQR method) | Month-end late-hour posting |
| JE108130         | 2025-09-28 | Snyder, Campos and Callahan | Accounts Receivable |   143439 |       0.8823 | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Accounts Receivable' (IQR method) | Month-end late-hour posting |
| JE108106         | 2025-03-30 | James Group                 | Accounts Receivable |   209131 |       0.8656 | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Accounts Receivable' (IQR method) | Month-end late-hour posting |
| JE108102         | 2025-03-29 | Perez Inc                   | Accounts Payable    |   247912 |       0.862  | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Accounts Payable' (IQR method) | Month-end late-hour posting    |
| JE108127         | 2025-09-28 | James Group                 | Office Supplies     |   206094 |       0.848  | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Office Supplies' (IQR method) | Month-end late-hour posting     |
| JE108054         | 2025-11-17 | QuickPay Consulting Ltd     | Consulting Fees     |   427044 |       0.8239 | High         | Statistical outlier for account 'Consulting Fees' (IQR method)                                                                                 |
| JE108068         | 2025-07-21 | QuickPay Consulting Ltd     | Consulting Fees     |   265230 |       0.8214 | High         | Statistical outlier for account 'Consulting Fees' (IQR method)                                                                                 |
| JE108055         | 2025-12-01 | QuickPay Consulting Ltd     | Consulting Fees     |   201318 |       0.8205 | High         | Statistical outlier for account 'Consulting Fees' (IQR method)                                                                                 |
| JE108112         | 2025-06-28 | Ferrell, Rice and Maddox    | Utilities           |   152391 |       0.8164 | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Utilities' (IQR method) | Month-end late-hour posting           |
| JE108115         | 2025-06-30 | Blair PLC                   | Office Supplies     |   325064 |       0.816  | High         | Posted on weekend or outside business hours | Statistical outlier for account 'Office Supplies' (IQR method) | Month-end late-hour posting     |

## 7. Recommendations

- Prioritize manual review of the **High risk** transaction population first, given limited audit hours.
- Follow up directly with vendors flagged under **vendor concentration** to confirm legitimacy of the relationship and check for related-party indicators.
- Use **Benford's Law** deviations as a supplementary population-level diagnostic, and combine them with transaction-level evidence before initiating further investigation, rather than treating a deviation alone as evidence of an issue.
- Recalibrate the vendor-concentration threshold (currently a fixed 8% of total spend): validation testing showed this test caught only **22.9%** of planted vendor-concentration anomalies, the lowest of all rule-based tests. As a fixed proof-of-concept parameter it would need tuning against a real client's vendor distribution, materiality thresholds, and historical risk patterns.

## 8. Known Limitations

- This analysis is a proof-of-concept run on synthetic data with known injected anomalies; thresholds (contamination rate, concentration %, IQR multiplier) would need tuning against real client risk appetite and historical fraud patterns.
- Duplicate detection uses exact vendor+amount+date matches; near-duplicates (off by a few rupees, or split into two entries) would require fuzzy matching.
- The month-end late-hour posting test is a fixed date/time rule (day >= 28, hour >= 18), not a comparison against a historical volume baseline -- it does not detect an actual spike in posting volume.
- In this run, **every account population exceeded the Benford deviation threshold** (all flagged `REVIEW`), which limits the test's discriminatory value here -- it isn't distinguishing higher-risk accounts from lower-risk ones. In production this would call for population-suitability checks and a calibrated statistical threshold rather than a fixed 0.08 cutoff.
- The ML model is unsupervised and re-trained fresh each run; in production it would benefit from feedback loops based on which flagged transactions auditors confirm vs. dismiss.
