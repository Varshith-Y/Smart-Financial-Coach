from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Date,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    segment = Column(String, nullable=True)

    accounts = relationship("Account", back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    institution = Column(String, nullable=True)
    account_type = Column(String, nullable=True)  # e.g. "TRANSACTION"
    currency = Column(String, default="AUD")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    raw_name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    group_name = Column(String, nullable=True)
    is_discretionary = Column(Integer, default=1)  # 1 = True, 0 = False

    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    txn_datetime = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    direction = Column(String, default="DEBIT")  # all expenses for now
    raw_category = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Month is stored as the first day of the month, e.g. 2025-03-01
    month = Column(Date, nullable=False)

    amount_limit = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships (optional)
    user = relationship("User", backref="budgets")
    category = relationship("Category", backref="budgets")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)              # e.g. "Europe 2026"
    target_amount = Column(Numeric(10, 2), nullable=False)
    current_amount = Column(Numeric(10, 2), default=0) # how much saved so far

    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)

    status = Column(String, default="ACTIVE")          # ACTIVE / COMPLETED / PAUSED
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="goals")
