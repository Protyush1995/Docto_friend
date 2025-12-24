'''from flask import Flask
from .main import bp as main_bp

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY="dev")
    app.register_blueprint(main_bp)
    return app'''

import os
from flask import Flask
from .main import bp as main_bp

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Load secret key from environment for production; keep a development fallback.
    # In production set FLASK_SECRET_KEY to a strong random value (do NOT commit it).
    secret = os.environ.get("FLASK_SECRET_KEY")
    if not secret:
        # Development fallback: use a generated secure token if possible, else a fixed 'dev' for simple local runs.
        try:
            import secrets
            secret = secrets.token_urlsafe(32)
        except Exception:
            secret = "dev"

    app.config.from_mapping(SECRET_KEY=secret)

    # Optional recommended session cookie hardening (safe defaults; adjust for your environment)
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    # Set SESSION_COOKIE_SECURE=True when running over HTTPS in production
    app.config.setdefault("SESSION_COOKIE_SECURE", False)

    app.register_blueprint(main_bp)
    return app
