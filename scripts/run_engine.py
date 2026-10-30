"""Run the decision engine on all orders in the database and save decisions."""

import os
import sys
import json
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import engine as db_engine, IS_POSTGRES
from src.engine.decision_engine import make_decision
from src.engine.llm_analyzer import analyze_order_with_llm


def load_rules(conn):
    rows = conn.execute(text("SELECT rule_key, rule_value FROM decision_rules")).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def load_pincode_stats(conn):
    rows = conn.execute(text("""
        SELECT pincode, total_orders, total_rto, rto_rate, risk_reliable
        FROM pincode_stats
    """)).fetchall()
    stats = {}
    for r in rows:
        stats[str(r[0])] = {
            "total_orders": r[1],
            "total_rto": r[2],
            "rto_rate": float(r[3] or 0),
            "risk_reliable": bool(r[4]),
        }
    return stats


def run_batch_evaluation(max_llm_samples: int = 20):
    """
    Evaluate all orders in the orders table.
    To avoid excessive API calls or quota exhaustion, we invoke the LLM for:
    - Highly anomalous addresses/names
    - A sample of up to max_llm_samples orders
    """
    print("=" * 60)
    print("🚀 Running Decision Engine on Orders")
    print("=" * 60)

    with db_engine.begin() as conn:
        rules = load_rules(conn)
        pincode_stats = load_pincode_stats(conn)

        orders_df = pd.read_sql(
            "SELECT * FROM orders ORDER BY order_datetime ASC", conn
        )

        print(f"📦 Evaluating {len(orders_df)} orders...")

        # Clear existing decisions
        conn.execute(text("DELETE FROM order_decisions"))

        decisions_to_insert = []
        llm_invocations = 0

        # Heuristic to detect obviously suspicious names or addresses locally before LLM
        def is_suspicious_for_llm(name, addr):
            name_str = str(name).strip().lower()
            addr_str = str(addr).strip().lower()
            if len(name_str) <= 3 or name_str in ["asdf", "test", "abc", "xyz", "qwe", "na", "null"]:
                return True
            if len(addr_str) < 15 or any(k in addr_str for k in ["test", "asdf", "fake"]):
                return True
            return False

        for idx, row in orders_df.iterrows():
            order_dict = row.to_dict()
            pincode = str(order_dict.get("pincode", ""))
            p_stats = pincode_stats.get(pincode)

            # Check if LLM should be consulted
            llm_result = None
            should_consult_llm = is_suspicious_for_llm(order_dict.get("customer_name"), order_dict.get("address"))
            if should_consult_llm and llm_invocations < max_llm_samples:
                llm_result = analyze_order_with_llm(order_dict)
                if llm_result:
                    llm_invocations += 1

            result = make_decision(order_dict, p_stats, rules, llm_result)

            decisions_to_insert.append({
                "order_id": order_dict["order_id"],
                "decision": result["decision"],
                "risk_score": result["risk_score"],
                "risk_category": result["risk_category"],
                "reason": result["reason"],
                "risk_factors": json.dumps(result["risk_factors"]),
                "llm_used": 1 if result["llm_used"] else 0,
                "llm_analysis": json.dumps(result["llm_analysis"]) if result["llm_analysis"] else None,
                "actual_status": order_dict.get("final_status"),
            })

        # Insert in chunks into order_decisions
        if IS_POSTGRES:
            insert_query = text("""
                INSERT INTO order_decisions (
                    order_id, decision, risk_score, risk_category, reason,
                    risk_factors, llm_used, llm_analysis, actual_status
                ) VALUES (
                    :order_id, :decision, :risk_score, :risk_category, :reason,
                    CAST(:risk_factors AS jsonb), :llm_used,
                    CASE WHEN :llm_analysis IS NOT NULL THEN CAST(:llm_analysis AS jsonb) ELSE NULL END,
                    :actual_status
                )
                ON CONFLICT (order_id) DO UPDATE SET
                    decision = EXCLUDED.decision,
                    risk_score = EXCLUDED.risk_score,
                    risk_category = EXCLUDED.risk_category,
                    reason = EXCLUDED.reason,
                    risk_factors = EXCLUDED.risk_factors,
                    llm_used = EXCLUDED.llm_used,
                    llm_analysis = EXCLUDED.llm_analysis,
                    actual_status = EXCLUDED.actual_status,
                    decided_at = NOW()
            """)
        else:
            insert_query = text("""
                INSERT INTO order_decisions (
                    order_id, decision, risk_score, risk_category, reason,
                    risk_factors, llm_used, llm_analysis, actual_status
                ) VALUES (
                    :order_id, :decision, :risk_score, :risk_category, :reason,
                    :risk_factors, :llm_used, :llm_analysis, :actual_status
                )
                ON CONFLICT (order_id) DO UPDATE SET
                    decision = EXCLUDED.decision,
                    risk_score = EXCLUDED.risk_score,
                    risk_category = EXCLUDED.risk_category,
                    reason = EXCLUDED.reason,
                    risk_factors = EXCLUDED.risk_factors,
                    llm_used = EXCLUDED.llm_used,
                    llm_analysis = EXCLUDED.llm_analysis,
                    actual_status = EXCLUDED.actual_status,
                    decided_at = CURRENT_TIMESTAMP
            """)

        chunk_size = 100
        for i in range(0, len(decisions_to_insert), chunk_size):
            chunk = decisions_to_insert[i:i + chunk_size]
            conn.execute(insert_query, chunk)

        print(f"✅ Stored {len(decisions_to_insert)} decisions in database!")
        print(f"🤖 LLM invoked for {llm_invocations} flagged orders.")

        # Print summary breakdown
        summary_query = text("""
            SELECT decision, COUNT(*) as count,
                   ROUND(AVG(risk_score), 1) as avg_risk,
                   SUM(CASE WHEN actual_status = 'RTO' THEN 1 ELSE 0 END) as actual_rtos,
                   SUM(CASE WHEN actual_status = 'DELIVERED' THEN 1 ELSE 0 END) as actual_delivered
            FROM order_decisions
            GROUP BY decision
            ORDER BY count DESC
        """)
        summary_rows = conn.execute(summary_query).fetchall()

        print("\n📊 Decision Breakdown:")
        print(f"{'Decision':<20} {'Count':<8} {'Avg Risk':<10} {'Actual RTO':<12} {'Delivered':<10}")
        print("-" * 65)
        for r in summary_rows:
            print(f"{r[0]:<20} {r[1]:<8} {r[2]:<10} {r[3]:<12} {r[4]:<10}")


if __name__ == "__main__":
    run_batch_evaluation()
