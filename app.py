"""Flask application entry point for the Result Management System."""

import logging
import os

from flask import Flask

from config import Config


def create_app(config_class: type = Config) -> Flask:
    """Application factory that creates and configures the Flask app.

    Args:
        config_class: Configuration class to use (defaults to Config).

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure data directory exists
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin_routes import admin_bp
    from routes.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp, url_prefix="/student")

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=flask_app.config.get("DEBUG", True),
    )
