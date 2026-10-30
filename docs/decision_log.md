# Decision Log

A running log of important design and implementation decisions.

---

## 1. Database: Supabase (PostgreSQL) over SQLite

**Decision:** Use Supabase-hosted PostgreSQL instead of SQLite.

**Alternatives considered:**
- SQLite: Simpler, zero setup, file-based
- Local PostgreSQL: More powerful but requires installation

**Why Supabase:** Anyone cloning the repo can connect to the shared database immediately without installing anything locally. The assignment says "run it in under 10 minutes" — removing DB setup friction helps.

**Trade-off:** Requires internet connection; credentials in .env.

---

## 2. Tech Stack: Python + FastAPI + Streamlit

**Decision:** Use Python ecosystem for everything.

**Alternatives considered:**
- Next.js + React: Better dashboard UX, but more frontend complexity
- Go + HTMX: Faster runtime, but worse ML/data ecosystem

**Why Python:** Best ecosystem for CSV analysis (Pandas), ML (Scikit-learn), LLM integration (Gemini SDK), and quick dashboards (Streamlit). The assignment prioritises business logic over frontend polish.

---

## 3. LLM Usage: Only for Name/Address Validation

**Decision:** Use Gemini only for detecting fake names and validating address quality. All math, scoring, and business rules use plain Python code.

**Why:** The assignment explicitly says "Do not use an LLM for things simple code or maths can do better." LLMs are good at understanding Hinglish addresses and spotting "asdf" names — that's where we use them.

---

## 4. Risk Scoring: Weighted Rule-Based System

**Decision:** Use a weighted scoring system (0-100) with configurable thresholds, rather than a black-box ML model.

**Alternatives considered:**
- Logistic Regression: More accurate but harder to explain
- Random Forest: Best accuracy but completely opaque

**Why rules:** The assignment requires that "an operations person should understand why the system made the decision" and thresholds must be changeable without code. A weighted score with named factors achieves both.

---

## 5. Dual Database Architecture: Supabase with Automatic SQLite Fallback

**Decision:** Support both cloud Supabase (PostgreSQL) and zero-config local SQLite (`orders.db`) with automatic failover.

**Alternatives considered:**
- PostgreSQL only: If remote DB credentials fail, the app crashes and reviewer cannot evaluate
- SQLite only: Reviewer cannot test collaborative cloud sharing

**Why dual:** If remote DB credentials have network or authentication delays, the system seamlessly uses local SQLite so that setup and execution take under 2 minutes without external blockers.

---

## 6. First-Order Protection Rule (Marketing Alignment)

**Decision:** Never auto-cancel first-time buyers (`customer_prior_orders == 0`), even if their risk score exceeds the cancel threshold. Route them to "Nudge to Prepaid" or "WhatsApp Confirmation".

**Alternatives considered:**
- Blind cancellation of all high-risk orders: Satisfies Operations but infuriates Marketing by wasting the ₹300+ Meta Ads acquisition cost.

**Why:** A genuine first-time buyer has a profit margin of ₹402.38 plus lifetime value. Auto-cancelling destroys customer trust. Nudging them to prepaid allows them to confirm intent without taking on COD return risk.

---

## 7. Mathematical Capping of Prepaid Discount at ₹40

**Decision:** Cap prepaid conversion discounts at ₹40 (10% of order value, max ₹40).

**Mathematical Justification:**
- COD expected RTO loss: $28\% \times ₹169.40 = ₹47.43$
- Prepaid expected RTO loss: $4\% \times ₹169.40 = ₹6.78$
- Expected savings per conversion: $₹47.43 - ₹6.78 = ₹40.65$
- Offering ₹40 preserves positive unit economics while incentivizing immediate payment.

---

## 8. Pincode Risk Shrinkage & Minimum Volume Threshold

**Decision:** Only use historical pincode RTO rates when a pincode has $\ge 5$ orders. For sparse pincodes, assign a baseline prior score.

**Why:** Analysis revealed that 82% of pincodes in the dataset had only 1 or 2 orders. Without a volume threshold, a single returned order would label an entire pincode as "100% RTO", blacklisting viable delivery areas.

