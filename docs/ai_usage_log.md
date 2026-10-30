# AI Usage Log

Which AI tools were used, for what, and corrections made.

---

## Tools Used

| Tool | Purpose |
|------|---------|
| Google Gemini (in the app) | Address validation, fake name detection |
| ChatGPT | Assignment understanding, approach planning |
| Antigravity (Claude) | Project scaffolding, code generation, debugging |

---

## Examples of AI Corrections

### Example 1: PostgreSQL-Specific Syntax Causing Failures on SQLite
- **What AI suggested:** Initially wrote PostgreSQL-specific syntax (`COUNT(*) FILTER (WHERE final_status = 'RTO')` and `CAST(:risk_factors AS jsonb)`) in shared database scripts.
- **What was wrong:** When running on local development or test environments using SQLite, these statements failed with syntax errors because SQLite does not support `FILTER` or `jsonb`.
- **How I fixed it:** Refactored SQL statements to ANSI-compliant `SUM(CASE WHEN final_status = 'RTO' THEN 1 ELSE 0 END)` and added a dialect checker (`IS_POSTGRES`) in `src/config.py` that selects the appropriate schema and JSON serialization strategy dynamically.

---

### Example 2: Assuming `orders_sample.csv` Had Unique `order_id` Values
- **What AI suggested:** A direct `df.to_sql("orders")` assuming that primary key constraints on `order_id` would succeed without pre-processing.
- **What was wrong:** The database threw `IntegrityError: UNIQUE constraint failed: orders.order_id`. Upon inspecting the CSV with Pandas, I found 60 duplicate rows (30 repeated `order_id`s like `KT100191`, `KT100317`), likely simulating duplicate Shopify webhook delivery.
- **How I fixed it:** Added an explicit deduplication stage in `src/db/import_csv.py` with `df.drop_duplicates(subset=['order_id'], keep='first')` and reported this as a valuable data finding in the Business Memo.

---

### Example 3: Naive Pincode Risk Scoring Without Volume Thresholding
- **What AI suggested:** Directly using `(pincode_rto_rate / 50.0) * weight` to score location risk.
- **What was wrong:** Over 82% of pincodes in the dataset have only 1 or 2 historical orders. If a single order returned, the raw RTO rate was 100%, causing the system to mistakenly classify entire pincodes as toxic. This would have validated the Head of Operations' flawed assumption and killed Marketing's customer acquisition.
- **How I fixed it:** Added a `pincode_min_orders` threshold ($\ge 5$). Sparse pincodes are flagged as `risk_reliable = False` and assigned a moderate prior baseline rather than a punitive penalty.

---
