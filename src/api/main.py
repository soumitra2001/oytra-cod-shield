"""FastAPI backend — decision engine API endpoints."""

import os
import re
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import get_db, engine as db_engine, IS_POSTGRES, RTO_COST_PER_ORDER, GROSS_MARGIN_RATE
from src.engine.decision_engine import make_decision
from src.engine.llm_analyzer import analyze_order_with_llm
from src.engine.backtest import run_backtest
from src.whatsapp.flows import (
    create_confirmation_message,
    create_nudge_message,
    calculate_discount,
    handle_reply,
    handle_timeout,
)

app = FastAPI(
    title="Oytra COD RTO Decision Engine",
    description="AI-powered system to evaluate COD orders before shipping",
    version="1.0.0",
)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")


# ---------- Pydantic Models ----------

class OrderInput(BaseModel):
    order_id: str | None = None
    customer_name: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    order_value: float
    items: str = "Oytra Haircare Set"
    num_items: int = 1
    customer_prior_orders: int | None = None
    customer_prior_rto: int | None = None
    utm_source: str = "new_order_ui"
    payment_method: str = "COD"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[^0-9]", "", str(v))
        if len(clean) == 12 and clean.startswith("91"):
            clean = clean[2:]
        if len(clean) != 10:
            raise ValueError("Customer phone number must be exactly 10 digits")
        return clean


class WhatsAppReply(BaseModel):
    order_id: str
    reply: str


class StatusUpdateInput(BaseModel):
    status: str


class WhatsAppSimulateRequest(BaseModel):
    customer_name: str
    order_id: str
    order_value: float
    flow_type: str = "confirmation"  # confirmation or nudge_prepaid
    action: str = "init"  # init, reply, timeout
    reply_text: str | None = None


# ---------- Helper ----------

def _load_rules() -> dict:
    """Load decision rules from DB into a dict."""
    with db_engine.connect() as conn:
        rows = conn.execute(text("SELECT rule_key, rule_value FROM decision_rules")).fetchall()
    return {r[0]: float(r[1]) for r in rows}


def _get_pincode_stats(pincode: str) -> dict | None:
    """Get stats for a pincode."""
    with db_engine.connect() as conn:
        row = conn.execute(
            text("SELECT total_orders, total_rto, rto_rate, risk_reliable FROM pincode_stats WHERE pincode = :p"),
            {"p": pincode},
        ).fetchone()
    if row:
        return {"total_orders": row[0], "total_rto": row[1], "rto_rate": float(row[2]), "risk_reliable": row[3]}
    return None


def _lookup_customer_history(phone: str) -> tuple[int, int]:
    """
    Look up customer order and return history by phone number in the orders database.
    Returns (past_delivered_orders, past_rtos).
    """
    clean = phone.strip().replace(" ", "").replace("+91", "").replace("-", "")
    with db_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT 
                COALESCE(SUM(CASE WHEN final_status = 'DELIVERED' OR final_status = 'CONFIRMED' THEN 1 ELSE 0 END), 0) as delivered,
                COALESCE(SUM(CASE WHEN final_status = 'RTO' OR final_status = 'CUSTOMER_CANCELLED' THEN 1 ELSE 0 END), 0) as rto,
                COALESCE(MAX(customer_prior_orders), 0) as max_prior_orders,
                COALESCE(MAX(customer_prior_rto), 0) as max_prior_rto
            FROM orders
            WHERE REPLACE(REPLACE(REPLACE(phone, ' ', ''), '+91', ''), '-', '') = :p
               OR phone LIKE :like_p
        """), {
            "p": clean,
            "like_p": f"%{clean[-10:]}%" if len(clean) >= 10 else f"%{clean}%"
        }).fetchone()

        if row and (row[0] > 0 or row[1] > 0 or row[2] > 0 or row[3] > 0):
            orders_cnt = max(int(row[0]), int(row[2]))
            rto_cnt = max(int(row[1]), int(row[3]))
            return orders_cnt, rto_cnt

    return 0, 0


# ---------- Endpoints ----------

@app.get("/")
def root():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Oytra COD RTO Decision Engine", "docs": "/docs"}


@app.get("/api/orders")
def get_orders(limit: int = 100, decision: str | None = None):
    """Retrieve orders with decisions for the frontend explorer."""
    with db_engine.connect() as conn:
        q = """
            SELECT o.order_id, o.customer_name, o.phone, o.address, o.city, o.state, o.pincode,
                   o.order_value, o.customer_prior_orders, o.customer_prior_rto, o.final_status,
                   od.decision, od.risk_score, od.reason
            FROM orders o
            LEFT JOIN order_decisions od ON o.order_id = od.order_id
        """
        params = {}
        if decision:
            q += " WHERE od.decision = :dec"
            params["dec"] = decision
        q += " ORDER BY o.order_datetime DESC LIMIT :lim"
        params["lim"] = limit

        rows = conn.execute(text(q), params).fetchall()
        return [
            {
                "order_id": r[0],
                "customer_name": r[1],
                "phone": r[2],
                "address": r[3],
                "city": r[4],
                "state": r[5],
                "pincode": r[6],
                "order_value": float(r[7] or 0),
                "customer_prior_orders": r[8],
                "customer_prior_rto": r[9],
                "final_status": r[10],
                "decision": r[11],
                "risk_score": float(r[12]) if r[12] is not None else None,
                "reason": r[13],
            }
            for r in rows
        ]


@app.get("/api/orders/created")
def get_created_orders():
    """Retrieve newly created/evaluated orders from the database."""
    with db_engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT o.order_id, o.customer_name, o.phone, o.address, o.city, o.state, o.pincode,
                   o.order_value, o.customer_prior_orders, o.customer_prior_rto, o.final_status,
                   od.decision, od.risk_score, od.reason, od.risk_category, od.llm_used,
                   o.order_datetime
            FROM orders o
            JOIN order_decisions od ON o.order_id = od.order_id
            WHERE o.utm_source = 'new_order_ui'
            ORDER BY o.id DESC
        """)).fetchall()
        return [
            {
                "order_id": r[0],
                "customer_name": r[1],
                "phone": r[2],
                "address": r[3],
                "city": r[4],
                "state": r[5],
                "pincode": r[6],
                "order_value": float(r[7] or 0),
                "customer_prior_orders": r[8],
                "customer_prior_rto": r[9],
                "final_status": r[10],
                "decision": r[11],
                "risk_score": float(r[12]) if r[12] is not None else None,
                "reason": r[13],
                "risk_category": r[14],
                "llm_used": bool(r[15]),
                "order_datetime": str(r[16]),
            }
            for r in rows
        ]


@app.get("/api/presets")
def get_presets():
    """Dynamically query real orders from database representing key risk scenarios."""
    presets = {}
    with db_engine.connect() as conn:
        # Safe
        row = conn.execute(text("""
            SELECT order_id, customer_name, phone, address, city, state, pincode, order_value,
                   customer_prior_orders, customer_prior_rto
            FROM orders
            WHERE customer_prior_orders >= 3 AND customer_prior_rto = 0
            LIMIT 1
        """)).fetchone()
        if row:
            presets["safe"] = {
                "order_id": row[0], "customer_name": row[1], "phone": row[2],
                "address": row[3], "city": row[4], "state": row[5], "pincode": str(row[6]).replace(".0", ""),
                "order_value": float(row[7]), "prior_orders": row[8], "prior_rto": row[9],
                "label": "✅ Loyal Safe Buyer"
            }

        # Hinglish Landmark
        row = conn.execute(text("""
            SELECT order_id, customer_name, phone, address, city, state, pincode, order_value,
                   customer_prior_orders, customer_prior_rto
            FROM orders
            WHERE (address LIKE '%ke saamne%' OR address LIKE '%ke paas%' OR address LIKE '%chowk%')
            LIMIT 1
        """)).fetchone()
        if row:
            presets["hinglish"] = {
                "order_id": row[0], "customer_name": row[1], "phone": row[2],
                "address": row[3], "city": row[4], "state": row[5], "pincode": str(row[6]).replace(".0", ""),
                "order_value": float(row[7]), "prior_orders": row[8], "prior_rto": row[9],
                "label": "🌿 First-Time (Hinglish)"
            }

        # Short/Incomplete Address
        row = conn.execute(text("""
            SELECT order_id, customer_name, phone, address, city, state, pincode, order_value,
                   customer_prior_orders, customer_prior_rto
            FROM orders
            WHERE LENGTH(address) < 15
            LIMIT 1
        """)).fetchone()
        if row:
            presets["short_addr"] = {
                "order_id": row[0], "customer_name": row[1], "phone": row[2],
                "address": row[3], "city": row[4], "state": row[5], "pincode": str(row[6]).replace(".0", ""),
                "order_value": float(row[7]), "prior_orders": row[8], "prior_rto": row[9],
                "label": "⚠️ Incomplete 'xyz' Address"
            }

        # Serial Returner
        row = conn.execute(text("""
            SELECT order_id, customer_name, phone, address, city, state, pincode, order_value,
                   customer_prior_orders, customer_prior_rto
            FROM orders
            WHERE customer_prior_rto >= 2
            LIMIT 1
        """)).fetchone()
        if row:
            presets["serial_rto"] = {
                "order_id": row[0], "customer_name": row[1], "phone": row[2],
                "address": row[3], "city": row[4], "state": row[5], "pincode": str(row[6]).replace(".0", ""),
                "order_value": float(row[7]), "prior_orders": row[8], "prior_rto": row[9],
                "label": "🛑 Serial Returner (2 RTOs)"
            }

    if not presets:
        raise HTTPException(status_code=404, detail="No orders found in database. Please run python scripts/setup_db.py first.")
    return presets


@app.post("/api/whatsapp/simulate")
def simulate_whatsapp(req: WhatsAppSimulateRequest):
    """Simulate WhatsApp interactions dynamically using business logic."""
    rules = _load_rules()
    order_data = {
        "customer_name": req.customer_name,
        "order_id": req.order_id,
        "order_value": req.order_value,
    }

    if req.action == "init":
        if req.flow_type == "confirmation":
            msg_obj = create_confirmation_message(order_data)
            return {
                "status": "PENDING_REPLY",
                "message": msg_obj["message"],
                "expires_at": msg_obj["expires_at"],
            }
        else:
            discount = calculate_discount(req.order_value, rules)
            msg_obj = create_nudge_message(order_data, discount)
            return {
                "status": "PENDING_REPLY",
                "message": msg_obj["message"],
                "discount_offered": discount,
                "expires_at": msg_obj["expires_at"],
            }

    elif req.action == "reply":
        reply = req.reply_text or ""
        result = handle_reply(reply, req.flow_type)
        new_status = result["new_status"].upper()

        if req.order_id:
            with db_engine.begin() as conn:
                if result["action"] == "confirm_order":
                    conn.execute(text("UPDATE orders SET final_status = 'CONFIRMED' WHERE order_id = :oid"), {"oid": req.order_id})
                elif result["action"] == "cancel_order":
                    conn.execute(text("UPDATE orders SET final_status = 'CUSTOMER_CANCELLED' WHERE order_id = :oid"), {"oid": req.order_id})
                elif result["action"] == "send_payment_link":
                    conn.execute(text("UPDATE orders SET final_status = 'CONVERTED_PREPAID', payment_method = 'PREPAID' WHERE order_id = :oid"), {"oid": req.order_id})

        return {
            "status": new_status,
            "action": result["action"],
            "response_message": result["response_message"],
        }

    elif req.action == "timeout":
        timeout_action = int(rules.get("timeout_action", 1))
        result = handle_timeout(req.flow_type, timeout_action)
        if req.order_id:
            with db_engine.begin() as conn:
                conn.execute(text("UPDATE orders SET final_status = 'AUTO_EXPIRED_24H' WHERE order_id = :oid"), {"oid": req.order_id})
        return {
            "status": "AUTO_EXPIRED_24H",
            "action": result["action"],
            "response_message": result["response_message"],
        }

    raise HTTPException(status_code=400, detail="Invalid action")


@app.post("/api/evaluate")
def evaluate_order(order: OrderInput):
    """
    Evaluate a COD order using historical learned patterns + LLM,
    and persist the order and decision to the database.
    """
    import json
    import random
    rules = _load_rules()
    pincode_stats = _get_pincode_stats(order.pincode)

    order_dict = order.model_dump()

    # Auto-generate Order ID if not provided
    if not order_dict.get("order_id"):
        order_dict["order_id"] = f"KT{random.randint(102500, 109999)}"

    # Automatically look up customer purchase and RTO history by phone number from database
    if order_dict.get("customer_prior_orders") is None or order_dict.get("customer_prior_rto") is None:
        db_prior_orders, db_prior_rto = _lookup_customer_history(order.phone)
        order_dict["customer_prior_orders"] = db_prior_orders
        order_dict["customer_prior_rto"] = db_prior_rto

    # LLM analysis for address/name quality
    llm_result = analyze_order_with_llm(order_dict)

    decision = make_decision(order_dict, pincode_stats, rules, llm_result)

    # Determine status
    if decision["decision"] == "ship":
        initial_status = "APPROVED_FOR_SHIPPING"
    elif decision["decision"] == "confirm":
        initial_status = "PENDING_CONFIRMATION"
    elif decision["decision"] == "nudge_prepaid":
        initial_status = "PENDING_PREPAID_NUDGE"
    else:
        initial_status = "HELD_RISK_CANCELLED"

    # Save to database
    with db_engine.begin() as conn:
        now_sql = "NOW()" if IS_POSTGRES else "CURRENT_TIMESTAMP"
        conn.execute(text(f"""
            INSERT INTO orders (
                order_id, order_datetime, customer_name, phone, address,
                city, state, pincode, order_value, items, num_items,
                customer_prior_orders, customer_prior_rto, utm_source,
                courier, payment_method, final_status
            ) VALUES (
                :order_id, {now_sql}, :customer_name, :phone, :address,
                :city, :state, :pincode, :order_value, 'Oytra Haircare Set', 1,
                :customer_prior_orders, :customer_prior_rto, 'new_order_ui',
                'Delhivery', 'COD', :final_status
            )
            ON CONFLICT (order_id) DO UPDATE SET
                order_datetime = {now_sql},
                customer_name = EXCLUDED.customer_name,
                phone = EXCLUDED.phone,
                address = EXCLUDED.address,
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                pincode = EXCLUDED.pincode,
                order_value = EXCLUDED.order_value,
                customer_prior_orders = EXCLUDED.customer_prior_orders,
                customer_prior_rto = EXCLUDED.customer_prior_rto,
                utm_source = 'new_order_ui',
                final_status = EXCLUDED.final_status
        """), {
            **order_dict,
            "final_status": initial_status,
        })

        if IS_POSTGRES:
            conn.execute(text("""
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
            """), {
                "order_id": order_dict["order_id"],
                "decision": decision["decision"],
                "risk_score": decision["risk_score"],
                "risk_category": decision["risk_category"],
                "reason": decision["reason"],
                "risk_factors": json.dumps(decision["risk_factors"]),
                "llm_used": decision["llm_used"],
                "llm_analysis": json.dumps(decision["llm_analysis"]) if decision["llm_analysis"] else None,
                "actual_status": initial_status,
            })
        else:
            conn.execute(text("""
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
            """), {
                "order_id": order_dict["order_id"],
                "decision": decision["decision"],
                "risk_score": decision["risk_score"],
                "risk_category": decision["risk_category"],
                "reason": decision["reason"],
                "risk_factors": json.dumps(decision["risk_factors"]),
                "llm_used": 1 if decision["llm_used"] else 0,
                "llm_analysis": json.dumps(decision["llm_analysis"]) if decision["llm_analysis"] else None,
                "actual_status": initial_status,
            })

    # WhatsApp message payload if applicable
    whatsapp = None
    if decision["decision"] == "confirm":
        whatsapp = create_confirmation_message(order_dict)
    elif decision["decision"] == "nudge_prepaid":
        discount = calculate_discount(order.order_value, rules)
        whatsapp = create_nudge_message(order_dict, discount)

    return {
        "order_id": order_dict["order_id"],
        "status": initial_status,
        **decision,
        "whatsapp": whatsapp,
    }


@app.get("/api/orders/{order_id}")
def get_order_detail(order_id: str):
    """Retrieve complete details, decision, and risk breakdown for a single order."""
    import json
    with db_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT o.order_id, o.order_datetime, o.customer_name, o.phone, o.address,
                   o.city, o.state, o.pincode, o.order_value, o.customer_prior_orders,
                   o.customer_prior_rto, o.final_status,
                   od.decision, od.risk_score, od.risk_category, od.reason, od.risk_factors,
                   od.llm_used, od.llm_analysis
            FROM orders o
            LEFT JOIN order_decisions od ON o.order_id = od.order_id
            WHERE o.order_id = :oid
        """), {"oid": order_id}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Order not found")

        risk_factors = row[16]
        if isinstance(risk_factors, str):
            try:
                risk_factors = json.loads(risk_factors)
            except:
                pass

        return {
            "order_id": row[0],
            "order_datetime": str(row[1]),
            "customer_name": row[2],
            "phone": row[3],
            "address": row[4],
            "city": row[5],
            "state": row[6],
            "pincode": row[7],
            "order_value": float(row[8] or 0),
            "customer_prior_orders": row[9],
            "customer_prior_rto": row[10],
            "final_status": row[11],
            "decision": row[12],
            "risk_score": float(row[13]) if row[13] is not None else None,
            "risk_category": row[14],
            "reason": row[15],
            "risk_factors": risk_factors,
            "llm_used": bool(row[17]),
        }


@app.post("/api/whatsapp/reply")
def process_whatsapp_reply(reply_data: WhatsAppReply):
    """Process a customer's WhatsApp reply."""
    # For the mock, we just process the reply logic
    # In a real system, this would look up the conversation in DB
    result = handle_reply(reply_data.reply, "confirmation")
    return {"order_id": reply_data.order_id, **result}


@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: str, data: StatusUpdateInput):
    """Manually update an order's status (e.g. DELIVERED, RTO, APPROVED_FOR_SHIPPING, etc.)."""
    status_upper = data.status.strip().upper()

    with db_engine.begin() as conn:
        result = conn.execute(
            text("UPDATE orders SET final_status = :status WHERE order_id = :oid"),
            {"status": status_upper, "oid": order_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Order not found")

        # Also update actual_status in order_decisions
        conn.execute(
            text("UPDATE order_decisions SET actual_status = :status WHERE order_id = :oid"),
            {"status": status_upper, "oid": order_id}
        )

    return {"order_id": order_id, "status": status_upper, "message": f"Status updated to {status_upper}"}


@app.get("/api/dashboard/metrics")
def get_dashboard_metrics(
    preset: str = "today",
    start_date: str | None = None,
    end_date: str | None = None,
):
    """
    Retrieve real-time founder executive metrics filtered strictly by order_datetime.
    Supports preset options: 'today', 'last7', 'last30', 'all', 'custom'.
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    effective_start = None
    effective_end = None

    if preset == "today":
        effective_start = today_str
        effective_end = today_str
    elif preset == "last7":
        effective_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        effective_end = today_str
    elif preset == "last30":
        effective_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        effective_end = today_str
    elif preset == "all":
        effective_start = None
        effective_end = None
    elif preset == "custom":
        effective_start = start_date
        effective_end = end_date or today_str
    else:
        effective_start = today_str
        effective_end = today_str

    params = {}
    where_clauses = []

    if effective_start:
        where_clauses.append("o.order_datetime >= :start_dt")
        params["start_dt"] = f"{effective_start} 00:00:00"
    if effective_end:
        where_clauses.append("o.order_datetime <= :end_dt")
        params["end_dt"] = f"{effective_end} 23:59:59.999999"

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT
            od.decision,
            od.risk_score,
            o.order_value,
            o.final_status,
            o.customer_prior_orders,
            o.customer_prior_rto,
            o.order_id,
            o.customer_name,
            o.order_datetime,
            o.city,
            o.state,
            o.payment_method,
            o.utm_source,
            od.reason
        FROM orders o
        JOIN order_decisions od ON o.order_id = od.order_id
        {where_sql}
        ORDER BY o.order_datetime DESC
    """

    with db_engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    total_orders = len(rows)
    total_value = sum(float(r[2] or 0) for r in rows)

    counts = {"ship": 0, "confirm": 0, "nudge_prepaid": 0, "cancel": 0}
    values = {"ship": 0.0, "confirm": 0.0, "nudge_prepaid": 0.0, "cancel": 0.0}

    delivered_orders = 0
    delivered_value = 0.0
    delivered_margin = 0.0

    incurred_rtos = 0
    incurred_rto_cost = 0.0

    avoided_rtos = 0
    false_cancels = 0
    false_cancel_margin_loss = 0.0
    prepaid_conversions = 0

    orders_list = []
    for r in rows:
        dec = r[0] or "ship"
        score = float(r[1]) if r[1] is not None else 0.0
        val = float(r[2] or 0)
        status = r[3] or ""
        oid = r[6]
        cname = r[7]
        odt = str(r[8])
        city = r[9]
        state = r[10]
        pay_method = r[11]
        utm = r[12]
        reason = r[13]

        if dec in counts:
            counts[dec] += 1
            values[dec] += val

        # Status outcomes: DELIVERED vs RTO vs Pending
        if status == "DELIVERED":
            delivered_orders += 1
            delivered_value += val
            delivered_margin += val * GROSS_MARGIN_RATE
        elif status == "RTO":
            incurred_rtos += 1
            incurred_rto_cost += RTO_COST_PER_ORDER

        # RTO Avoidance & False Cancels logic
        if dec == "cancel":
            if status == "DELIVERED":
                false_cancels += 1
                false_cancel_margin_loss += val * GROSS_MARGIN_RATE
            else:
                avoided_rtos += 1
        elif dec == "nudge_prepaid" and (status == "CONVERTED_PREPAID" or pay_method == "PREPAID"):
            prepaid_conversions += 1

        if len(orders_list) < 100:
            orders_list.append({
                "order_id": oid,
                "customer_name": cname,
                "order_datetime": odt,
                "city": city,
                "state": state,
                "order_value": val,
                "risk_score": score,
                "decision": dec,
                "status": status,
                "reason": reason,
            })

    # Financial Impact Calculations
    saved_from_avoided_rto = avoided_rtos * RTO_COST_PER_ORDER
    prepaid_conversion_savings = prepaid_conversions * 40.65
    total_losses = false_cancel_margin_loss + incurred_rto_cost
    net_impact = (delivered_margin + saved_from_avoided_rto + prepaid_conversion_savings) - total_losses

    pcts = {
        k: round(100.0 * counts[k] / max(total_orders, 1), 1)
        for k in counts
    }

    return {
        "filter": {
            "preset": preset,
            "start_date": effective_start,
            "end_date": effective_end,
            "date_display": (f"{effective_start} to {effective_end}" if effective_start != effective_end else effective_start) if effective_start else "All Time (1,988+ Historical)",
        },
        "total_orders": total_orders,
        "total_order_value": round(total_value, 2),
        "decisions_count": counts,
        "decisions_pct": pcts,
        "decisions_value": {k: round(v, 2) for k, v in values.items()},
        "financials": {
            "delivered_orders": delivered_orders,
            "delivered_value": round(delivered_value, 2),
            "delivered_margin": round(delivered_margin, 2),
            "avoided_rto_savings": round(saved_from_avoided_rto, 2),
            "incurred_rto_cost": round(incurred_rto_cost, 2),
            "false_cancel_margin_loss": round(false_cancel_margin_loss, 2),
            "total_losses": round(total_losses, 2),
            "prepaid_conversion_savings": round(prepaid_conversion_savings, 2),
            "net_financial_impact": round(net_impact, 2),
        },
        "outcomes": {
            "delivered_orders": delivered_orders,
            "incurred_rtos": incurred_rtos,
            "avoided_rtos": avoided_rtos,
            "false_cancellations": false_cancels,
            "prepaid_conversions": prepaid_conversions,
        },
        "orders": orders_list,
    }


@app.get("/api/backtest")
def get_backtest():
    """Run backtest against historical data."""
    results = run_backtest()
    if not results:
        raise HTTPException(status_code=404, detail="No decisions found. Run the engine first.")
    return results


@app.get("/api/rules")
def get_rules():
    """Get all configurable decision rules."""
    rules = _load_rules()
    with db_engine.connect() as conn:
        rows = conn.execute(
            text("SELECT rule_key, rule_value, description, category FROM decision_rules ORDER BY category, rule_key")
        ).fetchall()
    return [{"key": r[0], "value": float(r[1]), "description": r[2], "category": r[3]} for r in rows]


@app.put("/api/rules/{rule_key}")
def update_rule(rule_key: str, new_value: float):
    """Update a decision rule threshold."""
    with db_engine.begin() as conn:
        result = conn.execute(
            text("UPDATE decision_rules SET rule_value = :v, updated_at = NOW() WHERE rule_key = :k"),
            {"v": new_value, "k": rule_key},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_key}' not found")
    return {"rule_key": rule_key, "new_value": new_value, "status": "updated"}


@app.get("/api/stats/overview")
def get_overview():
    """Get overall order statistics."""
    with db_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        cod = conn.execute(text("SELECT COUNT(*) FROM orders WHERE payment_method = 'COD'")).scalar()
        rto = conn.execute(text("SELECT COUNT(*) FROM orders WHERE final_status = 'RTO'")).scalar()
        avg_val = conn.execute(text("SELECT ROUND(AVG(order_value), 2) FROM orders")).scalar()

    return {
        "total_orders": total,
        "cod_orders": cod,
        "rto_orders": rto,
        "rto_rate": round(100 * rto / max(cod, 1), 1),
        "avg_order_value": float(avg_val or 0),
    }
