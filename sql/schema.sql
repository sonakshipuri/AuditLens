-- schema.sql
-- Table structure for the AuditLens journal entries table.
-- Matches the columns produced by src/ingestion.py when loaded into SQLite.

CREATE TABLE IF NOT EXISTS journal_entries (
    transaction_id   TEXT PRIMARY KEY,
    date              DATE,
    time              TEXT,
    department        TEXT,
    account           TEXT,
    vendor            TEXT,
    amount            REAL,
    entry_type        TEXT,      -- 'Debit' or 'Credit'
    posted_by         TEXT,
    description       TEXT,
    day_of_week       TEXT,
    is_weekend        BOOLEAN,
    hour              INTEGER,
    month             INTEGER,
    day               INTEGER
);

CREATE INDEX IF NOT EXISTS idx_vendor ON journal_entries(vendor);
CREATE INDEX IF NOT EXISTS idx_account ON journal_entries(account);
CREATE INDEX IF NOT EXISTS idx_date ON journal_entries(date);
