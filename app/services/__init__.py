"""Business logic for expenses and aggregations."""
import csv
import io
from datetime import date, datetime
from collections import defaultdict

from sqlalchemy import extract

from app import db
from app.models import Expense, Tag


VALID_CATEGORIES = ["materials", "labor", "furniture", "appliances", "decor", "other"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value):
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value}")


def _get_or_create_tags(tag_names):
    tags = []
    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
        tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def get_all_expenses(category=None, tag=None, date_from=None, date_to=None, sort="date_desc"):
    query = Expense.query

    if category:
        query = query.filter(Expense.category == category)
    if tag:
        query = query.filter(Expense.tags.any(Tag.name == tag.strip().lower()))
    if date_from:
        query = query.filter(Expense.date >= _parse_date(date_from))
    if date_to:
        query = query.filter(Expense.date <= _parse_date(date_to))

    if sort == "amount_desc":
        query = query.order_by(Expense.amount.desc())
    elif sort == "amount_asc":
        query = query.order_by(Expense.amount.asc())
    elif sort == "date_asc":
        query = query.order_by(Expense.date.asc())
    else:  # date_desc (default)
        query = query.order_by(Expense.date.desc())

    return query.all()


def get_expense_by_id(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        from flask import abort
        abort(404)
    return expense


def create_expense(data):
    _validate_expense_data(data)
    expense = Expense(
        name=data["name"].strip(),
        category=data["category"].strip(),
        amount=float(data["amount"]),
        date=_parse_date(data["date"]),
        notes=data.get("notes", "").strip(),
    )
    tag_names = data.get("tags", [])
    if isinstance(tag_names, str):
        tag_names = [t for t in tag_names.split(",") if t.strip()]
    expense.tags = _get_or_create_tags(tag_names)
    db.session.add(expense)
    db.session.commit()
    return expense


def update_expense(expense_id, data):
    expense = get_expense_by_id(expense_id)
    _validate_expense_data(data)
    expense.name = data["name"].strip()
    expense.category = data["category"].strip()
    expense.amount = float(data["amount"])
    expense.date = _parse_date(data["date"])
    expense.notes = data.get("notes", "").strip()

    tag_names = data.get("tags", [])
    if isinstance(tag_names, str):
        tag_names = [t for t in tag_names.split(",") if t.strip()]
    expense.tags = _get_or_create_tags(tag_names)
    db.session.commit()
    return expense


def delete_expense(expense_id):
    expense = get_expense_by_id(expense_id)
    db.session.delete(expense)
    db.session.commit()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_expense_data(data):
    errors = []
    if not data.get("name", "").strip():
        errors.append("Name is required.")
    if not data.get("category", "").strip():
        errors.append("Category is required.")
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            errors.append("Amount must be greater than zero.")
    except (TypeError, ValueError):
        errors.append("Amount must be a valid number.")
    if not data.get("date"):
        errors.append("Date is required.")
    else:
        try:
            _parse_date(data["date"])
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("; ".join(errors))


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def get_total_cost():
    result = db.session.query(db.func.sum(Expense.amount)).scalar()
    return round(result or 0, 2)


def get_cost_by_category():
    rows = (
        db.session.query(Expense.category, db.func.sum(Expense.amount))
        .group_by(Expense.category)
        .all()
    )
    return {cat: round(total, 2) for cat, total in rows}


def get_monthly_summary():
    rows = (
        db.session.query(
            extract("year", Expense.date).label("year"),
            extract("month", Expense.date).label("month"),
            db.func.sum(Expense.amount).label("total"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )
    return [
        {
            "year": int(r.year),
            "month": int(r.month),
            "label": date(int(r.year), int(r.month), 1).strftime("%b %Y"),
            "total": round(r.total, 2),
        }
        for r in rows
    ]


def get_recent_expenses(limit=5):
    return Expense.query.order_by(Expense.date.desc()).limit(limit).all()


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_expenses_csv(expenses=None):
    if expenses is None:
        expenses = get_all_expenses()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Category", "Amount", "Date", "Tags", "Notes"])
    for e in expenses:
        writer.writerow([
            e.id,
            e.name,
            e.category,
            e.amount,
            e.date.isoformat(),
            ", ".join(t.name for t in e.tags),
            e.notes or "",
        ])
    output.seek(0)
    return output.getvalue()
