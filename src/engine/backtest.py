"""Backtest the decision engine against historical orders."""

import pandas as pd
from sqlalchemy import text
from src.config import engine as db_engine, RTO_COST_PER_ORDER, GROSS_MARGIN_RATE


def run_backtest():
    """
    Replay the decision policy on all historical orders and calculate financial impact.
    Reads from order_decisions table (must be populated first).
    """
    with db_engine.connect() as conn:
        query = text("""
            SELECT
                od.decision,
                od.risk_score,
                o.order_value,
                o.final_status,
                o.customer_prior_orders
            FROM order_decisions od
            JOIN orders o ON od.order_id = o.order_id
        """)
        df = pd.read_sql(query, conn)

    if df.empty:
        print("❌ No decisions found. Run the decision engine first.")
        return None

    results = {
        "total_orders": len(df),
        "buckets": {},
        "financial": {},
    }

    for decision in ["ship", "confirm", "nudge_prepaid", "cancel"]:
        subset = df[df["decision"] == decision]
        count = len(subset)
        rto_count = (subset["final_status"] == "RTO").sum()
        delivered_count = (subset["final_status"] == "DELIVERED").sum()

        results["buckets"][decision] = {
            "count": count,
            "actual_rto": int(rto_count),
            "actual_delivered": int(delivered_count),
            "rto_rate": round(100 * rto_count / max(count, 1), 1),
        }

    # Financial calculations
    cancelled = df[df["decision"] == "cancel"]
    cancelled_genuine = cancelled[cancelled["final_status"] == "DELIVERED"]
    cancelled_rto = cancelled[cancelled["final_status"] == "RTO"]

    # Money saved: RTOs we correctly avoided
    saved_from_cancel = len(cancelled_rto) * RTO_COST_PER_ORDER

    # Money lost: genuine orders we wrongly cancelled
    lost_from_cancel = (cancelled_genuine["order_value"] * GROSS_MARGIN_RATE).sum()

    # Nudge savings (assume some conversion rate)
    nudged = df[df["decision"] == "nudge_prepaid"]
    nudged_rto = nudged[nudged["final_status"] == "RTO"]
    # Estimate: if 30% convert to prepaid, those avoid RTO at COD rate
    estimated_nudge_conversions = len(nudged) * 0.30
    nudge_rto_avoided = estimated_nudge_conversions * 0.28 * RTO_COST_PER_ORDER  # COD RTO rate
    nudge_rto_avoided -= estimated_nudge_conversions * 0.04 * RTO_COST_PER_ORDER  # minus prepaid RTO

    results["financial"] = {
        "saved_from_cancels": round(saved_from_cancel, 2),
        "lost_from_cancels": round(lost_from_cancel, 2),
        "saved_from_nudges": round(nudge_rto_avoided, 2),
        "net_impact": round(saved_from_cancel - lost_from_cancel + nudge_rto_avoided, 2),
    }

    return results
