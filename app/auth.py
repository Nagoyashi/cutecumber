"""Auth: email+password signup, login, logout.

- bcrypt with per-password salt; passwords capped at 72 BYTES because bcrypt
  4+/5 raises ValueError beyond that (verified, not assumed).
- Login does a dummy bcrypt check when the email is unknown so response time
  doesn't reveal which emails have accounts.
- Rate limits on the POST handlers only.
"""

import re
from sqlite3 import IntegrityError

import bcrypt
from flask import (
    Blueprint,
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
