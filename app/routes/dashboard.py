from flask import Blueprint, render_template

from app.services import (
    get_total_cost,
    get_cost_by_category,
    get_monthly_summary,
    get_recent_expenses,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    total = get_total_cost()
    by_category = get_cost_by_category()
    monthly = get_monthly_summary()
    recent = get_recent_expenses(5)
    return render_template(
        "dashboard.html",
        total=total,
        by_category=by_category,
        monthly=monthly,
        recent=recent,
    )
