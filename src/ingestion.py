"""
ingestion.py
------------
Loads raw journal entry data (CSV or SQL table) and pushes it into a local
SQLite database (data/auditlens.db) so downstream SQL audit tests can run
against it. Also runs basic profiling.
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "auditlens.db")
CSV_PATH = os.path.join(DATA_DIR, "journal_entries.csv")


def load_raw_csv(path=CSV_PATH):
    df = pd.read_csv(path)
    return df


def clean(df):
    """Basic cleaning: types, dedupe exact rows, parse datetime."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["day_of_week"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.weekday >= 5
    df["hour"] = pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce").dt.hour
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day

    before = len(df)
    df = df.dropna(subset=["transaction_id", "date", "amount"])
    df = df.drop_duplicates()
    after = len(df)
    print(f"Cleaning: {before} -> {after} rows ({before - after} dropped for nulls/exact dupes)")
    return df


def load_to_sqlite(df, db_path=DB_PATH, table_name="journal_entries"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    print(f"Loaded {len(df)} rows into {db_path} (table: {table_name})")


def profile(df):
    print("\n--- DATA PROFILE ---")
    print(f"Rows: {len(df)}   Columns: {len(df.columns)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Distinct vendors: {df['vendor'].nunique()}")
    print(f"Distinct departments: {df['department'].nunique()}")
    print(f"Amount summary:\n{df['amount'].describe()}")
    print(f"Missing values per column:\n{df.isna().sum()}")


if __name__ == "__main__":
    raw = load_raw_csv()
    cleaned = clean(raw)
    profile(cleaned)
    load_to_sqlite(cleaned)
