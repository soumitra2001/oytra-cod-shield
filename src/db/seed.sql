-- ============================================================
-- Seed: Default decision rules (configurable by non-technical users)
-- ============================================================

INSERT INTO decision_rules (rule_key, rule_value, description, category) VALUES
  -- Decision thresholds (risk score boundaries)
  ('ship_max_score',          30,    'Ship as-is if risk score is at or below this value', 'thresholds'),
  ('confirm_max_score',       50,    'Send WhatsApp confirmation if score is at or below this value', 'thresholds'),
  ('nudge_max_score',         70,    'Nudge to prepaid if score is at or below this value', 'thresholds'),

  -- Risk weights
  ('weight_pincode_rto',      25,    'Maximum points from pincode RTO rate', 'weights'),
  ('weight_prior_rto',        40,    'Maximum points from customer RTO history', 'weights'),
  ('weight_first_order',      12,    'Points added for first-time buyer with no history', 'weights'),
  ('weight_order_value',      10,    'Maximum points from order value anomaly', 'weights'),
  ('weight_llm_flags',        25,    'Maximum points from LLM name/address analysis', 'weights'),

  -- Business rules
  ('first_order_protect',      1,    'If 1, never auto-cancel first-time buyers (nudge instead)', 'business'),
  ('pincode_min_orders',       5,    'Minimum orders in a pincode before its RTO rate is used', 'business'),

  -- Nudge settings
  ('prepaid_discount_pct',    10,    'Discount percentage offered for prepaid conversion', 'nudge'),
  ('max_prepaid_discount',    40,    'Maximum rupee discount for prepaid nudge', 'nudge'),

  -- WhatsApp settings
  ('whatsapp_timeout_hours',  24,    'Hours to wait for customer WhatsApp reply', 'whatsapp'),
  ('timeout_action',           1,    'Action on timeout: 1 = cancel, 0 = hold', 'whatsapp')
ON CONFLICT (rule_key) DO NOTHING;
