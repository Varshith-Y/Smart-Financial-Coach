from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import subprocess

from .database import Base, engine, SessionLocal
from . import models
from sqlalchemy import func

from pydantic import BaseModel
from datetime import datetime, date

from dateutil.relativedelta import relativedelta

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Financial Coach - API")

origins = [
    "http://localhost:5173",   # Vite dev server (or CRA)
    "http://127.0.0.1:5173",
    # you can later add your deployed frontend domain here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get a DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Pydantic Schemas ----------

class TransactionOut(BaseModel):
    id: int
    txn_datetime: datetime
    amount: float
    raw_category: str
    category_name: str | None
    account_id: int

    class Config:
        orm_mode = True

class CategorySpend(BaseModel):
    category_name: str
    total_spent: float


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_spent: float
    by_category: List[CategorySpend]

class CategoryMonthTotal(BaseModel):
    category_name: str
    total_spent: float


class MonthSnapshot(BaseModel):
    year: int
    month: int
    total_spent: float
    by_category: List[CategoryMonthTotal]


class BiggestJump(BaseModel):
    category_name: str
    from_year: int
    from_month: int
    to_year: int
    to_month: int
    absolute_change: float
    percentage_change: float | None = None


class TrajectoryResponse(BaseModel):
    months: List[MonthSnapshot]
    biggest_jump: BiggestJump | None = None

class BudgetCreate(BaseModel):
    category_name: str   # e.g. "Restaurant" (display_name)
    year: int
    month: int
    amount_limit: float  # monthly budget for that category


class BudgetOut(BaseModel):
    id: int
    category_name: str
    year: int
    month: int
    amount_limit: float

    class Config:
        orm_mode = True


class BudgetInsight(BaseModel):
    category_name: str
    year: int
    month: int
    amount_limit: float
    spent: float
    status: str          # "OK", "NEAR_LIMIT", "OVER_LIMIT"
    message: str


class GoalCreate(BaseModel):
    name: str
    target_amount: float
    start_date: date       # "2025-03-01"
    target_date: date      # "2026-03-01"


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    start_date: date
    target_date: date
    status: str

    class Config:
        orm_mode = True


class GoalProgress(BaseModel):
    id: int
    name: str
    target_amount: float
    current_amount: float
    percent_complete: float
    months_left: int
    monthly_needed: float
    status: str
    message: str


class GoalContribution(BaseModel):
    amount: float


class SpendRecommendation(BaseModel):
    category_from: str              # where to cut back
    category_to: str | None = None  # where to reallocate (optional)
    amount: float
    reason: str                     # why this was flagged
    action: str                     # what the user should do


class RecommendationsResponse(BaseModel):
    year: int
    month: int
    total_spent: float
    spend_recommendations: List[SpendRecommendation]
    goal_highlight: str | None = None
    budget_insights: List[BudgetInsight]


# ---------- Routes ----------

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/transactions", response_model=List[TransactionOut])
def list_transactions(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    query = (
        db.query(models.Transaction, models.Category)
        .outerjoin(models.Category, models.Transaction.category_id == models.Category.id)
        .order_by(models.Transaction.txn_datetime.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []
    for txn, cat in query:
        result.append(
            TransactionOut(
                id=txn.id,
                txn_datetime=txn.txn_datetime,
                amount=float(txn.amount),
                raw_category=txn.raw_category,
                category_name=cat.display_name if cat else None,
                account_id=txn.account_id,
            )
        )
    return result

@app.get("/summary/monthly", response_model=MonthlySummary)
def get_monthly_summary(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    # Compute month boundaries
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    # Total spent in this month
    total_spent = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0))
        .filter(models.Transaction.txn_datetime >= start)
        .filter(models.Transaction.txn_datetime < end)
        .scalar()
    )

    # Per-category breakdown
    rows = (
        db.query(
            models.Category.display_name,
            func.sum(models.Transaction.amount).label("cat_total"),
        )
        .join(
            models.Category,
            models.Transaction.category_id == models.Category.id,
        )
        .filter(models.Transaction.txn_datetime >= start)
        .filter(models.Transaction.txn_datetime < end)
        .group_by(models.Category.display_name)
        .all()
    )

    by_category = [
        CategorySpend(category_name=cat_name, total_spent=float(cat_total))
        for cat_name, cat_total in rows
    ]

    return MonthlySummary(
        year=year,
        month=month,
        total_spent=float(total_spent or 0),
        by_category=by_category,
    )

@app.get("/summary/trajectory", response_model=TrajectoryResponse)
def get_trajectory(
    months: int = 6,
    db: Session = Depends(get_db),
):
    """
    Return last N months of spending (by month, by category)
    plus the category with the largest month-on-month jump.
    """

    # 1) Get year-month-category totals from DB
    # NOTE: func.strftime is SQLite-specific; we'll adjust
    # later when we move to Postgres on Azure.
    rows = (
        db.query(
            func.extract("year", models.Transaction.txn_datetime).label("year"),
            func.extract("month", models.Transaction.txn_datetime).label("month"),
            models.Category.display_name.label("category_name"),
            func.sum(models.Transaction.amount).label("total_spent"),
        )
        .join(
            models.Category,
            models.Transaction.category_id == models.Category.id,
        )
        .group_by("year", "month", models.Category.display_name)
        .order_by("year", "month")
        .all()
    )

    if not rows:
        return TrajectoryResponse(months=[], biggest_jump=None)

    # 2) Build a structure: { (year, month): {category -> total} }
    from collections import defaultdict

    per_month_cat = defaultdict(lambda: defaultdict(float))

    for year_val, month_val, category_name, total_spent in rows:
        year = int(year_val)
        month = int(month_val)
        per_month_cat[(year, month)][category_name] += float(total_spent)

    # 3) Sort months and keep only the last N
    sorted_keys = sorted(per_month_cat.keys())  # list of (year, month)
    if months > 0:
        sorted_keys = sorted_keys[-months:]

    # 4) Build MonthSnapshot list
    month_snapshots: List[MonthSnapshot] = []
    for (year, month) in sorted_keys:
        cat_totals = per_month_cat[(year, month)]
        by_category = [
            CategoryMonthTotal(category_name=cat, total_spent=amt)
            for cat, amt in cat_totals.items()
        ]
        total_spent = sum(cat_totals.values())
        month_snapshots.append(
            MonthSnapshot(
                year=year,
                month=month,
                total_spent=total_spent,
                by_category=by_category,
            )
        )

    # 5) Compute biggest month-on-month jump per category
    # Flatten per category: { category_name: [(year, month, total), ...] }
    cat_history = defaultdict(list)
    for (year, month), cat_totals in per_month_cat.items():
        for cat, amt in cat_totals.items():
            cat_history[cat].append((year, month, amt))

    # Sort each category's history by (year, month)
    for cat in cat_history:
        cat_history[cat].sort(key=lambda x: (x[0], x[1]))

    biggest_jump: BiggestJump | None = None
    max_abs_change = 0.0

    for cat, entries in cat_history.items():
        # entries is list of (year, month, amt) for that category
        for i in range(1, len(entries)):
            prev_year, prev_month, prev_amt = entries[i - 1]
            curr_year, curr_month, curr_amt = entries[i]

            # Only consider jumps within our selected months window
            if (prev_year, prev_month) not in sorted_keys or (curr_year, curr_month) not in sorted_keys:
                continue

            diff = curr_amt - prev_amt  # positive = spend increase
            abs_diff = abs(diff)

            if abs_diff > max_abs_change:
                max_abs_change = abs_diff
                pct_change = None
                if prev_amt != 0:
                    pct_change = (diff / prev_amt) * 100.0

                biggest_jump = BiggestJump(
                    category_name=cat,
                    from_year=prev_year,
                    from_month=prev_month,
                    to_year=curr_year,
                    to_month=curr_month,
                    absolute_change=diff,
                    percentage_change=pct_change,
                )

    return TrajectoryResponse(
        months=month_snapshots,
        biggest_jump=biggest_jump,
    )

def get_demo_user(db: Session) -> models.User:
    user = db.query(models.User).first()
    if not user:
        # In case DB is empty (e.g. if loader wasn't run), create a default user.
        user = models.User(name="Demo User", email=None, segment="demo")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@app.post("/budgets", response_model=BudgetOut)
def upsert_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
):
    """
    Create or update a budget for a category for a specific month
    for the demo user.
    """
    user = get_demo_user(db)

    # Get category by display_name
    category = (
        db.query(models.Category)
        .filter(models.Category.display_name == payload.category_name)
        .first()
    )
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{payload.category_name}' not found. "
                   f"Make sure it matches a category in your data.",
        )

    # Month as first day
    month_start = date(payload.year, payload.month, 1)

    # Check if a budget already exists
    existing = (
        db.query(models.Budget)
        .filter(models.Budget.user_id == user.id)
        .filter(models.Budget.category_id == category.id)
        .filter(models.Budget.month == month_start)
        .first()
    )

    if existing:
        existing.amount_limit = payload.amount_limit
        db.commit()
        db.refresh(existing)
        budget = existing
    else:
        budget = models.Budget(
            user_id=user.id,
            category_id=category.id,
            month=month_start,
            amount_limit=payload.amount_limit,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)

    return BudgetOut(
        id=budget.id,
        category_name=category.display_name,
        year=payload.year,
        month=payload.month,
        amount_limit=float(budget.amount_limit),
    )


@app.get("/budgets", response_model=List[BudgetOut])
def list_budgets(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    user = get_demo_user(db)
    month_start = date(year, month, 1)

    rows = (
        db.query(models.Budget, models.Category)
        .join(models.Category, models.Budget.category_id == models.Category.id)
        .filter(models.Budget.user_id == user.id)
        .filter(models.Budget.month == month_start)
        .all()
    )

    result: List[BudgetOut] = []
    for budget, category in rows:
        result.append(
            BudgetOut(
                id=budget.id,
                category_name=category.display_name,
                year=year,
                month=month,
                amount_limit=float(budget.amount_limit),
            )
        )
    return result


@app.get("/insights/budget", response_model=List[BudgetInsight])
def get_budget_insights(
    year: int,
    month: int,
    threshold: float = 0.8,   # 80% of budget
    db: Session = Depends(get_db),
):
    """
    For each budgeted category for the demo user this month:
    - Compute spend
    - Return status + human-readable message
    """
    user = get_demo_user(db)
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    # Fetch budgets + categories
    budget_rows = (
        db.query(models.Budget, models.Category)
        .join(models.Category, models.Budget.category_id == models.Category.id)
        .filter(models.Budget.user_id == user.id)
        .filter(models.Budget.month == month_start)
        .all()
    )

    if not budget_rows:
        return []

    insights: List[BudgetInsight] = []

    for budget, category in budget_rows:
        # Sum spend for this category & user in the given month
        total_spent = (
            db.query(func.coalesce(func.sum(models.Transaction.amount), 0))
            .join(
                models.Account,
                models.Transaction.account_id == models.Account.id,
            )
            .filter(models.Account.user_id == user.id)
            .filter(models.Transaction.category_id == category.id)
            .filter(models.Transaction.txn_datetime >= month_start)
            .filter(models.Transaction.txn_datetime < month_end)
            .scalar()
        )

        spent = float(total_spent or 0)
        limit_val = float(budget.amount_limit)

        # Determine status
        if spent >= limit_val:
            status = "OVER_LIMIT"
            diff = spent - limit_val
            message = (
                f"You've exceeded your {category.display_name} budget "
                f"of ${limit_val:.2f} by ${diff:.2f} this month."
            )
        elif spent >= threshold * limit_val:
            status = "NEAR_LIMIT"
            remaining = limit_val - spent
            message = (
                f"You're close to your {category.display_name} budget for "
                f"{year}-{month:02d}. You've spent ${spent:.2f} out of "
                f"${limit_val:.2f}. Try to keep the remaining "
                f"${remaining:.2f} for the rest of the month."
            )
        else:
            status = "OK"
            remaining = limit_val - spent
            message = (
                f"Your {category.display_name} spending is on track. "
                f"You've spent ${spent:.2f} out of your ${limit_val:.2f} "
                f"budget for {year}-{month:02d}."
            )

        insights.append(
            BudgetInsight(
                category_name=category.display_name,
                year=year,
                month=month,
                amount_limit=limit_val,
                spent=spent,
                status=status,
                message=message,
            )
        )

    return insights

@app.get("/insights/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    year: int,
    month: int,
    db: Session = Depends(get_db),
):
    """
    Combine monthly summary, budgets and goals to generate
    simple 'AI-style' spend recommendations.
    """

    # 1) Get monthly summary (we reuse our existing function)
    monthly_summary: MonthlySummary = get_monthly_summary(year=year, month=month, db=db)

    # 2) Get budget insights (reuse existing logic)
    budget_insights: List[BudgetInsight] = get_budget_insights(year=year, month=month, db=db)

    # If there are no budgets set, we can't recommend much
    if not budget_insights:
        return RecommendationsResponse(
            year=year,
            month=month,
            total_spent=monthly_summary.total_spent,
            spend_recommendations=[],
            goal_highlight="Set at least one category budget to unlock recommendations.",
            budget_insights=[],
        )

    # 3) Split categories by status
    overs_or_near: List[BudgetInsight] = [
        b for b in budget_insights if b.status in ("OVER_LIMIT", "NEAR_LIMIT")
    ]

    slack_entries: List[tuple[float, BudgetInsight]] = []
    for b in budget_insights:
        remaining = b.amount_limit - b.spent
        if remaining > 0 and b.status == "OK":
            slack_entries.append((remaining, b))

    # Sort slack categories by how much room they have (descending)
    slack_entries.sort(key=lambda x: x[0], reverse=True)

    spend_recs: List[SpendRecommendation] = []

    # 4) Build simple reallocation suggestions
    for b in overs_or_near:
        # How much do we want to adjust?
        if b.status == "OVER_LIMIT":
            # amount over budget
            needed = b.spent - b.amount_limit
        else:  # NEAR_LIMIT
            # aim to free up ~10% of budget
            needed = 0.1 * b.amount_limit

        if needed <= 0:
            continue

        # Try to pair with a slack category
        if slack_entries:
            slack_remaining, slack_b = slack_entries[0]
            reallocate = min(needed, slack_remaining)

            if reallocate <= 0:
                continue

            # Reduce remaining slack in that category
            slack_entries[0] = (slack_remaining - reallocate, slack_b)

            reason = (
                f"{b.category_name} spending is {b.status.replace('_', ' ').lower()} "
                f"for {year}-{month:02d}."
            )
            action = (
                f"Try trimming about ${reallocate:.2f} from {b.category_name} and "
                f"shifting that towards your {slack_b.category_name} / savings for this month."
            )

            spend_recs.append(
                SpendRecommendation(
                    category_from=b.category_name,
                    category_to=slack_b.category_name,
                    amount=round(reallocate, 2),
                    reason=reason,
                    action=action,
                )
            )
        else:
            # No slack categories: suggest a direct reduction
            reason = (
                f"{b.category_name} spending is {b.status.replace('_', ' ').lower()} "
                f"for {year}-{month:02d}."
            )
            action = (
                f"Try reducing your {b.category_name} spend by about ${needed:.2f} "
                f"over the rest of the month to get back on track."
            )
            spend_recs.append(
                SpendRecommendation(
                    category_from=b.category_name,
                    category_to=None,
                    amount=round(needed, 2),
                    reason=reason,
                    action=action,
                )
            )

    # 5) Pull in goal context (optional 'highlight')
    try:
        goal_progress: List[GoalProgress] = get_goals_progress(db=db)
        active_goals = [g for g in goal_progress if g.status == "ACTIVE"]
        goal_highlight = None
        if active_goals:
            # most demanding goal = highest monthly_needed
            most_demanding = max(active_goals, key=lambda g: g.monthly_needed)
            goal_highlight = (
                f"Top priority goal: '{most_demanding.name}'. "
                f"To stay on track you need about "
                f"${most_demanding.monthly_needed:.2f}/month for the next "
                f"{most_demanding.months_left} month(s)."
            )
    except Exception:
        # In case goals table is empty or any issue, just skip
        goal_highlight = None

    return RecommendationsResponse(
        year=year,
        month=month,
        total_spent=monthly_summary.total_spent,
        spend_recommendations=spend_recs,
        goal_highlight=goal_highlight,
        budget_insights=budget_insights,
    )


@app.post("/goals", response_model=GoalOut)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
):
    user = get_demo_user(db)

    goal = models.Goal(
        user_id=user.id,
        name=payload.name,
        target_amount=payload.target_amount,
        current_amount=0,
        start_date=payload.start_date,
        target_date=payload.target_date,
        status="ACTIVE",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        start_date=goal.start_date,
        target_date=goal.target_date,
        status=goal.status,
    )


@app.get("/goals", response_model=List[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    user = get_demo_user(db)
    goals = db.query(models.Goal).filter(models.Goal.user_id == user.id).all()

    return [
        GoalOut(
            id=g.id,
            name=g.name,
            target_amount=float(g.target_amount),
            current_amount=float(g.current_amount),
            start_date=g.start_date,
            target_date=g.target_date,
            status=g.status,
        )
        for g in goals
    ]

@app.post("/goals/{goal_id}/contribute", response_model=GoalOut)
def contribute_to_goal(
    goal_id: int,
    payload: GoalContribution,
    db: Session = Depends(get_db),
):
    user = get_demo_user(db)
    goal = (
        db.query(models.Goal)
        .filter(models.Goal.id == goal_id)
        .filter(models.Goal.user_id == user.id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.current_amount = (goal.current_amount or 0) + payload.amount

    # Auto-complete if reached
    if goal.current_amount >= goal.target_amount:
        goal.status = "COMPLETED"

    db.commit()
    db.refresh(goal)

    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=float(goal.target_amount),
        current_amount=float(goal.current_amount),
        start_date=goal.start_date,
        target_date=goal.target_date,
        status=goal.status,
    )



@app.get("/goals/progress", response_model=List[GoalProgress])
def get_goals_progress(db: Session = Depends(get_db)):
    user = get_demo_user(db)
    today = date.today()

    goals = (
        db.query(models.Goal)
        .filter(models.Goal.user_id == user.id)
        .all()
    )

    results: List[GoalProgress] = []

    for g in goals:
        target = float(g.target_amount)
        current = float(g.current_amount or 0)

        # percent complete
        if target > 0:
            percent = (current / target) * 100.0
        else:
            percent = 0.0

        # months left from today to target_date (at least 1)
        if g.target_date <= today:
            months_left = 1
        else:
            rd = relativedelta(g.target_date, today)
            months_left = rd.years * 12 + rd.months
            if months_left <= 0:
                months_left = 1

        remaining = max(target - current, 0.0)
        monthly_needed = remaining / months_left if months_left > 0 else remaining

        # Build a simple coach message
        if g.status == "COMPLETED":
            message = (
                f"Goal '{g.name}' is completed 🎉. "
                f"You reached your target of ${target:.2f}."
            )
        else:
            message = (
                f"You're {percent:.1f}% of the way to '{g.name}'. "
                f"To hit ${target:.2f} by {g.target_date}, you need to save "
                f"about ${monthly_needed:.2f} per month for the next {months_left} month(s)."
            )

        results.append(
            GoalProgress(
                id=g.id,
                name=g.name,
                target_amount=target,
                current_amount=current,
                percent_complete=percent,
                months_left=months_left,
                monthly_needed=monthly_needed,
                status=g.status,
                message=message,
            )
        )

    return results

@app.post("/admin/load-demo-data")
def admin_load_demo_data(background_tasks: BackgroundTasks):
    """
    One-off helper to load demo transactions from data/transactions.csv
    into the SQLite database inside the container by reusing the
    scripts/load_transactions.py script.
    """

    def run_loader():
        try:
            # This will use DATABASE_URL from env, or fallback to sqlite:///./sfc.db
            # and read data/transactions.csv inside the container
            subprocess.run(
                ["python", "scripts/load_transactions.py"],
                check=True,
            )
        except Exception as exc:
            # Just log to container logs; response is already returned
            print("Error loading demo data:", exc)

    # Run in the background so the HTTP request returns quickly
    background_tasks.add_task(run_loader)

    return {"status": "started", "detail": "Demo data load triggered."}
