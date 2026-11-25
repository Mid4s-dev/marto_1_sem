"""
Flask application factory.
"""
import os
from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from app.models import db, User
from app.config import config_map
from app.audit_listeners import register_audit_listeners


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_name: str = None) -> Flask:
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_map.get(config_name, config_map["development"]))

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Audit ORM listeners
    register_audit_listeners(app)

    # Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.property.routes import property_bp
    from app.blueprints.finance.routes import finance_bp
    from app.blueprints.audit.routes import audit_bp
    from app.blueprints.reporting.routes import reporting_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(property_bp, url_prefix="/property")
    app.register_blueprint(finance_bp, url_prefix="/finance")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(reporting_bp, url_prefix="/reports")

    # Root redirect
    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("property.public_vacancies"))

    # Create tables in development / testing
    with app.app_context():
        db.create_all()
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            columns = {column["name"] for column in inspect(db.engine).get_columns("Units")}
            sqlite_columns = {
                "deposit": "NUMERIC(10, 2) NOT NULL DEFAULT 0",
                "description": "VARCHAR(500) NOT NULL DEFAULT ''",
                "image_url": "VARCHAR(500)",
                "bedrooms": "INTEGER NOT NULL DEFAULT 1",
                "bathrooms": "INTEGER NOT NULL DEFAULT 1",
            }
            for column_name, column_type in sqlite_columns.items():
                if column_name not in columns:
                    db.session.execute(text(f"ALTER TABLE Units ADD COLUMN {column_name} {column_type}"))
            db.session.commit()

    return app
