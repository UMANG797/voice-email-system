"""
Voice-Based Email System — main Flask application.

Run with:
    python app.py

First-time setup: copy .env.example to .env and fill in SECRET_KEY / FERNET_KEY.
"""

from flask import Flask, render_template, session, redirect, url_for, jsonify, request
from flask_wtf.csrf import CSRFProtect, CSRFError
from config import Config
from models.database import init_db, get_db
from routes.auth import auth_bp
from routes.email_routes import email_bp, login_required


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    csrf = CSRFProtect(app)
    # JSON API endpoints are same-origin fetch() calls from our own templates;
    # CSRF token is injected into every page and sent as a header (see base.html).
    app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]

    app.register_blueprint(auth_bp)
    app.register_blueprint(email_bp)

    with app.app_context():
        init_db()

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        mail_linked = bool(user["mail_login_email"]) if user else False
        return render_template("dashboard.html", user=user, mail_linked=mail_linked)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        message = "Your session has expired or is invalid. Please refresh the page and try again."
        if request.path.startswith("/api/") or request.is_json or request.accept_mimetypes.accept_json:
            return jsonify({"ok": False, "message": message}), 400
        return render_template("error.html", message=message), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", message="Something went wrong on our end. Please try again."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
