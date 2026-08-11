-- audit_tests.sql
-- Standalone SQL versions of the core audit tests. These demonstrate the
-- same logic as src/audit_tests.py, written directly in SQL -- useful for
-- showing SQL proficiency independent of the Python pipeline, and for
-- running quick ad-hoc checks directly against the database.

-- 1. DUPLICATE TRANSACTIONS
-- Same vendor + amount + date appearing more than once
SELECT vendor, amount, date, COUNT(*) AS occurrences,
       GROUP_CONCAT(transaction_id) AS transaction_ids
FROM journal_entries
GROUP BY vendor, amount, date
HAVING COUNT(*) > 1
ORDER BY occurrences DESC;


-- 2. ROUND-NUMBER TRANSACTIONS
-- Amounts that are suspiciously clean multiples of 10,000
SELECT transaction_id, date, vendor, account, amount
FROM journal_entries
WHERE amount >= 10000
  AND amount % 10000 = 0
ORDER BY amount DESC;


-- 3. OFF-HOURS / WEEKEND POSTINGS
SELECT transaction_id, date, day_of_week, hour, vendor, amount, posted_by
FROM journal_entries
WHERE is_weekend = 1
   OR hour < 7
   OR hour > 20
ORDER BY date;


-- 4. VENDOR CONCENTRATION
-- Vendors whose total spend exceeds 8% of overall spend
WITH vendor_totals AS (
    SELECT vendor, SUM(amount) AS vendor_spend
    FROM journal_entries
    GROUP BY vendor
),
grand_total AS (
    SELECT SUM(amount) AS total_spend FROM journal_entries
)
SELECT v.vendor,
       v.vendor_spend,
       ROUND(100.0 * v.vendor_spend / g.total_spend, 2) AS pct_of_total_spend
FROM vendor_totals v, grand_total g
WHERE (v.vendor_spend / g.total_spend) > 0.08
ORDER BY pct_of_total_spend DESC;


-- 5. STATISTICAL OUTLIERS PER ACCOUNT (simplified IQR-style using percentiles)
-- SQLite has no native PERCENTILE function, so this uses a window-function
-- approximation. For production use, prefer the Python IQR implementation
-- in src/audit_tests.py which is exact.
WITH ranked AS (
    SELECT transaction_id, account, amount,
           NTILE(4) OVER (PARTITION BY account ORDER BY amount) AS quartile
    FROM journal_entries
),
account_stats AS (
    SELECT account,
           MAX(CASE WHEN quartile = 1 THEN amount END) AS q1_max,
           MIN(CASE WHEN quartile = 4 THEN amount END) AS q4_min
    FROM ranked
    GROUP BY account
)
SELECT j.transaction_id, j.account, j.amount
FROM journal_entries j
JOIN account_stats s ON j.account = s.account
WHERE j.amount > s.q4_min * 1.5  -- rough outlier threshold
ORDER BY j.amount DESC;


-- 6. MONTH-END LATE-HOUR POSTINGS
SELECT transaction_id, date, day, hour, department, vendor, amount
FROM journal_entries
WHERE day >= 28
  AND hour >= 18
ORDER BY date;


-- 7. SUMMARY: TRANSACTION VOLUME AND VALUE BY MONTH (for the dashboard)
SELECT month,
       COUNT(*) AS transaction_count,
       ROUND(SUM(amount), 2) AS total_value,
       ROUND(AVG(amount), 2) AS avg_value
FROM journal_entries
GROUP BY month
ORDER BY month;


-- 8. SUMMARY: TOP 10 VENDORS BY SPEND
SELECT vendor,
       COUNT(*) AS transaction_count,
       ROUND(SUM(amount), 2) AS total_spend
FROM journal_entries
GROUP BY vendor
ORDER BY total_spend DESC
LIMIT 10;
