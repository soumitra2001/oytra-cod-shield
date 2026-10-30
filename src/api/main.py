"""FastAPI backend — decision engine API endpoints."""

import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import get_db, engine as db_engine
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
    order_id: str
    customer_name: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    order_value: float
    items: str = ""
    num_items: int = 1
    customer_prior_orders: int = 0
    customer_prior_rto: int = 0
    utm_source: str = ""
    payment_method: str = "COD"


class WhatsAppReply(BaseModel):
    order_id: str
    reply: str


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


@app.post("/api/evaluate")
def evaluate_order(order: OrderInput):
    """Evaluate a single COD order and return the decision."""
    rules = _load_rules()
    pincode_stats = _get_pincode_stats(order.pincode)

    order_dict = order.model_dump()

    # LLM analysis (only if API key is set)
    llm_result = analyze_order_with_llm(order_dict)

    decision = make_decision(order_dict, pincode_stats, rules, llm_result)

    # Generate WhatsApp message if needed
    whatsapp = None
    if decision["decision"] == "confirm":
        whatsapp = create_confirmation_message(order_dict)
    elif decision["decision"] == "nudge_prepaid":
        discount = calculate_discount(order.order_value, rules)
        whatsapp = create_nudge_message(order_dict, discount)

    return {
        "order_id": order.order_id,
        **decision,
        "whatsapp": whatsapp,
    }


@app.post("/api/whatsapp/reply")
def process_whatsapp_reply(reply_data: WhatsAppReply):
    """Process a customer's WhatsApp reply."""
    # For the mock, we just process the reply logic
    # In a real system, this would look up the conversation in DB
    result = handle_reply(reply_data.reply, "confirmation")
    return {"order_id": reply_data.order_id, **result}


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
