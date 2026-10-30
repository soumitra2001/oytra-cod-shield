# 🧴 Oytra COD RTO Decision Engine

An AI-powered system that evaluates every Cash on Delivery (COD) order **before shipping** and decides whether to: ship it, confirm via WhatsApp, nudge the customer to prepaid, or hold/cancel it.

Built for the Oytra Associate Software Engineer Take-Home Assignment.

---

## ⚡ Quick Start (< 10 minutes)

### Prerequisites

- **Python 3.10+** installed ([download](https://python.org))
- **Internet connection** (for Supabase DB + Gemini API)

### Step 1: Clone & Enter

```bash
git clone https://github.com/YOUR_USERNAME/assignment-oytra.git
cd assignment-oytra
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to get it | Required? | Default / Fallback |
|----------|----------------|-----------|---------------------|
| `DATABASE_URL` | Supabase project → Settings → Database → Connection string | Optional | Automatically falls back to local SQLite (`orders.db`) |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) (Free tier) | Optional | Fallback to rule-based address & name validator |

> 💡 **Zero-Config Guarantee**: The system runs 100% out of the box! If no cloud database is provided or credentials fail, it seamlessly uses a local SQLite database (`orders.db`) so anyone can clone and run the project in under 2 minutes.

The `.env` file looks like:

```env
# Supabase PostgreSQL (or leave blank to use local SQLite)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres

# Google Gemini API Key (get free at https://aistudio.google.com/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 5: Set Up Database & Import Data

```bash
python scripts/setup_db.py
```

This will:
- ✅ Create all 6 database tables in Supabase
- ✅ Seed configurable decision rules
- ✅ Import 2,018 orders from `orders_sample.csv`
- ✅ Compute pincode-level RTO statistics

### Step 6: Run the Decision Engine on All Orders

```bash
python scripts/run_engine.py
```

This processes all COD orders through the risk engine and stores decisions.

### Step 7: Launch the Web Application (Interactive UI & Simulator)

```bash
uvicorn src.api.main:app --reload
```

Opens immediately at **http://localhost:8000** (no Swagger needed!) with:
- ⚡ **Live Order Decision & Action Center**: Test and evaluate any COD order with 1-click presets (Loyal Safe Buyer, First-Time Buyer with Hinglish directions, Incomplete "xyz" Address, Serial RTO Offender) and execute automated operational workflows.
- 📱 **Interactive WhatsApp Phone Simulator**: Live mobile phone screen with simulated customer replies ("YES", "NO", Hinglish "Haan bhej do", random question, 24-hr timeout) and mathematical discount justification.
- 📊 **Founder Morning Executive Brief**: 4 decision buckets, avoided RTO savings, cancellation costs, and net ₹ profit preserved.
- ⚙️ **Rules & Thresholds Manager**: Adjust risk boundaries and discounts live in the database without code modifications.
- 📦 **Order Database Explorer**: Filter by decision bucket and search across all 1,988 historical orders.

### Step 8 (Alternative): Launch the Streamlit Analytics Dashboard

```bash
streamlit run dashboard/app.py
```

Opens at **http://localhost:8501** for an alternative analytical dashboard view.

---

## 🏗️ Project Structure

```
assignment-oytra/
├── orders_sample.csv            # 2,018 historical COD orders
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
│
├── frontend/                    # Modern Interactive Web UI (Single Page Application)
│   ├── index.html               # Main application layout with tabs, cards & mobile frame
│   ├── css/style.css            # WhatsApp phone mockup, chat bubbles & custom styling
│   └── js/app.js                # Interactive controllers & API integration
│
├── scripts/
│   ├── setup_db.py              # One-command DB setup + CSV import
│   └── run_engine.py            # Process all orders through decision engine
│
├── src/
│   ├── config.py                # Config, DB connection, business constants
│   ├── db/
│   │   ├── schema.sql           # Table definitions
│   │   ├── seed.sql             # Default thresholds
│   │   └── import_csv.py        # CSV → PostgreSQL importer
│   ├── engine/
│   │   ├── risk_scorer.py       # Rule-based risk scoring (code/math)
│   │   ├── llm_analyzer.py      # Gemini: address/name validation
│   │   ├── decision_engine.py   # Score → decision + explanation
│   │   └── backtest.py          # Replay policy on historical data
│   ├── whatsapp/
│   │   └── flows.py             # Confirmation + nudge message logic
│   └── api/
│       └── main.py              # FastAPI endpoints
│
├── dashboard/
│   └── app.py                   # Streamlit dashboard + WhatsApp simulator
│
├── tests/
│   └── test_risk_scorer.py      # Unit tests
│
└── docs/
    ├── business_memo.md         # Part 4: Memo to the founder
    ├── decision_log.md          # Design decisions + reasoning
    └── ai_usage_log.md          # AI tools used + corrections
```

---

## 🧠 How the Decision Engine Works

### 1. Risk Scoring (Code/Math — no LLM)

Each COD order gets a **0–100 risk score** from these factors:

| Factor | Max Points | How It's Calculated |
|--------|-----------|-------------------|
| Pincode RTO rate | 25 | Historical RTO % for this pincode |
| Customer RTO history | 30 | Prior RTOs / prior orders ratio |
| First-time buyer | 10 | Added if no order history |
| Order value anomaly | 10 | High-value orders flagged |
| **LLM flags** | **25** | Fake name, bad address (Gemini) |
| **Total** | **100** | |

### 2. LLM Analysis (Gemini — only where it helps)

The LLM is called **only** for:
- 🔍 **Fake name detection** — "asdf", "test", keyboard mashing
- 🏠 **Address quality** — incomplete, gibberish vs valid Hinglish
- 📍 **City/state/pincode mismatch**

It is **NOT used** for math, scoring, or business rules.

### 3. Decision Mapping

| Risk Score | Decision | Action |
|-----------|----------|--------|
| 0–30 | **Ship as-is** | Low risk, ship immediately |
| 31–55 | **Confirm** | Send WhatsApp confirmation |
| 56–75 | **Nudge to prepaid** | Offer discount to pay online |
| 76–100 | **Hold/Cancel** | Too risky, don't ship |

> 💡 **All thresholds are configurable** in the dashboard — no code changes needed.

### 4. First-Time Buyer Protection

First-time buyers are **never auto-cancelled**, even with high risk scores. They're nudged to prepaid instead (to protect the ₹300+ acquisition cost).

---

## 💬 WhatsApp Simulator

The dashboard includes a mock WhatsApp chat interface for two flows:

**Confirmation Flow:**
| Reply | Action |
|-------|--------|
| YES / haan / ok | Confirm → ship |
| NO / nahi / cancel | Cancel order |
| Random text | Ask again |
| No reply (24h) | Cancel or hold (configurable) |

**Nudge to Prepaid Flow:**
| Reply | Action |
|-------|--------|
| YES | Simulate payment → mark prepaid |
| NO | Fall back to COD confirmation |
| Random text | Ask again |
| No reply (24h) | Cancel or hold (configurable) |

---

## 📊 Dashboard

One screen for the founder to check every morning:

- 📦 Orders in each of the 4 buckets (yesterday)
- 💰 Estimated ₹ saved from avoided RTOs
- ⚠️ Estimated ₹ lost from cancelled genuine orders
- 📈 **Net ₹ impact**
- ⚙️ Configurable thresholds (edit without touching code)

---

## 💰 Key Financial Numbers

| Metric | Value |
|--------|-------|
| Cost per RTO | ₹169.40 |
| Margin per delivered order | ₹402.38 (62% of ₹649) |
| Customer acquisition cost | ₹300+ |
| Prepaid conversion savings | ~₹40.65 per order |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📄 Deliverables

1. **This repo** — runnable in < 10 minutes with zero-config local SQLite fallback
2. **Business Memo (PDF & Markdown)** — [`docs/business-memo.pdf`](docs/business-memo.pdf) & [`docs/business_memo.md`](docs/business_memo.md)
3. **Decision Log** — [`docs/decision-log.md`](docs/decision-log.md)
4. **AI Usage Log** — [`docs/ai-usage-log.md`](docs/ai-usage-log.md)
