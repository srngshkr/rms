"""Admin authentication helpers: login_required decorator and auth routes."""

import logging
from functools import wraps
from typing import Callable

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


def login_required(f: Callable) -> Callable:
    """Decorator that redirects unauthenticated requests to the admin login page."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin panel.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        from flask import current_app

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admin_user = current_app.config.get("ADMIN_USERNAME")
        admin_pass = current_app.config.get("ADMIN_PASSWORD")

        if username == admin_user and password == admin_pass:
            session["admin_logged_in"] = True
            session["admin_username"] = username
            logger.info("Admin '%s' logged in.", username)
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin.dashboard"))
        else:
            logger.warning("Failed login attempt for username '%s'.", username)
            flash("Invalid username or password.", "danger")

    return render_template("admin/login.html")


@auth_bp.route("/admin/logout")
def logout():
    """Admin logout route."""
    username = session.pop("admin_username", "Unknown")
    session.pop("admin_logged_in", None)
    logger.info("Admin '%s' logged out.", username)
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
