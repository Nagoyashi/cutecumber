"""Dashboard: home view, one-shot username claim, profile editing.

Usernames are immutable once claimed in v0 (DECISIONS.md #3). The claim is
race-safe twice over: the UPDATE only fires `WHERE username IS NULL`, and the
UNIQUE constraint on users.username catches two people claiming the same name
in the same instant.

Profile saves re-render the form with submitted values on validation errors —
nobody loses a 500-character bio to a redirect.
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

from .constants import (
    AVATAR_EMOJI,
    AVATAR_GRADIENTS,
    BIO_MAX,
    DISPLAY_NAME_MAX,
    PRONOUNS_MAX,
    validate_username,
)
from .db import get_db
from .extensions import limiter
from .security import login_required

bp = Blueprint("dash", __name__)


def _render_home(form: dict | None = None, add_form: dict | None = None):
    """Render the dashboard. `form` / `add_form` override field values after a
    failed save so nothing the user typed gets lost."""
    if form is None:
        form = {
            "display_name": g.user["display_name"] or "",
            "bio": g.user["bio"] or "",
            "pronouns": g.user["pronouns"] or "",
            "avatar": f"{g.user['avatar_kind']}:{g.user['avatar_value']}",
        }
    if add_form is None:
        add_form = {"title": "", "url": "", "emoji": ""}
    user_links = []
    if g.user["username"]:
        user_links = (
            get_db()
            .execute(
                "SELECT id, title, url, emoji FROM links"
                " WHERE user_id = ? ORDER BY position, id",
                (g.user["id"],),
            )
            .fetchall()
        )
    return render_template(
        "dash_home.html",
        site_origin=current_app.config["SITE_ORIGIN"],
        form=form,
        add_form=add_form,
        links=user_links,
        avatar_emoji=AVATAR_EMOJI,
        avatar_gradients=AVATAR_GRADIENTS,
    )


@bp.get("/dash")
@login_required
def home():
    return _render_home()


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


def _validate_profile(display_name: str, bio: str, pronouns: str, avatar: str):
    """Return (error_message, avatar_kind, avatar_value). error is None if ok."""
    if len(display_name) > DISPLAY_NAME_MAX:
        return f"display names max out at {DISPLAY_NAME_MAX} characters 🌷", None, None
    if len(bio) > BIO_MAX:
        return f"bios max out at {BIO_MAX} characters — short and sweet 🍬", None, None
    if len(pronouns) > PRONOUNS_MAX:
        return f"the pronouns field maxes out at {PRONOUNS_MAX} characters 🌱", None, None

    kind, _, value = avatar.partition(":")
    valid_avatar = (kind == "emoji" and value in AVATAR_EMOJI) or (
        kind == "gradient" and value in AVATAR_GRADIENTS
    )
    if not valid_avatar:
        return "that avatar isn't one of ours — pick one from the grid 🎀", None, None
    return None, kind, value


@bp.post("/dash/profile")
@limiter.limit("30 per 15 minutes")
@login_required
def profile():
    if not g.user["username"]:
        flash("claim your username first — then we'll make it cute 🌱", "error")
        return redirect(url_for("dash.home"))

    display_name = (request.form.get("display_name") or "").strip()
    bio = (request.form.get("bio") or "").strip()
    pronouns = (request.form.get("pronouns") or "").strip()
    avatar = (request.form.get("avatar") or "").strip()

    error, kind, value = _validate_profile(display_name, bio, pronouns, avatar)
    if error:
        flash(error, "error")
        return _render_home(
            form={
                "display_name": display_name,
                "bio": bio,
                "pronouns": pronouns,
                "avatar": avatar,
            }
        )

    db = get_db()
    db.execute(
        "UPDATE users SET display_name = ?, bio = ?, pronouns = ?,"
        " avatar_kind = ?, avatar_value = ? WHERE id = ?",
        (
            display_name or None,
            bio or None,
            pronouns or None,
            kind,
            value,
            g.user["id"],
        ),
    )
    db.commit()
    flash("saved! your page is looking adorable 💕", "success")
    return redirect(url_for("dash.home"))
