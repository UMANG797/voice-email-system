"""
Email feature routes: compose/send, inbox, search, delete, drafts,
and linking a real mail account (Gmail address + App Password) for SMTP/IMAP.
"""

from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
from functools import wraps
from datetime import datetime
from models.database import get_db, log_activity
from utils.validators import is_valid_email, clean_text
from utils.crypto_utils import encrypt_value, decrypt_value
from utils.mail_utils import send_email, fetch_inbox, delete_email, MailError

email_bp = Blueprint("email_bp", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"ok": False, "message": "Please log in first."}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def _get_mail_credentials(user_id):
    conn = get_db()
    user = conn.execute(
        "SELECT mail_login_email, mail_app_password_encrypted FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if not user or not user["mail_login_email"] or not user["mail_app_password_encrypted"]:
        return None, None

    mail_password = decrypt_value(user["mail_app_password_encrypted"])

    if not mail_password:
        return user["mail_login_email"], None

    return user["mail_login_email"], mail_password


@email_bp.route("/mail-settings", methods=["GET", "POST"])
@login_required
def mail_settings():
    if request.method == "GET":
        conn = get_db()
        user = conn.execute("SELECT mail_login_email FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        return render_template("mail_settings.html", mail_login_email=user["mail_login_email"] if user else None)

    data = request.get_json(silent=True) or request.form
    mail_email = clean_text(data.get("mail_email", ""), 254).lower()
    app_password = data.get("app_password", "").replace(" ", "")

    if not is_valid_email(mail_email) or not app_password:
        return jsonify({"ok": False, "message": "Please provide a valid email and app password."}), 400

    encrypted = encrypt_value(app_password)
    conn = get_db()
    conn.execute(
        "UPDATE users SET mail_login_email = ?, mail_app_password_encrypted = ? WHERE id = ?",
        (mail_email, encrypted, session["user_id"]),
    )
    conn.commit()
    conn.close()
    log_activity(session["user_id"], "mail_settings_updated", mail_email)
    return jsonify({"ok": True, "message": "Mail account linked successfully. You can now send and read email."})


@email_bp.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    if request.method == "GET":
        return render_template("compose.html")

    data = request.get_json(silent=True) or request.form
    to_email = clean_text(data.get("to_email", ""), 254)
    subject = clean_text(data.get("subject", ""), 300)
    body = clean_text(data.get("body", ""), 10000)
    save_as_draft = data.get("save_as_draft", False)

    if not is_valid_email(to_email):
        return jsonify({"ok": False, "message": "The recipient email address is not valid."}), 400
    if not subject:
        return jsonify({"ok": False, "message": "Please provide a subject."}), 400
    if not body:
        return jsonify({"ok": False, "message": "The email body cannot be empty."}), 400

    if save_as_draft:
        conn = get_db()
        conn.execute(
            "INSERT INTO drafts (user_id, recipient, subject, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (session["user_id"], to_email, subject, body, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        log_activity(session["user_id"], "draft_saved", subject)
        return jsonify({"ok": True, "message": "Saved as a draft."})

  mail_email, app_password = _get_mail_credentials(session["user_id"])

    if not mail_email or not app_password:
        return jsonify({
            "ok": False,
            "message": "Please reconnect your Gmail account from Mail Settings."
        }), 400

    try:
        send_email(mail_email, app_password, to_email, subject, body)
    except MailError as e:
        return jsonify({"ok": False, "message": str(e)}), 502

    log_activity(session["user_id"], "email_sent", f"to={to_email} subject={subject}")
    return jsonify({"ok": True, "message": "Your email was sent successfully."})


@email_bp.route("/inbox")
@login_required
def inbox():
    return render_template("inbox.html")


@email_bp.route("/api/inbox")
@login_required
def api_inbox():
    mail_email, app_password = _get_mail_credentials(session["user_id"])
    if not mail_email:
        return jsonify({"ok": False, "message": "Please link your email account in Settings first."}), 400

    query = request.args.get("q", "").strip()
    search_criteria = None
    if query:
        safe_query = query.replace('"', "")
        search_criteria = f'(OR (OR SUBJECT "{safe_query}" FROM "{safe_query}") BODY "{safe_query}")'

    try:
        messages = fetch_inbox(mail_email, app_password, limit=20, search_criteria=search_criteria)
    except MailError as e:
        return jsonify({"ok": False, "message": str(e)}), 502

    return jsonify({"ok": True, "messages": messages, "unread_count": len(messages)})


@email_bp.route("/api/inbox/delete", methods=["POST"])
@login_required
def api_delete_email():
    data = request.get_json(silent=True) or {}
    msg_id = data.get("id")
    if not msg_id:
        return jsonify({"ok": False, "message": "No email specified for deletion."}), 400

    mail_email, app_password = _get_mail_credentials(session["user_id"])
    if not mail_email:
        return jsonify({"ok": False, "message": "Please link your email account in Settings first."}), 400

    try:
        delete_email(mail_email, app_password, msg_id)
    except MailError as e:
        return jsonify({"ok": False, "message": str(e)}), 502

    log_activity(session["user_id"], "email_deleted", f"id={msg_id}")
    return jsonify({"ok": True, "message": "Email deleted."})


@email_bp.route("/drafts")
@login_required
def drafts():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM drafts WHERE user_id = ? ORDER BY created_at DESC", (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("drafts.html", drafts=rows)


@email_bp.route("/api/drafts/<int:draft_id>/delete", methods=["POST"])
@login_required
def delete_draft(draft_id):
    conn = get_db()
    conn.execute("DELETE FROM drafts WHERE id = ? AND user_id = ?", (draft_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Draft deleted."})


@email_bp.route("/activity-log")
@login_required
def activity_log():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 100",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return render_template("activity_log.html", logs=rows)
