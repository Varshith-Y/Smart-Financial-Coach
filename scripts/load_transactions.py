# scripts/load_transactions.py

# scripts/load_transactions.py
import os
import sys

# Ensure project root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import os
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app import models
from app.database import Base

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Simple category normalisation mapping
CATEGORY_MAP = {
    "Coffe": ("Coffee", "Food & Drink"),
    "Restuarant": ("Restaurant", "Food & Drink"),
    "Film/enjoyment": ("Entertainment", "Leisure"),
    # add more as you see patterns...
}


def get_or_create_user_and_account(db: Session):
    user = db.query(models.User).first()
    if not user:
        user = models.User(name="Demo User", email=None, segment="demo")
        db.add(user)
        db.commit()
        db.refresh(user)

    account = (
        db.query(models.Account)
        .filter(models.Account.user_id == user.id)
        .first()
    )
    if not account:
        account = models.Account(
            user_id=user.id,
            name="Demo Everyday Account",
            institution="Demo Bank",
            account_type="TRANSACTION",
            currency="AUD",
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    return user, account


def get_or_create_category(db: Session, raw_name: str) -> models.Category:
    existing = (
        db.query(models.Category)
        .filter(models.Category.raw_name == raw_name)
        .first()
    )
    if existing:
        return existing

    # Normalise display name + group
    if raw_name in CATEGORY_MAP:
        display_name, group_name = CATEGORY_MAP[raw_name]
    else:
        display_name, group_name = raw_name, None

    cat = models.Category(
        raw_name=raw_name,
        display_name=display_name,
        group_name=group_name,
        is_discretionary=1,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def load_csv(file_path: str = "data/transactions.csv"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV not found: {file_path}")

    df = pd.read_csv(file_path)

    # Expecting columns: date, category, amount
    required_cols = {"date", "category", "amount"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")

    db = SessionLocal()
    try:
        user, account = get_or_create_user_and_account(db)

        inserted = 0
        for _, row in df.iterrows():
            # Parse datetime
            # If your date has timezone suffix like '+0000', pandas may already parse it; adjust if needed
            dt = pd.to_datetime(row["date"])

            raw_category = str(row["category"])
            amount = float(row["amount"])

            category = get_or_create_category(db, raw_category)

            txn = models.Transaction(
                account_id=account.id,
                category_id=category.id,
                txn_datetime=dt.to_pydatetime(),
                amount=amount,
                direction="DEBIT",
                raw_category=raw_category,
            )
            db.add(txn)
            inserted += 1

        db.commit()
        print(f"Inserted {inserted} transactions.")
    finally:
        db.close()


if __name__ == "__main__":
    load_csv()
