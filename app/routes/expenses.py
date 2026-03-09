import io
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, make_response, session
from flask_login import login_required, current_user
from app import db

from app.services import (
    get_all_expenses,
    get_expense_by_id,
    create_expense,
    update_expense,
    delete_expense,
    export_expenses_csv,
    parse_receipt_with_ai,
    VALID_CATEGORIES,
)
from app.models import Tag, Expense

expenses_bp = Blueprint("expenses", __name__)

def _get_all_categories(wallet_id):
    if not wallet_id: return VALID_CATEGORIES
    wallet_categories = [cat[0] for cat in db.session.query(Expense.category).filter_by(wallet_id=wallet_id).distinct().all()]
    return sorted(list(set(VALID_CATEGORIES + wallet_categories)))

@expenses_bp.route("/")
@login_required
def list_expenses():
    wallet_id = session.get("active_wallet_id")
    if not wallet_id: return redirect(url_for("wallets.create_wallet"))

    search = request.args.get("search", "")
    category = request.args.get("category", "")
    tag = request.args.get("tag", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    sort = request.args.get("sort", "date_desc")

    expenses = get_all_expenses(
        wallet_id,
        category=category or None,
        tag=tag or None,
        date_from=date_from or None,
        date_to=date_to or None,
        sort=sort,
        search=search or None,
    )
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "expenses/list.html",
        expenses=expenses,
        categories=_get_all_categories(wallet_id),
        all_tags=all_tags,
        filters={"search": search, "category": category, "tag": tag, "date_from": date_from, "date_to": date_to, "sort": sort},
    )

@expenses_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    wallet_id = session.get("active_wallet_id")
    if not wallet_id: return redirect(url_for("wallets.create_wallet"))

    if request.method == "POST":
        data = request.form.to_dict()
        data["tags"] = request.form.get("tags", "")
        # Try custom category
        if data.get("custom_category") and data["category"] == "custom":
            data["category"] = data["custom_category"]
            
        try:
            create_expense(data, wallet_id)
            flash("Expense added successfully.", "success")
            return redirect(url_for("expenses.list_expenses"))
        except ValueError as exc:
            flash(str(exc), "danger")
    
    prefilled_data = request.args.get("prefilled")
    expense_data = None
    if prefilled_data:
        import json
        try:
            expense_data = json.loads(prefilled_data)
            class DummyExpense:
                def __init__(self, d):
                    self.id = None
                    self.name = d.get("name", "")
                    self.category = d.get("category", "")
                    self.amount = d.get("amount", "")
                    self.date = d.get("date", "")
                    self.notes = d.get("notes", "")
                    self.tags = []
            expense_data = DummyExpense(expense_data)
        except json.JSONDecodeError:
            pass

    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template("expenses/form.html", expense=expense_data, categories=_get_all_categories(wallet_id), all_tags=all_tags)

@expenses_bp.route("/scan", methods=["GET", "POST"])
@login_required
def scan_receipt():
    if request.method == "POST":
        if "receipt" not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
        
        file = request.files["receipt"]
        if file.filename == "":
            flash("No selected file", "danger")
            return redirect(request.url)
            
        if file:
            try:
                image_bytes = file.read()
                mime_type = file.content_type
                
                parsed_data = parse_receipt_with_ai(image_bytes, mime_type)
                
                import json
                prefilled_json = json.dumps(parsed_data)
                
                flash("Receipt parsed successfully! Please review the details.", "success")
                return redirect(url_for("expenses.add_expense", prefilled=prefilled_json))
                
            except Exception as e:
                flash(f"Error parsing receipt: {str(e)}", "danger")
                return redirect(request.url)
                
    return render_template("expenses/scan.html")

@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    wallet_id = session.get("active_wallet_id")
    if not wallet_id: return redirect(url_for("wallets.create_wallet"))

    expense = get_expense_by_id(expense_id)
    if request.method == "POST":
        data = request.form.to_dict()
        data["tags"] = request.form.get("tags", "")
        if data.get("custom_category") and data["category"] == "custom":
            data["category"] = data["custom_category"]
            
        try:
            update_expense(expense_id, data, wallet_id)
            flash("Expense updated successfully.", "success")
            return redirect(url_for("expenses.list_expenses"))
        except ValueError as exc:
            flash(str(exc), "danger")
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template("expenses/form.html", expense=expense, categories=_get_all_categories(wallet_id), all_tags=all_tags)

@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense_view(expense_id):
    wallet_id = session.get("active_wallet_id")
    if not wallet_id: return redirect(url_for("wallets.create_wallet"))
    delete_expense(expense_id, wallet_id)
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))

@expenses_bp.route("/export/csv")
@login_required
def export_csv():
    wallet_id = session.get("active_wallet_id")
    if not wallet_id: return redirect(url_for("wallets.create_wallet"))

    category = request.args.get("category") or None
    tag = request.args.get("tag") or None
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None
    expenses = get_all_expenses(wallet_id, category=category, tag=tag, date_from=date_from, date_to=date_to)
    csv_data = export_expenses_csv(expenses)
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=expenses.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

