"""Main decision engine — combines risk scorer + LLM analysis → final decision."""

from src.engine.risk_scorer import calculate_risk_score


def make_decision(order: dict, pincode_stats: dict, rules: dict, llm_result: dict | None = None) -> dict:
    """
    Evaluate a COD order and return a decision with explanation.

    Returns:
        Dict with: decision, risk_score, risk_category, reason, risk_factors, llm_used
    """
    # Step 1: Calculate base risk score (code/math)
    risk = calculate_risk_score(order, pincode_stats, rules)
    score = risk["risk_score"]
    factors = risk["risk_factors"]

    # Step 2: Add LLM analysis if available
    llm_used = False
    llm_score = 0
    max_llm_pts = rules.get("weight_llm_flags", 25)

    if llm_result:
        llm_used = True
        # LLM flags: name_suspicious, address_incomplete, address_gibberish
        if llm_result.get("name_suspicious", False):
            llm_score += max_llm_pts * 0.5
            factors["name_suspicious"] = True
        if llm_result.get("address_incomplete", False):
            llm_score += max_llm_pts * 0.3
            factors["address_incomplete"] = True
        if llm_result.get("address_gibberish", False):
            llm_score += max_llm_pts * 0.5
            factors["address_gibberish"] = True

        llm_score = min(max_llm_pts, llm_score)
        factors["llm_score"] = round(llm_score, 2)
        factors["llm_details"] = llm_result

    score = min(100, score + llm_score)

    # Step 3: Map score to decision
    ship_max = rules.get("ship_max_score", 30)
    confirm_max = rules.get("confirm_max_score", 55)
    nudge_max = rules.get("nudge_max_score", 75)
    protect_first = rules.get("first_order_protect", 1)

    if score <= ship_max:
        decision = "ship"
        category = "low"
    elif score <= confirm_max:
        decision = "confirm"
        category = "medium"
    elif score <= nudge_max:
        decision = "nudge_prepaid"
        category = "high"
    else:
        decision = "cancel"
        category = "very_high"

    # Business rule: protect first-time buyers from auto-cancel
    is_first_time = order.get("customer_prior_orders", 0) == 0
    if decision == "cancel" and is_first_time and protect_first:
        decision = "nudge_prepaid"
        factors["first_order_protected"] = True

    # Step 4: Generate plain-English reason
    reason = _generate_reason(order, decision, score, factors)

    return {
        "decision": decision,
        "risk_score": round(score, 2),
        "risk_category": category,
        "reason": reason,
        "risk_factors": factors,
        "llm_used": llm_used,
        "llm_analysis": llm_result,
    }


def _generate_reason(order: dict, decision: str, score: float, factors: dict) -> str:
    """Generate a plain-English reason for the decision."""
    name = order.get("customer_name", "Customer")
    parts = []

    if decision == "ship":
        parts.append(f"Order looks safe (risk score: {score}/100).")
        if factors.get("prior_orders", 0) > 0 and factors.get("prior_rto", 0) == 0:
            parts.append(f"{name} has {factors['prior_orders']} prior orders with no returns.")
        if factors.get("pincode_rto_rate") is not None and factors["pincode_rto_rate"] < 20:
            parts.append(f"Pincode {order.get('pincode', 'N/A')} has a low RTO rate ({factors['pincode_rto_rate']}%).")

    elif decision == "confirm":
        parts.append(f"Order needs confirmation (risk score: {score}/100).")
        if factors.get("first_time_buyer"):
            parts.append(f"{name} is a first-time buyer — confirm via WhatsApp before shipping.")
        if factors.get("pincode_rto_rate") is not None and factors["pincode_rto_rate"] > 25:
            parts.append(f"Pincode {order.get('pincode', 'N/A')} has an elevated RTO rate ({factors['pincode_rto_rate']}%).")

    elif decision == "nudge_prepaid":
        parts.append(f"Recommend converting to prepaid (risk score: {score}/100).")
        if factors.get("first_order_protected"):
            parts.append(f"{name} is a first-time buyer — nudging to prepaid instead of cancelling to protect acquisition cost.")
        if factors.get("rto_ratio", 0) > 0.3:
            parts.append(f"{name} has a {int(factors['rto_ratio'] * 100)}% return rate on past orders.")

    elif decision == "cancel":
        parts.append(f"High risk — hold/cancel this order (risk score: {score}/100).")
        if factors.get("rto_ratio", 0) > 0.5:
            parts.append(f"{name} has returned {factors.get('prior_rto', 0)} of {factors.get('prior_orders', 0)} prior orders.")
        if factors.get("name_suspicious"):
            parts.append("Customer name appears suspicious or fake.")
        if factors.get("address_gibberish"):
            parts.append("Delivery address appears incomplete or gibberish.")

    return " ".join(parts)
