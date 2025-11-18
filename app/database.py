import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use env var if set, else fall back to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sfc.db")

# For SQLite we need check_same_thread; for others we don’t
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
