from datetime import datetime, timezone

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_name="default"):
    app = Flask(__name__)

    from app.config import config
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.wallets import wallets_bp
    from app.routes.expenses import expenses_bp
    from app.routes.tags import tags_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(wallets_bp, url_prefix="/wallets")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(tags_bp, url_prefix="/tags")

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from flask import session
        from app.models import Wallet
        
        active_wallet = None
        if current_user.is_authenticated:
            wallet_id = session.get("active_wallet_id")
            if wallet_id:
                active_wallet = db.session.get(Wallet, wallet_id)
            if not active_wallet:
                # Fallback to first owned or shared wallet
                active_wallet = current_user.owned_wallets.first() or (current_user.shared_wallets[0] if current_user.shared_wallets else None)
                if active_wallet:
                    session["active_wallet_id"] = active_wallet.id
            
        return {
            "now": datetime.now(timezone.utc),
            "active_wallet": active_wallet
        }

    return app
