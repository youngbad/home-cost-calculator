"""Business logic for expenses and aggregations."""
import csv
import io
import os
import json
from datetime import date, datetime
from collections import defaultdict

from sqlalchemy import extract
from google import genai
from google.genai import types

from app import db
from app.models import Expense, Tag


VALID_CATEGORIES = ["groceries", "transport", "home", "entertainment", "health", "car", "other"]


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

def get_all_expenses(wallet_id, category=None, tag=None, date_from=None, date_to=None, sort="date_desc", search=None):
    query = Expense.query.filter_by(wallet_id=wallet_id)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(Expense.name.ilike(search_term) | Expense.notes.ilike(search_term))
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


def create_expense(data, wallet_id):
    _validate_expense_data(data)
    expense = Expense(
        name=data["name"].strip(),
        category=data["category"].strip(),
        amount=float(data["amount"]),
        date=_parse_date(data["date"]),
        notes=data.get("notes", "").strip(),
        wallet_id=wallet_id,
    )
    tag_names = data.get("tags", [])
    if isinstance(tag_names, str):
        tag_names = [t for t in tag_names.split(",") if t.strip()]
    expense.tags = _get_or_create_tags(tag_names)
    db.session.add(expense)
    db.session.commit()
    return expense


def update_expense(expense_id, data, wallet_id):
    expense = get_expense_by_id(expense_id)
    if expense.wallet_id != wallet_id:
        from flask import abort
        abort(403)
        
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


def delete_expense(expense_id, wallet_id):
    expense = get_expense_by_id(expense_id)
    if expense.wallet_id != wallet_id:
        from flask import abort
        abort(403)
        
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

def get_total_cost(wallet_id):
    result = db.session.query(db.func.sum(Expense.amount)).filter(Expense.wallet_id == wallet_id).scalar()
    return round(result or 0, 2)


def get_cost_by_category(wallet_id):
    rows = (
        db.session.query(Expense.category, db.func.sum(Expense.amount))
        .filter(Expense.wallet_id == wallet_id)
        .group_by(Expense.category)
        .all()
    )
    return {cat: round(total, 2) for cat, total in rows}


def get_monthly_summary(wallet_id):
    rows = (
        db.session.query(
            extract("year", Expense.date).label("year"),
            extract("month", Expense.date).label("month"),
            db.func.sum(Expense.amount).label("total"),
        )
        .filter(Expense.wallet_id == wallet_id)
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


def get_recent_expenses(wallet_id, limit=5):
    return Expense.query.filter_by(wallet_id=wallet_id).order_by(Expense.date.desc()).limit(limit).all()


def get_largest_expense(wallet_id):
    return Expense.query.filter_by(wallet_id=wallet_id).order_by(Expense.amount.desc()).first()


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


# ---------------------------------------------------------------------------
# AI Receipt Parsing
# ---------------------------------------------------------------------------

def parse_receipt_with_ai(image_bytes, mime_type):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
You are an expert in analyzing receipts and invoices.
Analyze this receipt/invoice image carefully and extract the information into a JSON object:
- "name": Store name and main purpose of the purchase (e.g., "Walmart - Groceries", "Shell - Fuel"). If store is not visible, summarize the items.
- "amount": Total final amount to pay as a float (e.g., 125.50). Pay special attention to "TOTAL", "SUM".
- "date": Date of purchase in YYYY-MM-DD format.
- "category": Match EXACTLY ONE of these categories: {', '.join(VALID_CATEGORIES)}. Default to "other".
- "notes": List 2-3 main items from the receipt (e.g., "milk, bread, eggs").

Return ONLY the raw JSON object.
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    
    # DEBUG: Wyświetl w terminalu dokładną odpowiedź od modelu AI
    print("\n--- AI MODEL RAW OUTPUT ---")
    print(response.text)
    print("---------------------------\n")
    
    try:
        # Clean up potential markdown formatting from the response
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        return data
    except json.JSONDecodeError:
        raise ValueError("Failed to parse AI response into JSON.")
