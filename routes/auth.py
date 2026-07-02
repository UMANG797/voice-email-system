"""
Authentication routes: registration, login (text password + a spoken
"voice password" phrase transcribed in the browser), logout.

Note on "voice password": true biometric voiceprint verification needs a
speaker-recognition model and enrolment audio samples, which is out of scope
for a from-scratch Flask app. Instead this app implements a *spoken passphrase*:
the browser transcribes what the user says (Web Speech API) and the resulting
text is checked like a second password. This is honest about what it is —
a convenience factor, not biometric security — and should not be relied on
as the sole protection for a real mailbox.
"""

from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models.database import get_db, log_login_attempt, log_activity, recent_failed_attempts
from utils.validators import is_valid_email, is_strong_password, clean_text
from config import Config

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    data = request.get_json(silent=True) or request.form
    name = clean_text(data.get("name", ""), 100)
    email = clean_text(data.get("email", ""), 254).lower()
    password = data.get("password", "")
    voice_password = clean_text(data.get("voice_password", ""), 100)

    if not name or not email or not password or not voice_password:
        return jsonify({"ok": False, "message": "All fields are required, including a spoken voice password."}), 400

    if not is_valid_email(email):
        return jsonify({"ok": False, "message": "That does not look like a valid email address."}), 400

    strong, msg = is_strong_password(password)
    if not strong:
        return jsonify({"ok": False, "message": msg}), 400

    if len(voice_password.split()) < 1:
        return jsonify({"ok": False, "message": "Please provide a voice password phrase."}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"ok": False, "message": "An account with this email already exists."}), 409

    conn.execute(
        """INSERT INTO users (name, email, password_hash, voice_password_hash, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            name,
            email,
            generate_password_hash(password),
            generate_password_hash(voice_password.lower()),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "Registration successful. You can now log in.", "redirect": url_for("auth.login")})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    data = request.get_json(silent=True) or request.form
    email = clean_text(data.get("email", ""), 254).lower()
    voice_password = clean_text(data.get("voice_password", ""), 100)
    text_password = data.get("text_password", "")

    ip = request.remote_addr or "unknown"

    if not is_valid_email(email):
        return jsonify({"ok": False, "message": "Please provide a valid email address."}), 400

    lockout_since = (datetime.utcnow() - timedelta(seconds=Config.LOGIN_LOCKOUT_SECONDS)).isoformat()
    if recent_failed_attempts(email, lockout_since) >= Config.MAX_LOGIN_ATTEMPTS:
        return jsonify({"ok": False, "message": "Too many failed attempts. Please try again in a few minutes."}), 429

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user:
        log_login_attempt(None, email, False, "unknown", ip)
        return jsonify({"ok": False, "message": "No account found with that email, or the password was incorrect."}), 401

    # Try voice password first
    if voice_password and check_password_hash(user["voice_password_hash"], voice_password.lower()):
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session.permanent = True
        log_login_attempt(user["id"], email, True, "voice", ip)
        log_activity(user["id"], "login", "Logged in via voice password")
        return jsonify({"ok": True, "message": f"Welcome back, {user['name']}.", "redirect": url_for("dashboard")})

    # Fall back to text password
    if text_password and check_password_hash(user["password_hash"], text_password):
        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session.permanent = True
        log_login_attempt(user["id"], email, True, "text_password", ip)
        log_activity(user["id"], "login", "Logged in via text password (voice password failed or skipped)")
        return jsonify({"ok": True, "message": f"Welcome back, {user['name']}.", "redirect": url_for("dashboard")})

    log_login_attempt(user["id"], email, False, "both_failed", ip)
    return jsonify({"ok": False, "message": "Login failed. Neither your voice password nor your text password matched."}), 401


@auth_bp.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "logout", "")
    session.clear()
    return redirect(url_for("index"))
