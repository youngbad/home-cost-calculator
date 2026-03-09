from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.models import Wallet, User
from app import db

wallets_bp = Blueprint("wallets", __name__)

@wallets_bp.route("/")
@login_required
def list_wallets():
    owned = current_user.owned_wallets.all()
    shared = current_user.shared_wallets
    return render_template("wallets/list.html", owned=owned, shared=shared)


@wallets_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_wallet():
    if request.method == "POST":
        name = request.form.get("name").strip()
        description = request.form.get("description", "").strip()
        
        if not name:
            flash("Wallet name is required.", "danger")
            return redirect(url_for("wallets.create_wallet"))
            
        wallet = Wallet(name=name, description=description, owner_id=current_user.id)
        db.session.add(wallet)
        db.session.commit()
        
        # Switch to the new wallet automatically
        session["active_wallet_id"] = wallet.id
        flash(f"Wallet '{name}' created!", "success")
        return redirect(url_for("dashboard.index"))
        
    return render_template("wallets/form.html", wallet=None)


@wallets_bp.route("/switch/<int:wallet_id>")
@login_required
def switch_wallet(wallet_id):
    wallet = db.session.get(Wallet, wallet_id)
    if wallet and (wallet.owner_id == current_user.id or current_user in wallet.shared_users):
        session["active_wallet_id"] = wallet.id
        flash(f"Switched to wallet: {wallet.name}", "success")
    else:
        flash("Wallet not found or access denied.", "danger")
    return redirect(url_for("dashboard.index"))


@wallets_bp.route("/<int:wallet_id>/edit", methods=["GET", "POST"])
@login_required
def edit_wallet(wallet_id):
    wallet = db.session.get(Wallet, wallet_id)
    if not wallet or wallet.owner_id != current_user.id:
        flash("You can only edit your own wallets.", "danger")
        return redirect(url_for("wallets.list_wallets"))
        
    if request.method == "POST":
        wallet.name = request.form.get("name").strip()
        wallet.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Wallet updated!", "success")
        return redirect(url_for("wallets.list_wallets"))
        
    return render_template("wallets/form.html", wallet=wallet)


@wallets_bp.route("/<int:wallet_id>/share", methods=["GET", "POST"])
@login_required
def share_wallet(wallet_id):
    wallet = db.session.get(Wallet, wallet_id)
    if not wallet or wallet.owner_id != current_user.id:
        flash("You can only share your own wallets.", "danger")
        return redirect(url_for("wallets.list_wallets"))
        
    if request.method == "POST":
        username = request.form.get("username").strip()
        if username == current_user.username:
            flash("You cannot share a wallet with yourself.", "warning")
        else:
            user = User.query.filter_by(username=username).first()
            if not user:
                flash("User not found.", "danger")
            elif user in wallet.shared_users:
                flash("User already has access to this wallet.", "info")
            else:
                wallet.shared_users.append(user)
                db.session.commit()
                flash(f"Wallet shared with {username}!", "success")
        return redirect(url_for("wallets.share_wallet", wallet_id=wallet_id))
        
    return render_template("wallets/share.html", wallet=wallet)

@wallets_bp.route("/<int:wallet_id>/unshare/<int:user_id>", methods=["POST"])
@login_required
def unshare_wallet(wallet_id, user_id):
    wallet = db.session.get(Wallet, wallet_id)
    if not wallet or wallet.owner_id != current_user.id:
        return redirect(url_for("wallets.list_wallets"))
        
    user = db.session.get(User, user_id)
    if user in wallet.shared_users:
        wallet.shared_users.remove(user)
        db.session.commit()
        flash(f"Revoked access for {user.username}.", "success")
        
    return redirect(url_for("wallets.share_wallet", wallet_id=wallet_id))
