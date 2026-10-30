"""LLM-based analysis for address quality and name validation using Gemini."""

import json
import os
from src.config import GEMINI_API_KEY


def analyze_order_with_llm(order: dict) -> dict | None:
    """
    Use Gemini to analyze customer name and address quality.

    Only called when rule-based scoring flags potential issues,
    or for first-time buyers with no history.

    Returns:
        Dict with: name_suspicious, address_incomplete, address_gibberish, explanation
        None if LLM is unavailable or fails.
    """
    if not GEMINI_API_KEY:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""You are an order fraud detection assistant for an Indian D2C e-commerce brand.
Analyze this COD order and check for suspicious patterns.

Customer Name: {order.get('customer_name', 'N/A')}
Phone: {order.get('phone', 'N/A')}
Address: {order.get('address', 'N/A')}
City: {order.get('city', 'N/A')}
State: {order.get('state', 'N/A')}
Pincode: {order.get('pincode', 'N/A')}

Check these things:
1. Is the customer name suspicious? (e.g., "asdf", "test", "xyz", keyboard mashing, single character, clearly fake)
2. Is the address incomplete? (e.g., missing house number, no locality, just a city name)
3. Is the address gibberish or nonsensical? (Note: Hinglish addresses like "Station chowk se left, Hanuman Mandir ke saamne" are VALID Indian addresses)
4. Does the city/state/pincode combination make sense?

Respond ONLY with this JSON (no markdown, no extra text):
{{
  "name_suspicious": true/false,
  "address_incomplete": true/false,
  "address_gibberish": true/false,
  "city_state_mismatch": true/false,
  "explanation": "Brief explanation of any flags"
}}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        # Parse response
        text = response.text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        result = json.loads(text)
        return result

    except Exception as e:
        print(f"⚠️  LLM analysis failed: {e}")
        return None
