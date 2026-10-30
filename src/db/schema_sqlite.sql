-- SQLite Database Schema
CREATE TABLE IF NOT EXISTS orders (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id        TEXT UNIQUE NOT NULL,
  order_datetime  DATETIME NOT NULL,
  customer_name   TEXT,
  phone           TEXT,
  address         TEXT,
  city            TEXT,
  state           TEXT,
  pincode         TEXT,
  order_value     REAL,
  items           TEXT,
  num_items       INTEGER,
  customer_prior_orders INTEGER DEFAULT 0,
  customer_prior_rto    INTEGER DEFAULT 0,
  utm_source      TEXT,
  courier         TEXT,
  payment_method  TEXT,
  final_status    TEXT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_pincode ON orders(pincode);
CREATE INDEX IF NOT EXISTS idx_orders_payment ON orders(payment_method);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(final_status);
CREATE INDEX IF NOT EXISTS idx_orders_datetime ON orders(order_datetime);

CREATE TABLE IF NOT EXISTS order_decisions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id        TEXT UNIQUE REFERENCES orders(order_id),
  decision        TEXT NOT NULL,
  risk_score      REAL,
  risk_category   TEXT,
  reason          TEXT NOT NULL,
  risk_factors    TEXT,
  llm_used        INTEGER DEFAULT 0,
  llm_analysis    TEXT,
  actual_status   TEXT,
  decided_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decision_rules (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_key        TEXT UNIQUE NOT NULL,
  rule_value      REAL NOT NULL,
  description     TEXT NOT NULL,
  category        TEXT DEFAULT 'general',
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pincode_stats (
  pincode         TEXT PRIMARY KEY,
  total_orders    INTEGER DEFAULT 0,
  total_delivered INTEGER DEFAULT 0,
  total_rto       INTEGER DEFAULT 0,
  rto_rate        REAL DEFAULT 0,
  avg_order_value REAL,
  risk_reliable   INTEGER DEFAULT 0,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS whatsapp_conversations (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id        TEXT REFERENCES orders(order_id),
  flow_type       TEXT NOT NULL,
  status          TEXT DEFAULT 'pending',
  messages        TEXT DEFAULT '[]',
  discount_offered REAL,
  payment_simulated INTEGER DEFAULT 0,
  replied_at      DATETIME,
  expires_at      DATETIME,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_metrics (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  metric_date     DATE UNIQUE NOT NULL,
  total_orders    INTEGER DEFAULT 0,
  shipped         INTEGER DEFAULT 0,
  confirmed       INTEGER DEFAULT 0,
  nudged          INTEGER DEFAULT 0,
  cancelled       INTEGER DEFAULT 0,
  estimated_rto_saved   REAL DEFAULT 0,
  estimated_genuine_lost REAL DEFAULT 0,
  prepaid_discounts     REAL DEFAULT 0,
  net_impact            REAL DEFAULT 0,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
