"""Dashboard: home view + one-shot username claim.

Usernames are immutable once claimed in v0 (DECISIONS.md #3). The claim is
race-safe twice over: the UPDATE only fires `WHERE username IS NULL`, and the
UNIQUE constraint on users.username catches two people claiming the same name
in the same instant.
"""

from sqlite3 import IntegrityError

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)

from .constants import validate_username
from .db import get_db
from .extensions import limiter
from .security import login_required

bp = Blueprint("dash", __name__)


@bp.get("/dash")
@login_required
def home():
    return render_template(
        "dash_home.html", site_origin=current_app.config["SITE_ORIGIN"]
    )


@bp.post("/dash/claim")
@limiter.limit("10 per hour")
@login_required
def claim():
    if g.user["username"]:
        flash("you've already claimed your username — it's yours forever 🌼", "error")
        return redirect(url_for("dash.home"))

    username = (request.form.get("username") or "").strip().lower()

    error = validate_username(username)
    if error:
        flash(error, "error")
        return redirect(url_for("dash.home"))

    db = get_db()
    try:
        cursor = db.execute(
            "UPDATE users SET username = ? WHERE id = ? AND username IS NULL",
            (username, g.user["id"]),
        )
        db.commit()
    except IntegrityError:
        flash("aw, someone got to that username first — try another! 🥲", "error")
        return redirect(url_for("dash.home"))

    if cursor.rowcount != 1:
        flash("you've already claimed your username — it's yours forever 🌼", "error")
        return redirect(url_for("dash.home"))

    flash("it's yours! your page is live ✨", "success")
    return redirect(url_for("dash.home"))
