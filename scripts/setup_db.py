"""One-command database setup: create tables, seed rules, import CSV."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from src.config import engine, IS_POSTGRES
from src.db.import_csv import import_csv, compute_pincode_stats


def run_sql_file(filepath: str):
    """Execute a SQL file against the database."""
    with open(filepath, "r") as f:
        sql = f.read()

    with engine.begin() as conn:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
    print(f"✅ Executed {os.path.basename(filepath)}")


def main():
    print("=" * 50)
    print("🚀 Oytra COD RTO — Database Setup")
    print(f"🔗 Database Dialect: {'PostgreSQL (Supabase)' if IS_POSTGRES else 'SQLite (Local)'}")
    print("=" * 50)

    # Step 1: Create tables
    schema_filename = "schema.sql" if IS_POSTGRES else "schema_sqlite.sql"
    schema_path = os.path.join(os.path.dirname(__file__), "..", "src", "db", schema_filename)
    print(f"\n📋 Creating tables using {schema_filename}...")
    run_sql_file(schema_path)

    # Step 2: Seed decision rules
    seed_path = os.path.join(os.path.dirname(__file__), "..", "src", "db", "seed.sql")
    print("\n🌱 Seeding decision rules...")
    run_sql_file(seed_path)

    # Step 3: Import CSV
    csv_path = os.path.join(os.path.dirname(__file__), "..", "orders_sample.csv")
    if os.path.exists(csv_path):
        print("\n📂 Importing CSV data...")
        import_csv(csv_path)
        compute_pincode_stats()
    else:
        print(f"\n⚠️  CSV not found at {csv_path} — skipping import")

    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
