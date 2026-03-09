from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Please choose another.", "danger")
            return redirect(url_for("auth.register"))
            
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))
        
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
        
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))
            
        flash("Invalid username or password.", "danger")
        
    return render_template("auth/login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
