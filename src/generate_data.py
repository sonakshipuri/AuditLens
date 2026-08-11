"""
generate_data.py
-----------------
Generates a synthetic general ledger / journal entries dataset that mimics
a real client's transaction data, with deliberately injected anomalies so
detection performance can be measured against ground truth.

Output: data/journal_entries.csv  (clean columns, no ground-truth leakage)
         data/ground_truth.csv     (transaction_id -> is_anomaly, anomaly_type)
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
N_NORMAL_TRANSACTIONS = 8000
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 12, 31)

DEPARTMENTS = ["Procurement", "Sales", "HR", "IT", "Marketing", "Finance", "Operations"]
ACCOUNTS = [
    "Accounts Payable", "Accounts Receivable", "Travel & Expense",
    "Office Supplies", "Consulting Fees", "Payroll", "Rent",
    "Utilities", "Inventory", "Marketing Spend",
]
ENTRY_TYPES = ["Debit", "Credit"]

# A small, realistic vendor pool (normal spend is spread across these)
VENDORS = [fake.company() for _ in range(40)]

# Employees who post entries
POSTERS = [fake.name() for _ in range(25)]


def random_business_datetime(start, end):
    """Random datetime, biased toward normal business hours on weekdays."""
    delta_days = (end - start).days
    d = start + timedelta(days=random.randint(0, delta_days))
    # push to a weekday
    while d.weekday() >= 5:
        d += timedelta(days=1)
    hour = random.choices(
        population=range(24),
        weights=[1] * 8 + [10] * 9 + [1] * 7,  # heavy weight on 8am-5pm
        k=1,
    )[0]
    minute = random.randint(0, 59)
    return d.replace(hour=hour, minute=minute, second=random.randint(0, 59))


def normal_amount(account):
    """
    Amount drawn from a realistic lognormal distribution per account type.
    sigma=0.5 keeps per-account IQR fences and the ML feature distribution
    well-calibrated against the injected anomaly multipliers in this file.

    Note: a wider-tail version of this function (rare large legit
    transactions, to give Benford's Law a naturally wider spread) was
    tested and rejected -- it degraded recall and precision on every other
    rule test by 10-15 points because they all read the same amount column.
    See README known limitations for why Benford is left as a documented
    gap rather than "fixed" here.
    """
    base = {
        "Payroll": 45000,
        "Rent": 120000,
        "Consulting Fees": 60000,
        "Inventory": 35000,
    }.get(account, 15000)
    amt = np.random.lognormal(mean=np.log(base), sigma=0.5)
    return round(float(amt), 2)


# ---------------------------------------------------------------------------
# 1. GENERATE NORMAL (CLEAN) TRANSACTIONS
# ---------------------------------------------------------------------------
rows = []
tx_id = 100000

for _ in range(N_NORMAL_TRANSACTIONS):
    tx_id += 1
    dt = random_business_datetime(START_DATE, END_DATE)
    account = random.choice(ACCOUNTS)
    row = {
        "transaction_id": f"JE{tx_id}",
        "date": dt.date().isoformat(),
        "time": dt.time().strftime("%H:%M:%S"),
        "department": random.choice(DEPARTMENTS),
        "account": account,
        "vendor": random.choice(VENDORS),
        "amount": normal_amount(account),
        "entry_type": random.choice(ENTRY_TYPES),
        "posted_by": random.choice(POSTERS),
        "description": fake.bs().capitalize(),
    }
    rows.append(row)

df = pd.DataFrame(rows)
ground_truth = {r["transaction_id"]: {"is_anomaly": 0, "anomaly_type": "none"} for r in rows}

# ---------------------------------------------------------------------------
# 2. INJECT ANOMALIES (each labeled in ground_truth for later validation)
# ---------------------------------------------------------------------------

def next_id():
    global tx_id
    tx_id += 1
    return f"JE{tx_id}"


injected_rows = []

# --- a) Duplicate transactions (same vendor + amount + date, posted twice) ---
dup_sources = df.sample(15, random_state=1).to_dict("records")
for src in dup_sources:
    new = src.copy()
    new["transaction_id"] = next_id()
    injected_rows.append(new)
    ground_truth[new["transaction_id"]] = {"is_anomaly": 1, "anomaly_type": "duplicate"}

# --- b) Round-number transactions (suspiciously clean amounts) ---
for _ in range(20):
    dt = random_business_datetime(START_DATE, END_DATE)
    account = random.choice(ACCOUNTS)
    new_id = next_id()
    injected_rows.append({
        "transaction_id": new_id,
        "date": dt.date().isoformat(),
        "time": dt.time().strftime("%H:%M:%S"),
        "department": random.choice(DEPARTMENTS),
        "account": account,
        "vendor": random.choice(VENDORS),
        "amount": float(random.choice([50000, 100000, 200000, 250000, 500000])),
        "entry_type": random.choice(ENTRY_TYPES),
        "posted_by": random.choice(POSTERS),
        "description": "Manual adjustment entry",
    })
    ground_truth[new_id] = {"is_anomaly": 1, "anomaly_type": "round_number"}

# --- c) Weekend / after-hours postings ---
for _ in range(18):
    # force a Saturday or Sunday, or a very late/early hour
    d = START_DATE + timedelta(days=random.randint(0, (END_DATE - START_DATE).days))
    if random.random() < 0.5:
        while d.weekday() < 5:
            d += timedelta(days=1)
        hour = random.randint(9, 17)
    else:
        hour = random.choice([1, 2, 3, 23])
    new_id = next_id()
    injected_rows.append({
        "transaction_id": new_id,
        "date": d.date().isoformat(),
        "time": f"{hour:02d}:{random.randint(0,59):02d}:00",
        "department": random.choice(DEPARTMENTS),
        "account": random.choice(ACCOUNTS),
        "vendor": random.choice(VENDORS),
        "amount": normal_amount("Consulting Fees"),
        "entry_type": random.choice(ENTRY_TYPES),
        "posted_by": random.choice(POSTERS),
        "description": "Off-hours entry",
    })
    ground_truth[new_id] = {"is_anomaly": 1, "anomaly_type": "off_hours_weekend"}

# --- d) Vendor concentration spike (one shell-like vendor gets abnormal volume) ---
shell_vendor = "QuickPay Consulting Ltd"
for _ in range(35):
    dt = random_business_datetime(START_DATE, END_DATE)
    new_id = next_id()
    injected_rows.append({
        "transaction_id": new_id,
        "date": dt.date().isoformat(),
        "time": dt.time().strftime("%H:%M:%S"),
        "department": "Procurement",
        "account": "Consulting Fees",
        "vendor": shell_vendor,
        "amount": normal_amount("Consulting Fees") * random.uniform(1.2, 2.5),
        "entry_type": "Debit",
        "posted_by": random.choice(POSTERS),
        "description": "Advisory services",
    })
    ground_truth[new_id] = {"is_anomaly": 1, "anomaly_type": "vendor_concentration"}

# --- e) Statistical outliers (amount far beyond normal range for account) ---
for _ in range(12):
    dt = random_business_datetime(START_DATE, END_DATE)
    account = random.choice(ACCOUNTS)
    new_id = next_id()
    injected_rows.append({
        "transaction_id": new_id,
        "date": dt.date().isoformat(),
        "time": dt.time().strftime("%H:%M:%S"),
        "department": random.choice(DEPARTMENTS),
        "account": account,
        "vendor": random.choice(VENDORS),
        "amount": normal_amount(account) * random.uniform(8, 15),
        "entry_type": random.choice(ENTRY_TYPES),
        "posted_by": random.choice(POSTERS),
        "description": "Urgent one-off payment",
    })
    ground_truth[new_id] = {"is_anomaly": 1, "anomaly_type": "statistical_outlier"}

# --- f) Month-end spike cluster (last 2 days of a few months, unusual volume) ---
for month in [3, 6, 9, 12]:
    for _ in range(10):
        day = random.choice([28, 29, 30, 31])
        try:
            d = datetime(2025, month, day)
        except ValueError:
            d = datetime(2025, month, 28)
        new_id = next_id()
        injected_rows.append({
            "transaction_id": new_id,
            "date": d.date().isoformat(),
            "time": f"{random.randint(18,23):02d}:{random.randint(0,59):02d}:00",
            "department": "Finance",
            "account": random.choice(ACCOUNTS),
            "vendor": random.choice(VENDORS),
            "amount": normal_amount("Consulting Fees") * random.uniform(1.5, 3),
            "entry_type": "Debit",
            "posted_by": random.choice(POSTERS),
            "description": "Period-end adjustment",
        })
        ground_truth[new_id] = {"is_anomaly": 1, "anomaly_type": "month_end_spike"}

# ---------------------------------------------------------------------------
# 3. COMBINE, SHUFFLE, SAVE
# ---------------------------------------------------------------------------
full_df = pd.concat([df, pd.DataFrame(injected_rows)], ignore_index=True)
full_df = full_df.sample(frac=1, random_state=7).reset_index(drop=True)

gt_df = pd.DataFrame(
    [{"transaction_id": k, **v} for k, v in ground_truth.items()]
)

full_df.to_csv(os.path.join(DATA_DIR, "journal_entries.csv"), index=False)
gt_df.to_csv(os.path.join(DATA_DIR, "ground_truth.csv"), index=False)

print(f"Generated {len(full_df)} total transactions")
print(f"  Normal:   {N_NORMAL_TRANSACTIONS}")
print(f"  Injected anomalies: {len(injected_rows)}")
print(f"Saved to {DATA_DIR}/journal_entries.csv and ground_truth.csv")