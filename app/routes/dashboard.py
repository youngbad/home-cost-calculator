from flask import Blueprint, render_template, redirect, url_for, session
from flask_login import login_required, current_user

from app.services import (
    get_total_cost,
    get_cost_by_category,
    get_monthly_summary,
    get_recent_expenses,
    get_largest_expense,
    VALID_CATEGORIES,
)
from app.models import Wallet
from app import db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    wallet_id = session.get("active_wallet_id")
    if not wallet_id:
        active_wallet = current_user.owned_wallets.first() or (current_user.shared_wallets[0] if current_user.shared_wallets else None)
        if not active_wallet:
            return redirect(url_for("wallets.create_wallet"))
        wallet_id = active_wallet.id
        session["active_wallet_id"] = wallet_id
        
    total = get_total_cost(wallet_id)
    by_category = get_cost_by_category(wallet_id)
    monthly = get_monthly_summary(wallet_id)
    recent = get_recent_expenses(wallet_id, 5)
    largest = get_largest_expense(wallet_id)
    
    # Custom Categories handling in next steps, but keeping VALID_CATEGORIES for base list
    # Let's get unique categories from this wallet
    from app.models import Expense
    wallet_categories = [cat[0] for cat in db.session.query(Expense.category).filter_by(wallet_id=wallet_id).distinct().all()]
    all_categories = sorted(list(set(VALID_CATEGORIES + wallet_categories)))
    
    # Example budget goal - we can move this to Wallet model later
    budget = 100000.0
    budget_percentage = min((total / budget) * 100, 100) if budget > 0 else 0

    return render_template(
        "dashboard.html",
        total=total,
        by_category=by_category,
        monthly=monthly,
        recent=recent,
        largest=largest,
        categories=all_categories,
        budget=budget,
        budget_percentage=budget_percentage,
    )
