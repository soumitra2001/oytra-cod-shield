"""WhatsApp confirmation and nudge-to-prepaid flow logic."""

import json
from datetime import datetime, timedelta, timezone


def create_confirmation_message(order: dict) -> dict:
    """Generate the WhatsApp confirmation message for an order."""
    name = order.get("customer_name", "Customer").split()[0]
    order_id = order.get("order_id", "N/A")
    value = order.get("order_value", 0)

    message = (
        f"Hi {name}! 👋\n\n"
        f"Thank you for your order #{order_id}.\n\n"
        f"Your order worth ₹{value} is placed as Cash on Delivery.\n\n"
        f"Please confirm if you'd like us to deliver your order.\n\n"
        f"Reply *YES* to confirm or *NO* to cancel."
    )

    return {
        "flow_type": "confirmation",
        "message": message,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }


def create_nudge_message(order: dict, discount_amount: float) -> dict:
    """Generate the WhatsApp nudge-to-prepaid message."""
    name = order.get("customer_name", "Customer").split()[0]
    order_id = order.get("order_id", "N/A")
    value = order.get("order_value", 0)
    pay_amount = value - discount_amount

    message = (
        f"Hi {name}! 👋\n\n"
        f"Your order #{order_id} is ready!\n\n"
        f"💰 Pay online and enjoy ₹{int(discount_amount)} OFF on your order.\n\n"
        f"Original amount: ₹{value}\n"
        f"Discount: ₹{int(discount_amount)}\n"
        f"*Pay only ₹{int(pay_amount)}!*\n\n"
        f"Reply *YES* to get the payment link or *NO* to continue with COD."
    )

    return {
        "flow_type": "nudge_prepaid",
        "message": message,
        "discount_offered": discount_amount,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }


def calculate_discount(order_value: float, rules: dict) -> float:
    """Calculate the prepaid discount amount."""
    pct = rules.get("prepaid_discount_pct", 10)
    max_disc = rules.get("max_prepaid_discount", 40)
    discount = min(order_value * (pct / 100), max_disc)
    return round(discount, 2)


def handle_reply(reply: str, flow_type: str) -> dict:
    """
    Process a customer's WhatsApp reply.

    Returns:
        Dict with: action, response_message, new_status
    """
    reply = reply.strip().lower()
    words = set(reply.replace(",", " ").replace(".", " ").replace("!", " ").split())

    is_affirmative = (
        bool(words.intersection({"yes", "y", "ha", "haan", "han", "ok", "okay", "confirm", "pls"}))
        or "bhej do" in reply
        or "bhejo" in reply
        or "deliver" in reply
    )

    is_negative = (
        bool(words.intersection({"no", "n", "nahi", "nhi", "cancel"}))
        or "mat bhejo" in reply
        or "don't" in reply
        or "dont" in reply
    )

    if is_affirmative and not is_negative:
        if flow_type == "confirmation":
            return {
                "action": "confirm_order",
                "new_status": "confirmed",
                "response_message": "Thank you! ✅ Your order is confirmed and will be shipped shortly.",
            }
        else:  # nudge_prepaid
            return {
                "action": "send_payment_link",
                "new_status": "converted_prepaid",
                "response_message": (
                    "Great choice! 🎉\n\n"
                    "Here's your secure payment link:\n"
                    "🔗 https://pay.oytra.com/order/XXXXX\n\n"
                    "Complete the payment to lock in your discount!"
                ),
            }

    elif is_negative and not is_affirmative:
        if flow_type == "confirmation":
            return {
                "action": "cancel_order",
                "new_status": "rejected",
                "response_message": "Your order has been cancelled. If you change your mind, you can place a new order on our website. 🙏",
            }
        else:  # nudge_prepaid — fall back to COD confirmation
            return {
                "action": "fallback_cod_confirm",
                "new_status": "pending",
                "response_message": (
                    "No worries! Your order will continue as Cash on Delivery.\n\n"
                    "Please confirm you'd like us to deliver it.\n"
                    "Reply *YES* to confirm or *NO* to cancel."
                ),
            }

    else:
        # Random / unclear reply
        return {
            "action": "ask_again",
            "new_status": "awaiting_clarification",
            "response_message": "Sorry, I didn't understand that. 🤔\n\nPlease reply *YES* or *NO*.",
        }


def handle_timeout(flow_type: str, timeout_action: int) -> dict:
    """Handle 24-hour timeout with no reply."""
    if timeout_action == 1:
        return {
            "action": "cancel_order",
            "new_status": "expired",
            "response_message": "Your order has been cancelled as we didn't receive a response within 24 hours. You can place a new order anytime. 🙏",
        }
    else:
        return {
            "action": "hold_order",
            "new_status": "expired",
            "response_message": "Your order is on hold. Please contact us to proceed. 🙏",
        }
