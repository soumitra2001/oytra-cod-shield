-- ============================================================
-- Oytra COD RTO Risk Assessment — Database Schema
-- Run this against your Supabase PostgreSQL database
-- ============================================================

-- 1. Orders (raw CSV import)
CREATE TABLE IF NOT EXISTS orders (
  id              BIGSERIAL PRIMARY KEY,
  order_id        TEXT UNIQUE NOT NULL,
  order_datetime  TIMESTAMPTZ NOT NULL,
  customer_name   TEXT,
  phone           TEXT,
  address         TEXT,
  city            TEXT,
  state           TEXT,
  pincode         TEXT,
  order_value     NUMERIC(10,2),
  items           TEXT,
  num_items       INTEGER,
  customer_prior_orders INTEGER DEFAULT 0,
  customer_prior_rto    INTEGER DEFAULT 0,
  utm_source      TEXT,
  courier         TEXT,
  payment_method  TEXT,
  final_status    TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_pincode ON orders(pincode);
CREATE INDEX IF NOT EXISTS idx_orders_payment ON orders(payment_method);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(final_status);
CREATE INDEX IF NOT EXISTS idx_orders_datetime ON orders(order_datetime);

-- 2. Order Decisions (engine output)
CREATE TABLE IF NOT EXISTS order_decisions (
  id              BIGSERIAL PRIMARY KEY,
  order_id        TEXT UNIQUE REFERENCES orders(order_id),
  decision        TEXT NOT NULL CHECK (
    decision IN ('ship', 'confirm', 'nudge_prepaid', 'cancel')
  ),
  risk_score      NUMERIC(5,2),
  risk_category   TEXT,
  reason          TEXT NOT NULL,
  risk_factors    JSONB,
  llm_used        BOOLEAN DEFAULT FALSE,
  llm_analysis    JSONB,
  actual_status   TEXT,
  decided_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Decision Rules (configurable thresholds)
CREATE TABLE IF NOT EXISTS decision_rules (
  id              SERIAL PRIMARY KEY,
  rule_key        TEXT UNIQUE NOT NULL,
  rule_value      NUMERIC(10,2) NOT NULL,
  description     TEXT NOT NULL,
  category        TEXT DEFAULT 'general',
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Pincode Stats (aggregated risk)
CREATE TABLE IF NOT EXISTS pincode_stats (
  pincode         TEXT PRIMARY KEY,
  total_orders    INTEGER DEFAULT 0,
  total_delivered INTEGER DEFAULT 0,
  total_rto       INTEGER DEFAULT 0,
  rto_rate        NUMERIC(5,2) DEFAULT 0,
  avg_order_value NUMERIC(10,2),
  risk_reliable   BOOLEAN DEFAULT FALSE,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 5. WhatsApp Conversations (mock simulator)
CREATE TABLE IF NOT EXISTS whatsapp_conversations (
  id              BIGSERIAL PRIMARY KEY,
  order_id        TEXT REFERENCES orders(order_id),
  flow_type       TEXT NOT NULL CHECK (
    flow_type IN ('confirmation', 'nudge_prepaid')
  ),
  status          TEXT DEFAULT 'pending' CHECK (
    status IN ('pending', 'confirmed', 'rejected', 'converted_prepaid', 'expired', 'awaiting_clarification')
  ),
  messages        JSONB DEFAULT '[]',
  discount_offered NUMERIC(10,2),
  payment_simulated BOOLEAN DEFAULT FALSE,
  replied_at      TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Daily Metrics (dashboard aggregation)
CREATE TABLE IF NOT EXISTS daily_metrics (
  id              SERIAL PRIMARY KEY,
  metric_date     DATE UNIQUE NOT NULL,
  total_orders    INTEGER DEFAULT 0,
  shipped         INTEGER DEFAULT 0,
  confirmed       INTEGER DEFAULT 0,
  nudged          INTEGER DEFAULT 0,
  cancelled       INTEGER DEFAULT 0,
  estimated_rto_saved   NUMERIC(12,2) DEFAULT 0,
  estimated_genuine_lost NUMERIC(12,2) DEFAULT 0,
  prepaid_discounts     NUMERIC(12,2) DEFAULT 0,
  net_impact            NUMERIC(12,2) DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
