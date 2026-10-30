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
    """Generate a clear, transparent plain-English explanation of why this order received this risk score."""
    name = order.get("customer_name", "Customer")
    addr = order.get("address", "")
    pincode = str(order.get("pincode", "N/A")).replace(".0", "")

    # 1. State clear score and safe vs risky classification
    if score <= 30:
        tier_text = f"Risk Score is {score:.1f}/100 — SAFE (Low Risk, 0-30 threshold). Safe to ship directly without customer friction."
    elif score <= 60:
        tier_text = f"Risk Score is {score:.1f}/100 — MODERATELY RISKY (Medium Risk, 31-60 threshold). Risky to ship directly; requires WhatsApp intent & address confirmation."
    elif score <= 80:
        tier_text = f"Risk Score is {score:.1f}/100 — HIGH RISK (61-80 threshold). High return likelihood; requires ₹40 prepaid discount conversion nudge."
    else:
        tier_text = f"Risk Score is {score:.1f}/100 — SEVERE RISK (81-100 threshold). Very high return probability; recommended for hold or cancellation."

    points_breakdown = []

    # 2. Address evaluation
    if factors.get("short_or_incomplete_address"):
        pts = factors.get("address_risk_score", 20.0)
        points_breakdown.append(f"Incomplete address '{addr}' missing flat/house/building details (+{pts:.0f} pts)")
    elif factors.get("sparse_address"):
        pts = factors.get("address_risk_score", 15.0)
        points_breakdown.append(f"Address '{addr}' lacks specific building details (+{pts:.0f} pts)")
    else:
        points_breakdown.append("Address is complete with building/house specifics (0 pts)")

    # 3. Customer purchase and RTO history
    if factors.get("first_time_buyer"):
        pts = factors.get("rto_history_score", 12.0)
        points_breakdown.append(f"First-time buyer with no verified delivery history (+{pts:.0f} pts)")
    elif factors.get("prior_orders", 0) > 0:
        prior_o = factors.get("prior_orders", 0)
        prior_r = factors.get("prior_rto", 0)
        if prior_r >= 2:
            points_breakdown.append(f"Serial returner with {prior_r} RTO returns out of {prior_o} prior orders (+40 pts)")
        elif prior_r == 1:
            points_breakdown.append(f"Prior return history of 1 RTO out of {prior_o} orders (+19 pts)")
        else:
            points_breakdown.append(f"Trusted buyer with {prior_o} successful deliveries and zero returns (0 pts)")

    # 4. Pincode regional risk
    if factors.get("pincode_rto_rate") is not None:
        p_rate = factors["pincode_rto_rate"]
        p_pts = factors.get("pincode_rto_score", 0)
        points_breakdown.append(f"Pincode {pincode} has a historical RTO rate of {p_rate}% (+{p_pts:.1f} pts)")
    elif factors.get("pincode_note"):
        p_pts = factors.get("pincode_rto_score", 7.5)
        points_breakdown.append(f"Pincode {pincode} regional baseline rate (+{p_pts:.1f} pts)")

    # 5. Cart value / name anomaly
    if factors.get("value_score") and factors.get("value_score") > 0:
        points_breakdown.append(f"High cart exposure above average order value (+{factors['value_score']:.0f} pts)")
    if factors.get("name_suspicious"):
        points_breakdown.append("Suspicious customer name detected (+30 pts)")

    factors_str = "; ".join(points_breakdown)
    return f"{tier_text} Contributing factors: {factors_str}."
