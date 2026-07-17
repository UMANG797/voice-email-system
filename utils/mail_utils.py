"""
Mail utilities: sending via SMTP and reading via IMAP, using each user's own
mail account credentials (e.g. a Gmail address + Gmail "App Password").

Every function raises a clear, caught exception type so routes can turn
failures into a friendly, speakable error message instead of a stack trace.
"""

import smtplib
import imaplib
import email as email_lib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from email.mime.application import MIMEApplication
from config import Config


class MailError(Exception):
    """Raised for any SMTP/IMAP failure, with a user-friendly message."""
    pass


def send_email(sender_email, app_password, to_email, subject, body, attachments=None):
    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        for att in (attachments or []):
            part = MIMEApplication(att["data"], Name=att["filename"])
            part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            msg.attach(part)

        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, to_email, msg.as_string())

    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Failure: {e}")
        raise MailError(f"Your email login was rejected by the mail server. Please check your app password. (Detail: {e})")
    except smtplib.SMTPRecipientsRefused as e:
        print(f"SMTP Recipients Refused: {e}")
        raise MailError("The recipient's email address was refused by the mail server.")
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        print(f"SMTP Error: {e}")
        raise MailError("Could not send the email. Please check your internet connection and try again.")


def _decode_str(value):
    if value is None:
        return ""
    decoded_parts = decode_header(value)
    result = ""
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="ignore")
        else:
            result += part
    return result


def _extract_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if content_type == "text/plain" and "attachment" not in disposition:
                try:
                    return part.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    continue
        return "(This message has no readable plain text body.)"
    else:
        try:
            return msg.get_payload(decode=True).decode(errors="ignore")
        except Exception:
            return "(This message has no readable plain text body.)"


def fetch_inbox(user_email, app_password, folder="INBOX", limit=15, search_criteria=None):
    """Returns a list of dicts: id, from, subject, date, body_preview (newest first)."""
    try:
        imap = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT, timeout=20)
        imap.login(user_email, app_password)
        imap.select(folder)

        criteria = search_criteria or "ALL"
        status, data = imap.search(None, criteria)
        if status != "OK":
            raise MailError("Could not search the mailbox.")

        ids = data[0].split()
        ids = ids[-limit:] if len(ids) > limit else ids
        ids.reverse()

        messages = []
        for msg_id in ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw_email)
            body = _extract_body(msg)
            messages.append({
                "id": msg_id.decode(),
                "from": _decode_str(msg.get("From")),
                "subject": _decode_str(msg.get("Subject")) or "(No subject)",
                "date": msg.get("Date") or "",
                "body": body.strip()[:3000],
            })

        imap.logout()
        return messages

    except imaplib.IMAP4.error as e:
        print(f"IMAP Authentication Failure: {e}")
        raise MailError(f"Your email login was rejected by the mail server. Please check your app password. (Detail: {e})")
    except (OSError, TimeoutError) as e:
        print(f"IMAP Connection Error: {e}")
        raise MailError("Could not connect to the mail server. Please check your internet connection.")


def delete_email(user_email, app_password, msg_id, folder="INBOX"):
    try:
        imap = imaplib.IMAP4_SSL(Config.IMAP_HOST, Config.IMAP_PORT, timeout=20)
        imap.login(user_email, app_password)
        imap.select(folder)
        imap.store(msg_id.encode() if isinstance(msg_id, str) else msg_id, "+FLAGS", "\\Deleted")
        imap.expunge()
        imap.logout()
    except imaplib.IMAP4.error as e:
        print(f"IMAP Delete Failure: {e}")
        raise MailError(f"Your email login was rejected by the mail server. (Detail: {e})")
    except (OSError, TimeoutError) as e:
        print(f"IMAP Delete Connection Error: {e}")
        raise MailError("Could not connect to the mail server. Please check your internet connection.")
