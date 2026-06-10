"""Auth: email+password signup, login, logout.

- bcrypt with per-password salt; passwords capped at 72 BYTES because bcrypt
  4+/5 raises ValueError beyond that (verified, not assumed).
- Login does a dummy bcrypt check when the email is unknown so response time
  doesn't reveal which emails have accounts.
- Rate limits on the POST handlers only.
"""

import hashlib
import re
import secrets
import time
from sqlite3 import IntegrityError

import bcrypt
from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .constants import EMAIL_MAX, PASSWORD_MAX_BYTES, PASSWORD_MIN
from .db import get_db
from .extensions import limiter
from .mail import send_email
from .security import session_auth_fragment
from .theme import default_theme_json

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Burned once at import; used to equalise timing for unknown emails.
_DUMMY_HASH = bcrypt.hashpw(b"cutecumber-dummy-password", bcrypt.gensalt())


def _validate_signup(email: str, password: str) -> str | None:
    if not email or len(email) > EMAIL_MAX or not EMAIL_RE.match(email):
        return "that email doesn't look quite right — mind double-checking it? 🤔"
    if len(password) < PASSWORD_MIN:
        return f"passwords need at least {PASSWORD_MIN} characters — make it a long cozy one 🔐"
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return "that password is a little too long — 72 characters is our max 🙈"
    return None


@bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def signup():
    if g.user is not None:
        return redirect(url_for("dash.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        error = _validate_signup(email, password)
        if error is None:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("ascii")
            db = get_db()
            try:
                cursor = db.execute(
                    "INSERT INTO users (email, password_hash, theme_json)"
                    " VALUES (?, ?, ?)",
                    (email, password_hash, default_theme_json()),
                )
                db.commit()
            except IntegrityError:
                error = "there's already an account with that email — try logging in instead 💌"
            else:
                session.clear()
                session["user_id"] = cursor.lastrowid
                session["auth"] = session_auth_fragment(password_hash)
                session.permanent = True
                flash("welcome to cutecumber! let's get you a username 🥒", "success")
                return redirect(url_for("dash.home"))

        flash(error, "error")

    return render_template("auth_signup.html")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per 15 minutes", methods=["POST"])
def login():
    if g.user is not None:
        return redirect(url_for("dash.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password_bytes = (request.form.get("password") or "").encode("utf-8")

        row = (
            get_db()
            .execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (email,)
            )
            .fetchone()
        )

        if len(password_bytes) > PASSWORD_MAX_BYTES:
            # bcrypt 5 raises past 72 bytes; no stored password can be this
            # long anyway. Burn a hash so timing stays uniform, then fail.
            bcrypt.checkpw(b"x", _DUMMY_HASH)
            ok = False
        else:
            stored = row["password_hash"].encode("ascii") if row else _DUMMY_HASH
            ok = bcrypt.checkpw(password_bytes, stored) and row is not None

        if ok:
            session.clear()
            session["user_id"] = row["id"]
            session["auth"] = session_auth_fragment(row["password_hash"])
            session.permanent = True
            flash("welcome back! 🌷", "success")
            return redirect(url_for("dash.home"))

        flash("hmm, that email and password don't match anything we know 🥺", "error")

    return render_template("auth_login.html")


@bp.post("/logout")
def logout():
    session.clear()
    flash("logged out — see you soon! 👋", "success")
    return redirect(url_for("auth.login"))


# ------------------------------------------------------------ password reset

RESET_TOKEN_TTL = 60 * 60  # 1 hour

_NEUTRAL_RESET_MESSAGE = (
    "if that email has a cutecumber account, a reset link is on its way 💌"
)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _valid_reset_user(token: str):
    """Return the user row for a live, unexpired token — else None.
    Tokens are stored hashed, so a database leak leaks nothing usable."""
    if not token or len(token) > 128:
        return None
    return (
        get_db()
        .execute(
            "SELECT id, email, password_hash FROM users"
            " WHERE reset_token_hash = ? AND reset_expires > ?",
            (_token_hash(token), int(time.time())),
        )
        .fetchone()
    )


@bp.route("/reset", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def reset_request():
    if g.user is not None:
        return redirect(url_for("dash.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        row = (
            get_db()
            .execute("SELECT id FROM users WHERE email = ?", (email,))
            .fetchone()
        )
        if row is not None:
            token = secrets.token_urlsafe(32)
            db = get_db()
            db.execute(
                "UPDATE users SET reset_token_hash = ?, reset_expires = ?"
                " WHERE id = ?",
                (_token_hash(token), int(time.time()) + RESET_TOKEN_TTL, row["id"]),
            )
            db.commit()
            link = f"{current_app.config['SITE_ORIGIN']}/reset/{token}"
            send_email(
                email,
                "reset your cutecumber password 🥒",
                "hi!\n\nsomeone (hopefully you) asked to reset the password for"
                " this cutecumber account.\n\nreset it here (link is good for"
                f" one hour):\n{link}\n\nif this wasn't you, you can safely"
                " ignore this email — your password hasn't changed.\n\n— the"
                " cutecumber garden 🥒",
            )
        # Same message either way: no account enumeration.
        flash(_NEUTRAL_RESET_MESSAGE, "success")
        return redirect(url_for("auth.login"))

    return render_template("auth_reset_request.html")


@bp.route("/reset/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reset_with_token(token: str):
    user = _valid_reset_user(token)
    if user is None:
        flash("that reset link is expired or already used — request a fresh one 🌱", "error")
        return redirect(url_for("auth.reset_request"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        if len(password) < PASSWORD_MIN:
            flash(f"passwords need at least {PASSWORD_MIN} characters — make it a long cozy one 🔐", "error")
            return render_template("auth_reset_form.html", token=token)
        if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
            flash("that password is a little too long — 72 characters is our max 🙈", "error")
            return render_template("auth_reset_form.html", token=token)

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("ascii")
        db = get_db()
        db.execute(
            "UPDATE users SET password_hash = ?, reset_token_hash = NULL,"
            " reset_expires = NULL WHERE id = ?",
            (password_hash, user["id"]),
        )
        db.commit()
        # Single-use token consumed; every old session is now invalid because
        # the auth fragment changed. Sign them straight in here.
        session.clear()
        session["user_id"] = user["id"]
        session["auth"] = session_auth_fragment(password_hash)
        session.permanent = True
        flash("password updated — welcome back! 🌷", "success")
        return redirect(url_for("dash.home"))

    return render_template("auth_reset_form.html", token=token)
