"""Tests for the risk scoring engine."""

import pytest
from src.engine.risk_scorer import calculate_risk_score


DEFAULT_RULES = {
    "ship_max_score": 30,
    "confirm_max_score": 50,
    "nudge_max_score": 70,
    "weight_pincode_rto": 25,
    "weight_prior_rto": 40,
    "weight_first_order": 12,
    "weight_order_value": 10,
    "weight_llm_flags": 25,
    "pincode_min_orders": 5,
}


def test_low_risk_returning_customer():
    """A customer with good history, valid address and safe pincode should be low risk."""
    order = {
        "customer_name": "Pooja Sharma",
        "address": "Flat 402, Sunshine Apartments, Indiranagar",
        "customer_prior_orders": 5,
        "customer_prior_rto": 0,
        "order_value": 649,
    }
    pincode = {"rto_rate": 10, "total_orders": 20, "risk_reliable": True}
    result = calculate_risk_score(order, pincode, DEFAULT_RULES)
    assert result["risk_category"] == "low"
    assert result["risk_score"] <= 30


def test_high_risk_repeat_offender():
    """A customer with many RTOs should be high risk."""
    order = {
        "customer_name": "Vikram Singh",
        "address": "Flat 101, Lake View, MG Road",
        "customer_prior_orders": 5,
        "customer_prior_rto": 4,
        "order_value": 649,
    }
    pincode = {"rto_rate": 40, "total_orders": 30, "risk_reliable": True}
    result = calculate_risk_score(order, pincode, DEFAULT_RULES)
    assert result["risk_score"] > 55


def test_first_time_buyer_moderate_risk():
    """First-time buyer should get moderate risk, not zero."""
    order = {
        "customer_name": "Ananya Joshi",
        "address": "Plot 14, Sector 18, Noida",
        "customer_prior_orders": 0,
        "customer_prior_rto": 0,
        "order_value": 649,
    }
    pincode = {"rto_rate": 15, "total_orders": 10, "risk_reliable": True}
    result = calculate_risk_score(order, pincode, DEFAULT_RULES)
    assert result["risk_factors"].get("first_time_buyer") is True
    assert result["risk_score"] > 0


def test_incomplete_address_flagged():
    """Incomplete address like 'xyz' should get high address risk."""
    order = {
        "customer_name": "Deepika Yadav",
        "address": "xyz",
        "customer_prior_orders": 0,
        "customer_prior_rto": 0,
        "order_value": 649,
    }
    pincode = {"rto_rate": 20, "total_orders": 10, "risk_reliable": True}
    result = calculate_risk_score(order, pincode, DEFAULT_RULES)
    assert result["risk_factors"].get("short_or_incomplete_address") is True
    assert result["risk_score"] >= 40
