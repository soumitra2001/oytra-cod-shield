"""Oytra COD RTO Risk Engine — Founder Dashboard & WhatsApp Simulator."""

import os
import sys
import json
import pandas as pd
import streamlit as st
from datetime import datetime, date

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import (
    RTO_COST_PER_ORDER,
    AVG_MARGIN_PER_ORDER,
    GROSS_MARGIN_RATE,
    CUSTOMER_ACQUISITION_COST,
    engine as db_engine,
)
from src.whatsapp.flows import (
    create_confirmation_message,
    create_nudge_message,
    calculate_discount,
    handle_reply,
    handle_timeout,
)

# Page configuration
st.set_page_config(
    page_title="Oytra | COD RTO Intelligence",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .chat-bubble-bot {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        max-width: 85%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .chat-bubble-user {
        background-color: #dcf8c6;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 10px;
        margin-left: auto;
        max-width: 85%;
        text-align: right;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    """Load orders, decisions, and rules from database."""
    try:
        with db_engine.connect() as conn:
            orders_df = pd.read_sql("SELECT * FROM orders", conn)
            decisions_df = pd.read_sql("SELECT * FROM order_decisions", conn)
            rules_df = pd.read_sql("SELECT * FROM decision_rules ORDER BY category, rule_key", conn)
            pincodes_df = pd.read_sql("SELECT * FROM pincode_stats ORDER BY total_orders DESC", conn)

        if not decisions_df.empty and not orders_df.empty:
            merged = pd.merge(decisions_df, orders_df, on="order_id", suffixes=("", "_order"))
            merged["order_date"] = pd.to_datetime(merged["order_datetime"]).dt.date
            return merged, rules_df, pincodes_df
        return pd.DataFrame(), rules_df, pincodes_df
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def update_rule_in_db(key: str, value: float):
    """Update a threshold in decision_rules."""
    with db_engine.begin() as conn:
        from sqlalchemy import text
        conn.execute(
            text("UPDATE decision_rules SET rule_value = :v, updated_at = NOW() WHERE rule_key = :k"),
            {"v": value, "k": key},
        )
    st.cache_data.clear()


# Load data
df, rules_df, pincodes_df = load_data()

# ----------------- SIDEBAR -----------------
st.sidebar.image("https://img.icons8.com/fluency/96/natural-food.png", width=60)
st.sidebar.title("Oytra COD Control")
st.sidebar.caption("D2C Haircare • Pre-Shipment COD RTO Protection")

navigation = st.sidebar.radio(
    "Navigation",
    ["📊 Founder Dashboard", "💬 WhatsApp Simulator", "⚙️ Rules & Thresholds", "🔍 Order Explorer", "📈 Pincode Risk Map"],
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏷️ Business Constants")
st.sidebar.markdown(f"- **RTO Cost**: ₹{RTO_COST_PER_ORDER:.2f}")
st.sidebar.markdown(f"- **Gross Margin**: {int(GROSS_MARGIN_RATE * 100)}%")
st.sidebar.markdown(f"- **Avg Profit/Order**: ₹{AVG_MARGIN_PER_ORDER:.2f}")
st.sidebar.markdown(f"- **CAC (Meta Ads)**: ₹{CUSTOMER_ACQUISITION_COST:.0f}+")


# ----------------- PAGE 1: FOUNDER DASHBOARD -----------------
if navigation == "📊 Founder Dashboard":
    st.title("☀️ Founder Morning Overview")
    st.markdown("Decision breakdown, avoided RTO savings, cancellation costs, and net bottom-line impact.")

    if df.empty:
        st.warning("No decision data found. Please run the decision engine script first: `python scripts/run_engine.py`")
    else:
        # Date selector
        dates_available = sorted(df["order_date"].unique(), reverse=True)
        date_filter = st.selectbox(
            "Filter Timeframe",
            ["Full Historical Dataset (~2,000 orders)", "Most Recent Day in Dataset"] + [str(d) for d in dates_available[:5]],
        )

        if date_filter == "Full Historical Dataset (~2,000 orders)":
            active_df = df
        elif date_filter == "Most Recent Day in Dataset":
            latest_d = dates_available[0]
            active_df = df[df["order_date"] == latest_d]
        else:
            sel_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            active_df = df[df["order_date"] == sel_date]

        # 4 Decision Buckets
        ship_count = (active_df["decision"] == "ship").sum()
        confirm_count = (active_df["decision"] == "confirm").sum()
        nudge_count = (active_df["decision"] == "nudge_prepaid").sum()
        cancel_count = (active_df["decision"] == "cancel").sum()
        total_eval = len(active_df)

        st.markdown("### 📦 The 4 Decision Buckets")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("1. Ship As-Is", f"{ship_count}", f"{round(100*ship_count/max(total_eval,1), 1)}% of orders")
        with c2:
            st.metric("2. WhatsApp Confirm", f"{confirm_count}", f"{round(100*confirm_count/max(total_eval,1), 1)}% of orders")
        with c3:
            st.metric("3. Nudge to Prepaid", f"{nudge_count}", f"{round(100*nudge_count/max(total_eval,1), 1)}% of orders")
        with c4:
            st.metric("4. Hold / Cancel", f"{cancel_count}", f"{round(100*cancel_count/max(total_eval,1), 1)}% of orders")

        st.markdown("---")
        st.markdown("### 💰 Financial Impact Calculation")

        # Calculations
        # 1. Avoided RTOs:
        # Cancelled orders that would have RTO'd
        cancelled_rtos = ((active_df["decision"] == "cancel") & (active_df["actual_status"] == "RTO")).sum()
        saved_avoided_rtos = cancelled_rtos * RTO_COST_PER_ORDER

        # 2. Lost margin from genuine orders cancelled:
        cancelled_genuine = ((active_df["decision"] == "cancel") & (active_df["actual_status"] == "DELIVERED")).sum()
        cancelled_genuine_val = active_df[(active_df["decision"] == "cancel") & (active_df["actual_status"] == "DELIVERED")]["order_value"].sum()
        lost_margin = cancelled_genuine_val * GROSS_MARGIN_RATE

        # 3. Nudge to Prepaid Impact:
        # Assume 25% of nudged orders convert to prepaid
        # Converting COD (28% RTO) to Prepaid (4% RTO) saves (0.28 - 0.04)*169.40 = ~₹40.66 per conversion
        # Less the discount given (~₹35 avg)
        converted_prepaid_est = nudge_count * 0.25
        saved_from_nudge_conversion = converted_prepaid_est * (0.28 - 0.04) * RTO_COST_PER_ORDER
        discounts_given_est = converted_prepaid_est * 35.0
        net_nudge_gain = saved_from_nudge_conversion - discounts_given_est

        # Net impact
        net_financial_impact = saved_avoided_rtos - lost_margin + net_nudge_gain

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Estimated ₹ Saved from Avoided RTOs",
                f"₹{saved_avoided_rtos:,.2f}",
                f"{cancelled_rtos} high-risk returns stopped",
            )
        with m2:
            st.metric(
                "Estimated ₹ Lost from False Cancels",
                f"-₹{lost_margin:,.2f}",
                f"{cancelled_genuine} genuine buyers cancelled",
                delta_color="inverse",
            )
        with m3:
            st.metric(
                "Net Nudge Prepaid Gain",
                f"+₹{net_nudge_gain:,.2f}",
                f"{int(converted_prepaid_est)} est. prepaid conversions",
            )
        with m4:
            st.metric(
                "⭐ Net ₹ Financial Impact",
                f"₹{net_financial_impact:,.2f}",
                "Net bottom-line contribution",
            )

        st.info(
            f"💡 **Executive Summary**: Out of **{total_eval}** evaluated COD orders, **{ship_count}** are safe to ship immediately. "
            f"**{confirm_count}** are protected via WhatsApp confirmation to verify intent without friction. "
            f"**{nudge_count}** borderline risky orders are offered an instant discount to convert into prepaid (avoiding COD return risk while keeping the Meta ad acquisition). "
            f"Only **{cancel_count}** non-recoverable repeat RTO offenders are blocked, stopping **₹{saved_avoided_rtos:,.2f}** in dead shipping losses."
        )


# ----------------- PAGE 2: WHATSAPP SIMULATOR -----------------
elif navigation == "💬 WhatsApp Simulator":
    st.title("💬 WhatsApp Interactive Mock Simulator")
    st.markdown("Live demonstration of the automated conversational customer flows for **Ship after confirmation** and **Nudge to prepaid**.")

    flow_type = st.radio("Select Customer Flow", ["Ship after confirmation", "Nudge to prepaid"], horizontal=True)

    col_setup, col_chat = st.columns([1, 1.3])

    with col_setup:
        st.subheader("1. Order Parameters")
        cust_name = st.text_input("Customer Name", "Rahul Sharma")
        order_num = st.text_input("Order ID", "KT101889")
        order_val = st.number_input("Order Value (₹)", min_value=199, max_value=5000, value=649, step=50)

        # Discount calculation math
        rule_dict = {}
        if not rules_df.empty:
            rule_dict = dict(zip(rules_df["rule_key"], rules_df["rule_value"]))
        discount_val = calculate_discount(order_val, rule_dict)

        if flow_type == "Nudge to prepaid":
            st.markdown("#### 📐 The Mathematical Justification for the Discount")
            st.caption(
                f"- Expected RTO loss on COD order: 28% × ₹169.40 = **₹47.43**\n"
                f"- Expected RTO loss on Prepaid order: 4% × ₹169.40 = **₹6.78**\n"
                f"- Gross RTO savings from converting to prepaid: ₹47.43 - ₹6.78 = **₹40.65**\n"
                f"- **Discount Offered**: **₹{int(discount_val)}** (leaves net positive brand profit + eliminates payment collection friction!)"
            )

        st.subheader("2. Simulate Customer Action")
        quick_action = st.selectbox(
            "Customer Reply Preset",
            ["Type Custom Message", "Reply: 'YES'", "Reply: 'NO'", "Reply: 'Haan bhej do please' (Hinglish)", "Reply: 'test random text'", "24 Hours Timeout (No Reply)"],
        )

        custom_text = ""
        if quick_action == "Type Custom Message":
            custom_text = st.text_input("Enter customer WhatsApp message:")
        elif quick_action == "Reply: 'YES'":
            custom_text = "YES"
        elif quick_action == "Reply: 'NO'":
            custom_text = "NO"
        elif quick_action == "Reply: 'Haan bhej do please' (Hinglish)":
            custom_text = "Haan bhej do please"
        elif quick_action == "Reply: 'test random text'":
            custom_text = "What is the delivery date?"
        else:
            custom_text = "__TIMEOUT__"

    with col_chat:
        st.subheader("📱 Live WhatsApp Preview")
        st.caption("WhatsApp Business API • Message Window")

        # Prepare outgoing message
        dummy_order = {"customer_name": cust_name, "order_id": order_num, "order_value": order_val}
        if flow_type == "Ship after confirmation":
            out_msg = create_confirmation_message(dummy_order)["message"]
            mode_key = "confirmation"
        else:
            out_msg = create_nudge_message(dummy_order, discount_val)["message"]
            mode_key = "nudge_prepaid"

        # Display Outgoing Bot Message
        st.markdown(f'<div class="chat-bubble-bot"><b>Oytra Care</b> 🌿<br><br>{out_msg.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

        if custom_text == "__TIMEOUT__":
            timeout_res = handle_timeout(mode_key, 1)
            st.warning("⏱️ **24 Hours Elapsed with No Reply**")
            st.markdown(f'<div class="chat-bubble-bot"><b>System Auto-Action</b> 🤖<br><br>{timeout_res["response_message"]}</div>', unsafe_allow_html=True)
            st.error(f"Final Order Status: **{timeout_res['action'].upper()}**")
        elif custom_text:
            # Customer reply
            st.markdown(f'<div class="chat-bubble-user"><b>{cust_name}</b><br><br>{custom_text}</div>', unsafe_allow_html=True)

            # Process reply
            bot_reply = handle_reply(custom_text, mode_key)
            st.markdown(f'<div class="chat-bubble-bot"><b>Oytra Care</b> 🌿<br><br>{bot_reply["response_message"].replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

            if bot_reply["new_status"] == "converted_prepaid":
                st.success("💳 **Prepaid Conversion Triggered**: Order status updated to PREPAID upon payment completion.")
            elif bot_reply["new_status"] == "confirmed":
                st.success("✅ **Order Confirmed**: Order released to warehouse for priority fulfillment.")
            elif bot_reply["new_status"] == "rejected":
                st.error("🛑 **Order Cancelled**: Order marked as customer-cancelled. No forward shipping burnt.")


# ----------------- PAGE 3: RULES & THRESHOLDS -----------------
elif navigation == "⚙️ Rules & Thresholds":
    st.title("⚙️ Non-Technical Business Rules Panel")
    st.markdown("Operations & Marketing managers can adjust risk thresholds in real-time **without modifying any code**.")

    if rules_df.empty:
        st.warning("No rules found in database.")
    else:
        for cat, group in rules_df.groupby("category"):
            st.subheader(f"Category: {cat.capitalize()}")
            for idx, row in group.iterrows():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**`{row['rule_key']}`** — {row['description']}")
                with c2:
                    new_val = st.number_input(
                        "Value",
                        value=float(row["rule_value"]),
                        key=f"rule_{row['rule_key']}",
                        label_visibility="collapsed",
                    )
                    if new_val != float(row["rule_value"]):
                        if st.button("Save", key=f"btn_{row['rule_key']}"):
                            update_rule_in_db(row["rule_key"], new_val)
                            st.success(f"Updated {row['rule_key']} to {new_val}")
            st.markdown("---")


# ----------------- PAGE 4: ORDER EXPLORER -----------------
elif navigation == "🔍 Order Explorer":
    st.title("🔍 Order Evaluation Explorer")
    st.markdown("Inspect every historical COD order, risk scoring breakdown, plain-English reason, and LLM flags.")

    if df.empty:
        st.warning("No data found.")
    else:
        filter_decision = st.multiselect("Filter by Decision", ["ship", "confirm", "nudge_prepaid", "cancel"], default=["ship", "confirm", "nudge_prepaid", "cancel"])
        search_query = st.text_input("Search Customer Name, Phone, Pincode, or Order ID:")

        view_df = df[df["decision"].isin(filter_decision)]
        if search_query:
            q = search_query.lower()
            view_df = view_df[
                view_df["customer_name"].str.lower().str.contains(q, na=False)
                | view_df["order_id"].str.lower().str.contains(q, na=False)
                | view_df["pincode"].astype(str).str.contains(q, na=False)
            ]

        st.caption(f"Showing {len(view_df)} orders")

        cols_to_display = ["order_id", "customer_name", "pincode", "order_value", "risk_score", "decision", "reason", "actual_status"]
        st.dataframe(view_df[cols_to_display], use_container_width=True, height=500)


# ----------------- PAGE 5: PINCODE RISK MAP -----------------
elif navigation == "📈 Pincode Risk Map":
    st.title("📈 Pincode RTO Risk Aggregation")
    st.markdown("Aggregated historical RTO performance across delivery pincodes.")

    if pincodes_df.empty:
        st.warning("No pincode stats found.")
    else:
        st.dataframe(pincodes_df, use_container_width=True, height=500)
