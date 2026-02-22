import io
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, make_response

from app.services import (
    get_all_expenses,
    get_expense_by_id,
    create_expense,
    update_expense,
    delete_expense,
    export_expenses_csv,
    VALID_CATEGORIES,
)
from app.models import Tag

expenses_bp = Blueprint("expenses", __name__)


# ---------------------------------------------------------------------------
# HTML views
# ---------------------------------------------------------------------------

@expenses_bp.route("/")
def list_expenses():
    category = request.args.get("category", "")
    tag = request.args.get("tag", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    sort = request.args.get("sort", "date_desc")

    expenses = get_all_expenses(
        category=category or None,
        tag=tag or None,
        date_from=date_from or None,
        date_to=date_to or None,
        sort=sort,
    )
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "expenses/list.html",
        expenses=expenses,
        categories=VALID_CATEGORIES,
        all_tags=all_tags,
        filters={"category": category, "tag": tag, "date_from": date_from, "date_to": date_to, "sort": sort},
    )


@expenses_bp.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        data = request.form.to_dict()
        data["tags"] = request.form.get("tags", "")
        try:
            create_expense(data)
            flash("Expense added successfully.", "success")
            return redirect(url_for("expenses.list_expenses"))
        except ValueError as exc:
            flash(str(exc), "danger")
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template("expenses/form.html", expense=None, categories=VALID_CATEGORIES, all_tags=all_tags)


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
def edit_expense(expense_id):
    expense = get_expense_by_id(expense_id)
    if request.method == "POST":
        data = request.form.to_dict()
        data["tags"] = request.form.get("tags", "")
        try:
            update_expense(expense_id, data)
            flash("Expense updated successfully.", "success")
            return redirect(url_for("expenses.list_expenses"))
        except ValueError as exc:
            flash(str(exc), "danger")
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template("expenses/form.html", expense=expense, categories=VALID_CATEGORIES, all_tags=all_tags)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
def delete_expense_view(expense_id):
    delete_expense(expense_id)
    flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/export/csv")
def export_csv():
    category = request.args.get("category") or None
    tag = request.args.get("tag") or None
    date_from = request.args.get("date_from") or None
    date_to = request.args.get("date_to") or None
    expenses = get_all_expenses(category=category, tag=tag, date_from=date_from, date_to=date_to)
    csv_data = export_expenses_csv(expenses)
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=expenses.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@expenses_bp.route("/api", methods=["GET"])
def api_list():
    expenses = get_all_expenses(
        category=request.args.get("category"),
        tag=request.args.get("tag"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        sort=request.args.get("sort", "date_desc"),
    )
    return jsonify([e.to_dict() for e in expenses])


@expenses_bp.route("/api", methods=["POST"])
def api_create():
    data = request.get_json(force=True)
    try:
        expense = create_expense(data)
        return jsonify(expense.to_dict()), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@expenses_bp.route("/api/<int:expense_id>", methods=["GET"])
def api_get(expense_id):
    return jsonify(get_expense_by_id(expense_id).to_dict())


@expenses_bp.route("/api/<int:expense_id>", methods=["PUT"])
def api_update(expense_id):
    data = request.get_json(force=True)
    try:
        expense = update_expense(expense_id, data)
        return jsonify(expense.to_dict())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@expenses_bp.route("/api/<int:expense_id>", methods=["DELETE"])
def api_delete(expense_id):
    delete_expense(expense_id)
    return jsonify({"message": "Deleted"}), 200
