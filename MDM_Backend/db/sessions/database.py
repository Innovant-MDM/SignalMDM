"""
signalmdm/database.py
---------------------
Database engine, session factory, Base declarative, and the FastAPI
dependency `get_db`.

All ORM models import `Base` from here. The engine is created lazily
on first import so tests can override `DATABASE_URL` before the module
is loaded.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load .env from the project root (MDM_Backend/)
load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:2025@localhost:5432/SignalMDM",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,       # Recycles stale connections automatically
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("APP_ENV") == "development",  # SQL logging in dev
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Shared declarative base — every ORM model must inherit from this.
Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """
    Yield a database session and guarantee it is closed after the request,
    even on exception.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
