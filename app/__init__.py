from datetime import datetime, timezone

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name="default"):
    app = Flask(__name__)

    from app.config import config
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.expenses import expenses_bp
    from app.routes.tags import tags_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(tags_bp, url_prefix="/tags")

    @app.context_processor
    def inject_now():
        return {"now": datetime.now(timezone.utc)}

    return app
