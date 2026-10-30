"""Application configuration — loads .env and provides DB/API clients."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orders.db")

# Ensure SQLAlchemy uses psycopg2 driver if postgresql:// is provided
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as test_conn:
        pass
except Exception as e:
    print(f"⚠️ Warning: Could not connect to {DATABASE_URL[:30]}... ({e})")
    print("👉 Falling back to local SQLite database: sqlite:///./orders.db")
    DATABASE_URL = "sqlite:///./orders.db"
    engine = create_engine(DATABASE_URL)

IS_POSTGRES = engine.dialect.name == "postgresql"
SessionLocal = sessionmaker(bind=engine)

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Business constants (from the assignment)
FORWARD_SHIPPING_COST = 65.0
RETURN_SHIPPING_COST = 65.0
PACKAGING_COST = 25.0
DAMAGE_RATE = 0.08
AVG_DAMAGED_PRODUCT_COST = 180.0
RTO_COST_PER_ORDER = FORWARD_SHIPPING_COST + RETURN_SHIPPING_COST + PACKAGING_COST + (DAMAGE_RATE * AVG_DAMAGED_PRODUCT_COST)  # ₹169.40
GROSS_MARGIN_RATE = 0.62
AVG_ORDER_VALUE = 649.0
AVG_MARGIN_PER_ORDER = AVG_ORDER_VALUE * GROSS_MARGIN_RATE  # ₹402.38
CUSTOMER_ACQUISITION_COST = 300.0
COD_RTO_RATE = 0.28
PREPAID_RTO_RATE = 0.04


def get_db():
    """FastAPI dependency for DB sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
