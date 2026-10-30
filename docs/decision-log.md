# Decision Log: Oytra COD RTO Risk Management

A running list of important architectural, data, and business design choices made during development, what alternatives were considered, and why each choice was selected.

---

### 1. Decision Engine: Explainable Weighted Scoring vs. Black-Box ML Model
* **Choice:** Built a transparent 0–100 composite risk scoring engine using calibrated weights and configurable thresholds.
* **Alternatives Considered:**
  * *Black-Box Random Forest / XGBoost:* Higher initial AUC on training data, but completely opaque to an operations manager.
  * *Binary Logistic Regression:* Good probability output, but difficult for non-technical team members to adjust without code redeployment.
* **Why We Picked This:** The assignment explicitly emphasizes that *"an operations person should understand why the system made the decision"* and *"thresholds must be easy for a non-technical person to change without touching code"*. A 0–100 score where points map to identifiable operational factors (address quality, buyer history, pincode baseline, cart value) meets this requirement directly.

---

### 2. LLM Boundary: Specialized NLP vs. Simple Code/Math
* **Choice:** Used Gemini (`gemini-2.5-flash`) strictly for qualitative NLP tasks (distinguishing Hinglish landmark directions from lazy placeholder text like `"call me"` or `"asdf"`). All mathematical risk scoring, unit economics, thresholds, and customer history aggregations are handled in Python/SQL.
* **Alternatives Considered:**
  * *Passing the entire order JSON to an LLM to output "Ship or Cancel":* Expensive, high latency (~1.5s), non-deterministic, and prone to hallucinations on mathematical margin tradeoffs.
  * *Pure regex matching:* Breaks on colloquial Indian addresses like *"Station chowk se left, SBI ke saamne"*, which our data showed has a 72.4% delivery success rate.
* **Why We Picked This:** The prompt instructions explicitly state: *"Do not use an LLM for things simple code or maths can do better. Tell us where you drew that line and why."* Code handles numbers and rules; LLM handles human linguistic nuance.

---

### 3. Business Strategy: First-Time Buyer Protection Rule (Marketing Alignment)
* **Choice:** Implemented an automated guardrail (`first_order_protect = 1`): the system **never auto-cancels a first-time buyer** (`customer_prior_orders == 0`), even if their risk score crosses the cancel threshold. They are routed to **Nudge to Prepaid** (with a ₹40 discount) or **WhatsApp Confirmation**.
* **Alternatives Considered:**
  * *Blind Cancellation of all high-score orders:* Satisfies the Head of Operations, but destroys Marketing's ₹300+ Meta ad spend.
* **Why We Picked This:** A genuine customer delivers ₹402 in gross profit. Cancelling them loses ₹402 profit + ₹300 wasted CAC = ₹702 total loss. Absorbing an RTO only costs ₹169.40. Therefore, false cancellations are 4× more destructive than RTOs. Nudging them to prepaid allows them to confirm intent safely without incurring COD door refusal risk.

---

### 4. Financial Economics: Capping Prepaid Nudge Discount at ₹40
* **Choice:** Offered a 10% discount capped strictly at **₹40** for customers who convert from COD to Prepaid via WhatsApp.
* **Alternatives Considered:**
  * *Offering ₹100 flat discount:* Strong conversion incentive, but wipes out 25% of gross profit margin.
  * *No discount (just a payment link):* Low conversion rate (~5%), as Indian buyers prefer COD for perceived safety.
* **Why We Picked This (The Math):**
  * Expected return cost on COD: $28\% \times ₹169.40 = ₹47.43$
  * Expected return cost on Prepaid: $4\% \times ₹169.40 = ₹6.78$
  * Gross logistics risk saved per conversion: $₹47.43 - ₹6.78 = ₹40.65$
  * By offering ₹40, Oytra captures almost the entire expected risk reduction while securing immediate cash flow and eliminating cash-at-door friction.

---

### 5. Pincode Intelligence: 5-Order Volume Threshold (Avoiding the Operations Blindspot)
* **Choice:** The engine only applies a pincode's historical RTO rate if that pincode has **at least 5 recorded orders** in our database (`pincode_min_orders = 5`). For sparse pincodes, the engine applies a regional baseline.
* **Alternatives Considered:**
  * *Banning COD in any pincode with high return history:* Head of Operations' proposal.
* **Why We Picked This:** Data analysis revealed that **over 82% of pincodes had only 1 or 2 past orders**. If a single package failed delivery in a remote pincode, its raw RTO rate was 100%. Blacklisting it would permanently cut off over 800 deliverable areas and waste Meta ad clicks.

---

### 6. Database: Dual Supabase PostgreSQL with Automated SQLite Failover
* **Choice:** Supported cloud-hosted Supabase PostgreSQL (`orders`, `order_decisions`, `pincode_stats`, `decision_rules`) with automatic local SQLite fallback (`orders.db`).
* **Alternatives Considered:**
  * *PostgreSQL only:* If remote database credentials have connection or network latency issues, the application crashes and the assignment cannot be reviewed.
  * *SQLite only:* Doesn't demonstrate production relational modeling or cloud database integration.
* **Why We Picked This:** Satisfies the reviewer requirement to *"run it in under 10 minutes"* without setup friction, while maintaining full PostgreSQL production fidelity.

---

### 7. Frontend Architecture: Interactive SPA vs. Swagger / Streamlit
* **Choice:** Built a responsive single-page application using modern HTML5, Tailwind CSS, Lucide icons, and Vanilla JavaScript with no build step, featuring a tabbed workflow (Create Order, Created Orders with live status dropdown, Founder Dashboard with custom date filter, Rules & Thresholds).
* **Alternatives Considered:**
  * *Swagger / OpenAPI UI only:* Functional for APIs, but fails to provide a real interactive experience for testing WhatsApp flows or founder executive metrics.
  * *Streamlit:* Quick to build, but re-renders the whole page on every state update, breaking interactive WhatsApp chat simulation.
* **Why We Picked This:** Offers a clean, realistic operations and founder experience where live WhatsApp replies update the database in real time.
