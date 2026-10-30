# AI Usage Log: Oytra COD RTO Risk Management

A transparent log detailing which AI tools were used during development, what tasks they handled, and specific examples where the AI produced incorrect, suboptimal, or broken code and how those issues were caught and corrected.

---

### AI Tools Used

| Tool | Primary Purpose in Project |
| :--- | :--- |
| **Google Gemini (`gemini-2.5-flash`)** | Integrated inside the production application to analyze customer delivery addresses for completeness, detect placeholder names, and interpret colloquial Hinglish directions. |
| **Antigravity AI Agent** | Initial codebase scaffolding, boilerplate API routing, writing database seed scripts, and frontend component layout. |

---

### Real Examples of AI Errors, Hallucinations, and How They Were Fixed

#### Example 1: PostgreSQL-Specific Boolean Cast Failure (`psycopg2.errors.DatatypeMismatch`)
* **What the AI Generated:**
  In `src/db/import_csv.py`, the AI generated SQL aggregation to populate `pincode_stats`:
  ```sql
  INSERT INTO pincode_stats (pincode, total_orders, ..., risk_reliable)
  SELECT pincode, ...,
      CASE WHEN COUNT(*) >= 5 THEN 1 ELSE 0 END AS risk_reliable
  FROM orders GROUP BY pincode;
  ```
* **What Went Wrong:**
  When executing against the Supabase PostgreSQL database, the script crashed with:
  `psycopg2.errors.DatatypeMismatch: column "risk_reliable" is of type boolean but expression is of type integer. LINE 13: CASE WHEN COUNT(*) >= 5 THEN 1 ELSE 0 END`.
  The AI had written SQLite-compatible integer booleans (`1 / 0`) instead of PostgreSQL strict booleans (`TRUE / FALSE`).
* **How I Caught & Fixed It:**
  Caught via the terminal stack trace during `python scripts/setup_db.py`. I refactored the SQL expression to `CASE WHEN COUNT(*) >= 5 THEN TRUE ELSE FALSE END` and added a dialect checker (`IS_POSTGRES`) in `src/config.py` to ensure all queries execute cleanly across both PostgreSQL and SQLite.

---

#### Example 2: Calling a Deprecated Gemini Model Endpoint (HTTP 404 NOT_FOUND)
* **What the AI Generated:**
  In `src/engine/llm_analyzer.py`, the AI configured the Google GenAI SDK using an outdated model string:
  ```python
  model = "gemini-2.0-flash"
  ```
* **What Went Wrong:**
  During live order evaluation, the API returned:
  `google.genai.errors.ClientError: 404 NOT_FOUND: models/gemini-2.0-flash is not found for API version v1beta`.
  The AI had referenced an experimental/deprecated preview endpoint that was no longer active.
* **How I Caught & Fixed It:**
  Tested the endpoint using `POST /api/evaluate` and caught the 404 in the uvicorn logs. Upgraded the SDK call to the stable `gemini-2.5-flash` model, and added an automated fallback wrapper with `try...except` so that if the Gemini API ever experiences rate limits (429) or network outages, the system automatically falls back to heuristic rule scoring without failing the user's order submission.

---

#### Example 3: Naive Pincode Risk Scoring Without Volume Thresholding (The Sparsity Trap)
* **What the AI Generated:**
  In the initial risk scorer, the AI scored location risk directly from raw pincode return rates:
  ```python
  pincode_risk_points = (pincode_rto_rate / 100.0) * max_pincode_weight
  ```
* **What Went Wrong:**
  When inspecting the 1,988 CSV rows with Pandas, I found that **over 82% of pincodes had only 1 or 2 total orders**. If a single order in a remote pincode had returned, its raw RTO rate was 100%, causing the AI to assign maximum risk (+25 pts) to viable delivery zones. This blindly validated the Head of Operations' flawed assumption and would have permanently blacklisted hundreds of postal codes.
* **How I Caught & Fixed It:**
  Caught by analyzing pincode frequency distributions. I introduced a mandatory volume gate: `pincode_min_orders = 5`. Pincodes with fewer than 5 orders are marked `risk_reliable = False` and receive a balanced regional baseline score (+7.5 pts) rather than an unfair penalty.

---

#### Example 4: Address Heuristic Failure on Incomplete Single-Entity Addresses
* **What the AI Generated:**
  The AI wrote address validation regex looking only for word count and string length:
  `if len(address) > 15 and len(address.split()) >= 3: address_score = 0.0`.
* **What Went Wrong:**
  When testing with realistic Indian addresses like `"DLF Apartment, 560076"` or `"SNN Raj, 560076"`, the length was >15 characters, so the AI gave it **0 risk points** (marking it Low Risk / Ship As-Is at 19.5/100). However, courier delivery agents cannot deliver a package without a flat, floor, or house number. Incomplete addresses like this have a 61.7% return rate in our dataset.
* **How I Caught & Fixed It:**
  Caught by manually submitting test orders in the UI. I refined the address heuristic and Gemini prompt to explicitly check for house/flat/building/door numbers (`re.search(r'\d+', address)` or building keywords), properly adding +20 risk points and moving the order into the **WhatsApp Confirmation** tier before courier dispatch.
