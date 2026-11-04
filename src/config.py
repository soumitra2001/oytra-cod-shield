"""Application configuration — loads .env and provides DB/API clients."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Database: defaults to pre-configured Supabase PostgreSQL if not in env or on any DB connection error
DEFAULT_DB_URL = "testdb"

def get_db_engine():
    env_db = os.getenv("DATABASE_URL")
    
    # 1. Try env DATABASE_URL if explicitly provided
    if env_db and env_db.strip():
        candidate_url = env_db.strip()
        if candidate_url.startswith("postgresql://"):
            candidate_url = candidate_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        try:
            eng = create_engine(candidate_url, pool_pre_ping=True)
            with eng.connect():
                pass
            return eng, candidate_url
        except Exception as e:
            print(f"⚠️ Warning: Custom DATABASE_URL failed ({e})")
            print(f"👉 Falling back to default cloud database: {DEFAULT_DB_URL[:35]}...")

    # 2. Fall back to the default Supabase PostgreSQL database
    cloud_url = DEFAULT_DB_URL
    if cloud_url.startswith("postgresql://"):
        cloud_url = cloud_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    try:
        eng = create_engine(cloud_url, pool_pre_ping=True)
        with eng.connect():
            pass
        return eng, cloud_url
    except Exception as e:
        print(f"⚠️ Warning: Could not connect to default cloud database ({e})")
        print("👉 Falling back to local SQLite database: sqlite:///./orders.db")
        local_sqlite = "sqlite:///./orders.db"
        return create_engine(local_sqlite), local_sqlite

engine, DATABASE_URL = get_db_engine()
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
