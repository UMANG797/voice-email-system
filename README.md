# Voice-Based Email System

A Flask web app that lets a visually impaired (or hands-free) user register, log in,
compose/send, and read/search/delete email — all primarily by voice, using the browser's
built-in Speech Recognition (speech-to-text) and Speech Synthesis (text-to-speech), talking
to a Flask backend that sends real mail over SMTP and reads real mail over IMAP.

## A note on architecture (read this first)

The original spec asked for server-side PyAudio + SpeechRecognition for capturing voice,
and a biometric "voice-print" for login. Those don't actually work for a **web app**:

- A Flask server run on a computer somewhere has no access to the *microphone on the
  visitor's device* — `PyAudio` would only capture audio from whatever machine `app.py`
  happens to be running on, which is useless for a real user visiting the site.
- True voice-print (speaker recognition) biometrics requires a trained speaker-verification
  model and enrollment samples — a much bigger project than "build a working web app."

So this app uses the standard, correct architecture for browser-based voice:
**Web Speech API in the browser** (Chrome/Edge) for both speaking prompts aloud and
transcribing what the user says, sent to Flask as regular text. "Voice password" is
implemented honestly as a **spoken passphrase** checked like a second password — a
convenience, not biometric security. This is explained to the user on the registration page.

## What's fully implemented

- Registration & login (hashed password + spoken passphrase, with automatic fallback to
  typed password), session management, login-attempt lockout
- Voice-guided dashboard that speaks its menu and accepts spoken commands (Compose Email,
  Open Inbox, Drafts, Search Email, Settings, Activity Log, Logout, Help, Repeat, Stop)
- Compose: voice-guided recipient/subject/message capture, read-back, yes/no confirmation,
  and real sending via SMTP (Gmail by default)
- Inbox: real IMAP fetch, voice "Read Next / Repeat / Delete Email / Go Back", search by
  sender/subject/keyword, delete with confirmation
- Drafts (save/view/delete) and an Activity Log
- Security: password hashing (Werkzeug), encrypted-at-rest mail app-passwords (Fernet),
  CSRF protection (Flask-WTF), input validation, parameterized SQL (no string-built queries),
  Jinja2 auto-escaping (XSS), security response headers, login attempt rate-limiting
- Accessibility: skip link, ARIA live regions for spoken status, large tap targets, high
  contrast light/dark themes, full keyboard operability, semantic HTML

## What's simplified (and why)

- **Attachments**: send-side attachment support exists in `utils/mail_utils.py`
  (`send_email(..., attachments=[...])`) but isn't wired into the Compose UI yet, since
  voice-driven file selection needs a file picker, which is a mouse/keyboard action anyway.
  Reading attachments from Inbox mail is not implemented.
- **Forgot Password / Voice OTP**: not implemented. A real "forgot password" flow needs its
  own transactional email sending (a chicken-and-egg problem before the user has linked a
  mail account) — this is a good next feature to add once the app has its own transactional
  mail sender.
- **Sent Mail / Trash folders**: the Inbox page can fetch any IMAP folder
  (`fetch_inbox(..., folder=...)` in `utils/mail_utils.py` already supports this), but the
  UI only exposes the main Inbox folder today. Gmail's Sent/Trash folder names
  (`[Gmail]/Sent Mail`, `[Gmail]/Trash`) can be wired into a folder dropdown quickly.
- **Voice-print biometric login**: see architecture note above — implemented as a spoken
  passphrase instead.
- Tested primarily against **Gmail** (App Passwords + standard IMAP/SMTP). Other providers
  that support IMAP/SMTP with app passwords should work by changing `SMTP_HOST`/`IMAP_HOST`
  in `.env`, but haven't been tested here.

## Installation Guide

**Requirements:** Python 3.9+, a Gmail account with 2-Step Verification enabled (to generate
an App Password), and Google Chrome or Microsoft Edge (for Web Speech API support).

1. Extract the project and open a terminal in the `voice_email_system` folder.
2. Windows: double-click `install.bat` (or run it from a terminal).
   Mac/Linux: run `./install.sh`.
3. Generate your two secrets and put them in `.env`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"          # -> SECRET_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # -> FERNET_KEY
   ```
4. Start the app: Windows `run.bat`, Mac/Linux `./run.sh`. Or directly: `python app.py`.
5. Open `http://127.0.0.1:5000` in Chrome or Edge.
6. Register an account, then go to **Mail Settings** and link a Gmail address + an
   [App Password](https://myaccount.google.com/apppasswords) so Compose/Inbox work with
   real email.

## User Manual (quick reference)

| Say this on the Dashboard | It does |
|---|---|
| "Compose Email" | Opens Compose |
| "Open Inbox" | Opens Inbox |
| "Drafts" | Opens saved drafts |
| "Search Email" | Opens Inbox (then use the search box or say "search [term]") |
| "Mail Settings" | Opens the page to link your Gmail account |
| "Activity Log" | Shows your recent actions |
| "Logout" | Logs you out |
| "Help" | Repeats the list of commands |
| "Repeat" | Repeats the last spoken message |
| "Stop" | Stops the current speech |

In **Compose**, press "Compose by Voice" and answer the recipient/subject/message prompts;
the app reads the whole email back and asks "yes" or "no" before sending.

In **Inbox**, press "Voice Commands" and say "Read Next", "Repeat", "Delete Email", or
"Go Back". Typing in the search box also works without voice.

If your browser doesn't support voice (anything other than Chrome/Edge), every page still
works fully with the on-screen form fields and buttons.

## Developer Guide

```
voice_email_system/
├── app.py                  # Flask app factory, routes for /, /dashboard, error handlers
├── config.py                # Env-driven configuration
├── models/database.py       # SQLite schema + helper functions (no ORM)
├── routes/auth.py           # Register / login / logout
├── routes/email_routes.py   # Compose, inbox (API), drafts, mail settings, activity log
├── utils/mail_utils.py      # SMTP send + IMAP fetch/delete, wrapped in MailError
├── utils/crypto_utils.py    # Fernet encrypt/decrypt for stored app-passwords
├── utils/validators.py      # Email/password validation, input sanitisation
├── templates/                # Jinja2 templates (one per page) + base.html layout
├── static/js/voice.js        # Core speak()/listen() wrappers around Web Speech API
├── static/js/app.js          # CSRF-aware fetch helper, toast, dark mode toggle
└── static/css/style.css      # All styling (light + dark theme, responsive, accessible)
```

Database tables: `users`, `login_history`, `drafts`, `activity_logs` (see
`models/database.py` for exact schema). SQLite file is created automatically at
`database/voice_email.db` on first run.

To add a new voice command: add a phrase → URL mapping in the relevant template's
`<script>` block (see the `commands` object in `dashboard.html` for the pattern).

To add a new mail folder to Inbox: `fetch_inbox()` in `utils/mail_utils.py` already accepts
a `folder` argument — add a `<select>` to `inbox.html` and pass its value through
`api_inbox()` in `routes/email_routes.py`.

## Testing notes

Manually verified: registration validation (weak passwords, duplicate emails, invalid email
format rejected), login lockout after repeated failures, CSRF token required on all POST/API
routes, SQL injection attempts against login/search fields (parameterized queries prevent
these), XSS payloads in email subject/body (Jinja2 auto-escapes on render), SMTP/IMAP error
paths (wrong app password, no internet) return friendly spoken messages instead of stack
traces. Voice recognition itself can only be tested live in a browser with microphone
access — exercise it yourself in Chrome/Edge after installing.
