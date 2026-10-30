"""Rule-based risk scoring engine — no LLM, pure code/math."""


def calculate_risk_score(order: dict, pincode_stats: dict, rules: dict) -> dict:
    """
    Calculate a 0-100 risk score for a COD order.

    Args:
        order: Order data dict with keys matching CSV columns.
        pincode_stats: Dict with pincode-level stats {rto_rate, total_orders, risk_reliable}.
        rules: Dict of decision_rules {rule_key: rule_value}.

    Returns:
        Dict with risk_score, risk_factors breakdown, and risk_category.
    """
    factors = {}
    total_score = 0.0

    # --- Factor 1: Pincode RTO Rate ---
    max_pincode_pts = rules.get("weight_pincode_rto", 25)
    min_orders = rules.get("pincode_min_orders", 5)

    if pincode_stats and pincode_stats.get("risk_reliable", False):
        pincode_rto = pincode_stats.get("rto_rate", 0)
        # Scale: 0% RTO → 0 pts, 50%+ RTO → max pts
        pincode_score = min(max_pincode_pts, (pincode_rto / 50.0) * max_pincode_pts)
        factors["pincode_rto_rate"] = round(pincode_rto, 2)
        factors["pincode_rto_score"] = round(pincode_score, 2)
    else:
        # Not enough data — use moderate default
        pincode_score = max_pincode_pts * 0.3
        factors["pincode_rto_rate"] = None
        factors["pincode_rto_score"] = round(pincode_score, 2)
        factors["pincode_note"] = "Insufficient data, using default"

    total_score += pincode_score

    # --- Factor 2: Customer RTO History ---
    max_rto_pts = rules.get("weight_prior_rto", 35)
    prior_orders = order.get("customer_prior_orders", 0) or 0
    prior_rto = order.get("customer_prior_rto", 0) or 0

    if prior_orders > 0:
        if prior_rto >= 2:
            rto_score = max_rto_pts  # Very high risk: 76.5% historical RTO rate
        elif prior_rto == 1:
            rto_score = max_rto_pts * 0.55  # Elevated risk: 35.2% RTO rate
        else:
            rto_score = 0.0  # Proven good customer!
        factors["prior_orders"] = prior_orders
        factors["prior_rto"] = prior_rto
        factors["rto_ratio"] = round(prior_rto / prior_orders, 2)
        factors["rto_history_score"] = round(rto_score, 2)
    else:
        # First-time buyer — add modest uncertainty risk
        first_order_pts = rules.get("weight_first_order", 12)
        rto_score = first_order_pts
        factors["first_time_buyer"] = True
        factors["rto_history_score"] = round(rto_score, 2)

    total_score += rto_score

    # --- Factor 3: Address Quality (Rule-based) ---
    address_str = str(order.get("address", "")).strip().lower()
    address_score = 0.0
    if len(address_str) < 15 or address_str in ["xyz", "call me", "test", "delhi", "near station"]:
        address_score = 30.0  # 61.7% historical RTO rate on short addresses
        factors["short_or_incomplete_address"] = True
    elif len(address_str.split()) <= 2:
        address_score = 15.0
        factors["sparse_address"] = True
    factors["address_risk_score"] = round(address_score, 2)
    total_score += address_score

    # --- Factor 4: Customer Name Check (Rule-based) ---
    name_str = str(order.get("customer_name", "")).strip().lower()
    name_score = 0.0
    if any(fake in name_str for fake in ["test", "asdf", "dummy", "fake", "sample"]):
        name_score = 30.0
        factors["suspicious_name"] = True
    factors["name_risk_score"] = round(name_score, 2)
    total_score += name_score

    # --- Factor 5: Order Value Anomaly ---
    max_value_pts = rules.get("weight_order_value", 10)
    order_value = float(order.get("order_value", 0) or 0)
    avg_value = 649.0

    if order_value > 0:
        value_ratio = order_value / avg_value
        if value_ratio > 2.2:
            value_score = max_value_pts
        elif value_ratio > 1.6:
            value_score = max_value_pts * 0.5
        else:
            value_score = 0.0
        factors["order_value"] = float(order_value)
        factors["value_ratio"] = round(value_ratio, 2)
        factors["value_score"] = round(value_score, 2)
    else:
        value_score = max_value_pts
        factors["value_score"] = round(value_score, 2)

    total_score += value_score

    # Clamp to 0-100 (LLM score will be added separately)
    total_score = min(100, max(0, total_score))

    # Determine risk category based on thresholds
    ship_max = rules.get("ship_max_score", 30)
    confirm_max = rules.get("confirm_max_score", 55)
    nudge_max = rules.get("nudge_max_score", 75)

    if total_score <= ship_max:
        category = "low"
    elif total_score <= confirm_max:
        category = "medium"
    elif total_score <= nudge_max:
        category = "high"
    else:
        category = "very_high"

    return {
        "risk_score": round(total_score, 2),
        "risk_category": category,
        "risk_factors": factors,
    }
