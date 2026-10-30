# Oytra COD Shield — AI Pre-Shipment Risk Engine

An AI-powered risk assessment engine that evaluates incoming Cash on Delivery (COD) orders **before shipping** to eliminate return-to-origin (RTO) courier costs while protecting genuine first-time buyers and marketing customer acquisition cost (CAC).

Built for the **Oytra Associate Software Engineer Take-Home Assignment**.

---

## ⚡ Quick Start (< 5 minutes)

### Prerequisites
- **Python 3.10+**
- Free **Google Gemini API Key** ([Get free key here](https://aistudio.google.com/apikey))

### 1. Clone & Enter Repository
```bash
git clone https://github.com/soumitra2001/oytra-cod-shield.git
cd oytra-cod-shield
```

### 2. Create Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add AI API Key
The cloud database is already pre-configured in the code with automatic local SQLite fallback—no database setup or DB URL is required. Just set your Gemini API key:
```bash
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

### 4. Launch Application
```bash
uvicorn src.api.main:app --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🖥️ Dashboard Functionality & Flow

The web interface provides an end-to-end operational flow across four dedicated tabs:

1. **Create Order**:
   - Enter order details (Customer Name, 10-digit Phone, Delivery Address, Pincode, and Cart Value).
   - Order ID is auto-generated (`#KTxxxxxx`).
   - The engine queries customer history by phone number, scores address quality via Gemini LLM, computes a transparent **0–100 risk score**, and routes the order into one of four action tiers (**Ship As-Is**, **WhatsApp Confirmation**, **Prepaid Nudge**, or **Hold / Cancel**) with a plain-English explanation for operations.

2. **Created Orders**:
   - Real-time table of all newly submitted and evaluated orders.
   - **Live Status Dropdown**: Change order status on the fly (`PENDING_CONFIRMATION`, `APPROVED_FOR_SHIPPING`, `DELIVERED`, `RTO`).
   - **Interactive Modal & WhatsApp Simulator**: Click any order row or the WhatsApp button to view itemized score factors and test customer conversational responses (*Confirm "YES"*, *Cancel "NO"*, *Hinglish "Haan bhej do"*, or *24h Timeout*).

3. **Founder Dashboard**:
   - Executive morning brief answering: *How many orders landed in each bucket? How much was saved from avoided RTOs? What is the net financial impact?*
   - **Date Range Filters**: View metrics by `Today`, `Last 7 Days`, `Last 30 Days`, `All Time`, or select a `Custom Range`.
   - **Live Unit Economics**: Connects delivered orders (62% gross margin), avoided RTO savings (Rs. 169.40/order), and courier losses to display live net financial contribution.

4. **Rules & Thresholds**:
   - Dynamic business settings (e.g. *first_order_protect*, *pincode_min_orders*, *max_prepaid_discount*, and score thresholds).
   - Saved and updated directly in the database without code redeployment.

---

## 🧪 Running Unit Tests

```bash
pytest tests/ -v
```

---

## 📄 Assignment Deliverables

* 📊 **Executive Business Memo (PDF)**: [`docs/business-memo.pdf`](docs/business-memo.pdf)
* 📝 **Business Memo (Markdown)**: [`docs/business-memo.md`](docs/business-memo.md)
* 🪵 **Decision Log**: [`docs/decision-log.md`](docs/decision-log.md)
* 🤖 **AI Usage Log**: [`docs/ai-usage-log.md`](docs/ai-usage-log.md)
