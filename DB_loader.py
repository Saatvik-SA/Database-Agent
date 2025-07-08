# db_loader.py

import sqlite3
import pandas as pd
import os

def connect_to_sqlite(db_path: str):
    """Connect to a local .db or .sqlite file."""
    return sqlite3.connect(db_path)

def load_csv_as_sqlite(csv_path: str):
    """Convert a single CSV file to an in-memory SQLite DB."""
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(":memory:")
    df.to_sql("uploaded_csv", conn, index=False, if_exists='replace')
    return conn

def load_excel_as_sqlite(xlsx_path: str):
    """Convert all sheets from Excel to in-memory SQLite DB."""
    xls = pd.ExcelFile(xlsx_path)
    conn = sqlite3.connect(":memory:")

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        clean_name = sheet_name.strip().replace(" ", "_").lower()
        df.to_sql(clean_name, conn, index=False, if_exists="replace")

    return conn
