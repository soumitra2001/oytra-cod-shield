"""Import orders_sample.csv into Supabase and compute pincode_stats."""

import os
import sys
import pandas as pd
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import engine


def import_csv(csv_path: str = "orders_sample.csv"):
    """Load CSV into the orders table."""
    print(f"📂 Reading {csv_path}...")
    df = pd.read_csv(csv_path)

    # Clean column names
    df.columns = df.columns.str.strip().str.lower()

    # Deduplicate orders by order_id
    initial_count = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    if len(df) < initial_count:
        print(f"🧹 Removed {initial_count - len(df)} duplicate order rows")

    # Ensure proper types
    df["order_datetime"] = pd.to_datetime(df["order_datetime"])
    df["order_value"] = pd.to_numeric(df["order_value"], errors="coerce")
    df["num_items"] = pd.to_numeric(df["num_items"], errors="coerce").fillna(1).astype(int)
    df["customer_prior_orders"] = pd.to_numeric(df["customer_prior_orders"], errors="coerce").fillna(0).astype(int)
    df["customer_prior_rto"] = pd.to_numeric(df["customer_prior_rto"], errors="coerce").fillna(0).astype(int)

    # Normalize final_status
    df["final_status"] = df["final_status"].str.strip().str.upper()

    print(f"📊 Loaded {len(df)} orders")
    print(f"   - Delivered: {(df['final_status'] == 'DELIVERED').sum()}")
    print(f"   - RTO: {(df['final_status'] == 'RTO').sum()}")

    # Insert into database
    with engine.begin() as conn:
        # Clear existing data
        conn.execute(text("DELETE FROM order_decisions"))
        conn.execute(text("DELETE FROM whatsapp_conversations"))
        conn.execute(text("DELETE FROM orders"))
        print("🗑️  Cleared existing data")

        # Insert orders
        df.to_sql("orders", conn, if_exists="append", index=False, method="multi", chunksize=200)
        print(f"✅ Inserted {len(df)} orders into database")

    return df


def compute_pincode_stats():
    """Aggregate pincode-level RTO statistics from orders table."""
    print("\n📍 Computing pincode stats...")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pincode_stats"))

        conn.execute(text("""
            INSERT INTO pincode_stats (pincode, total_orders, total_delivered, total_rto, rto_rate, avg_order_value, risk_reliable)
            SELECT
                pincode,
                COUNT(*) AS total_orders,
                SUM(CASE WHEN final_status = 'DELIVERED' THEN 1 ELSE 0 END) AS total_delivered,
                SUM(CASE WHEN final_status = 'RTO' THEN 1 ELSE 0 END) AS total_rto,
                ROUND(
                    100.0 * SUM(CASE WHEN final_status = 'RTO' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                    2
                ) AS rto_rate,
                ROUND(AVG(order_value), 2) AS avg_order_value,
                CASE WHEN COUNT(*) >= 5 THEN TRUE ELSE FALSE END AS risk_reliable
            FROM orders
            GROUP BY pincode
        """))

        result = conn.execute(text("SELECT COUNT(*) FROM pincode_stats"))
        count = result.scalar()
        print(f"✅ Computed stats for {count} pincodes")

        # Show top risky pincodes
        result = conn.execute(text("""
            SELECT pincode, total_orders, total_rto, rto_rate
            FROM pincode_stats
            WHERE risk_reliable = TRUE
            ORDER BY rto_rate DESC
            LIMIT 10
        """))
        rows = result.fetchall()
        if rows:
            print("\n🔴 Top 10 risky pincodes (min 5 orders):")
            print(f"   {'Pincode':<10} {'Orders':<8} {'RTOs':<6} {'RTO%':<8}")
            for r in rows:
                print(f"   {r[0]:<10} {r[1]:<8} {r[2]:<6} {r[3]:<8}%")


if __name__ == "__main__":
    csv_file = os.path.join(os.path.dirname(__file__), "..", "..", "orders_sample.csv")
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)

    import_csv(csv_file)
    compute_pincode_stats()
    print("\n🎉 Data import complete!")
