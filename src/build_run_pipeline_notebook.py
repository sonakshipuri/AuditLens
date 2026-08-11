"""
Builds run_pipeline.ipynb — the actual pipeline (same steps as
run_pipeline.py) in notebook form, so it can be run cell-by-cell.
Run once with: python build_run_pipeline_notebook.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

# ---------------------------------------------------------------------------
md("""# AuditLens — Run Pipeline

Notebook version of `run_pipeline.py`. Running all cells top to bottom
regenerates every output file the project produces:

- `data/journal_entries.csv`, `data/ground_truth.csv`
- `data/auditlens.db` (SQLite)
- `data/rule_based_flags.csv`, `data/benford_analysis.csv`
- `data/ml_anomaly_scores.csv`
- `data/final_risk_scores.csv`, `data/dashboard_export.csv`
- `reports/audit_findings_report.md`

This is the same logic as `run_pipeline.py` — use this notebook when you
want to run/inspect the pipeline interactively, and the `.py` script when
you just want to regenerate everything from the command line.
""")

# ---------------------------------------------------------------------------
md("## Setup")
code("""import os
import sys

sys.path.insert(0, os.path.abspath('src'))

BASE_DIR = os.path.abspath('.')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'reports'), exist_ok=True)
""")

# ---------------------------------------------------------------------------
md("## Step 1/7 — Generate synthetic journal entries\n\nSkips automatically if `data/journal_entries.csv` already exists. Delete it first if you want to regenerate with different random data.")
code("""csv_path = os.path.join(DATA_DIR, 'journal_entries.csv')

if not os.path.exists(csv_path):
    print('Generating synthetic journal entries...')
    import generate_data  # runs on import
else:
    print('journal_entries.csv already exists, skipping generation.')
    print('(delete data/journal_entries.csv to regenerate)')
""")

# ---------------------------------------------------------------------------
md("## Step 2/7 — Ingest, clean, profile, load to SQLite")
code("""from ingestion import load_raw_csv, clean, load_to_sqlite, profile

raw = load_raw_csv()
df = clean(raw)
profile(df)
load_to_sqlite(df)
""")

# ---------------------------------------------------------------------------
md("## Step 3/7 — Rule-based audit tests + Benford's Law")
code("""from audit_tests import run_all_tests, benfords_law_check

rule_flags = run_all_tests(df)
rule_flags.to_csv(os.path.join(DATA_DIR, 'rule_based_flags.csv'), index=False)

benford_df = benfords_law_check(df)
benford_df.to_csv(os.path.join(DATA_DIR, 'benford_analysis.csv'), index=False)

print(f"Flagged {len(rule_flags)} transactions across all rule tests")
rule_flags.head()
""")

# ---------------------------------------------------------------------------
md("## Step 4/7 — ML anomaly detection (Isolation Forest)")
code("""from anomaly_detection import run_isolation_forest

ml_scores = run_isolation_forest(df)
ml_scores.to_csv(os.path.join(DATA_DIR, 'ml_anomaly_scores.csv'), index=False)

n_ml_flagged = (ml_scores['ml_flag'] == 'anomaly').sum()
print(f"Flagged {n_ml_flagged} transactions via ML")
ml_scores.sort_values('ml_anomaly_score', ascending=False).head()
""")

# ---------------------------------------------------------------------------
md("## Step 5/7 — Combine into final risk scores")
code("""from risk_scoring import combine_scores, validate_against_ground_truth

risk_df = combine_scores(df, rule_flags, ml_scores)
risk_df.to_csv(os.path.join(DATA_DIR, 'final_risk_scores.csv'), index=False)

print(risk_df['risk_level'].value_counts().to_string())
risk_df.head()
""")

# ---------------------------------------------------------------------------
md("## Step 6/7 — Validate against planted ground truth\n\n(Synthetic-data-only step — a real client dataset wouldn't have this.)")
code("""validation_results = validate_against_ground_truth(risk_df)
""")

# ---------------------------------------------------------------------------
md("## Step 7/7 — Generate audit findings report + dashboard export")
code("""from generate_report import generate_report

report_path = generate_report()

# Dashboard-ready export: one flat table with everything Power BI/Streamlit needs
dashboard_export = risk_df.merge(df, on='transaction_id', how='left')
dashboard_path = os.path.join(DATA_DIR, 'dashboard_export.csv')
dashboard_export.to_csv(dashboard_path, index=False)

print('Pipeline complete.')
print(f'  Report:            reports/audit_findings_report.md')
print(f'  Dashboard export:  data/dashboard_export.csv')
print(f'  Risk scores:       data/final_risk_scores.csv')
print(f'  SQLite DB:         data/auditlens.db')
""")

md("""### Preview the generated report""")
code("""with open(report_path) as f:
    print(f.read()[:2000])
""")

nb['cells'] = cells
nbf.write(nb, 'run_pipeline.ipynb')
print("Notebook written.")
