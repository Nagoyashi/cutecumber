"""Dashboard: home view, one-shot username claim, profile editing.

Usernames are immutable once claimed in v0 (DECISIONS.md #3). The claim is
race-safe twice over: the UPDATE only fires `WHERE username IS NULL`, and the
UNIQUE constraint on users.username catches two people claiming the same name
in the same instant.

Profile saves re-render the form with submitted values on validation errors —
nobody loses a 500-character bio to a redirect.
"""

import time
from sqlite3 import IntegrityError

import bcrypt

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .constants import (
    AVATAR_EMOJI,
    PASSWORD_MAX_BYTES,
    TOMBSTONE_DAYS,
    AVATAR_GRADIENTS,
    BIO_MAX,
    DISPLAY_NAME_MAX,
    PRONOUNS_MAX,
    validate_username,
)
from .avatars import (
    AvatarError,
    delete_avatar_file,
    process_avatar,
    store_avatar,
)
from .db import get_db
from .extensions import limiter
from .security import login_required
from .theme import (
    COLOR_KEYS,
    ENUM_KEYS,
    PRESETS,
    THEME_VERSION,
    load_theme,
    resolve_theme,
    validate_theme,
)

bp = Blueprint("dash", __name__)


VALID_SECTIONS = ("links", "profile", "theme")


def _render_home(
    form: dict | None = None,
    add_form: dict | None = None,
    open_section: str | None = None,
):
    """Render the dashboard. `form` / `add_form` override field values after a
    failed save so nothing the user typed gets lost. `open_section` decides
    which collapsible section starts expanded (defaults to ?open=… or links)."""
    if open_section is None:
        requested = request.args.get("open", "")
        open_section = requested if requested in VALID_SECTIONS else "links"
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
    stored_theme = load_theme(g.user["theme_json"])
    return render_template(
        "dash_home.html",
        site_origin=current_app.config["SITE_ORIGIN"],
        form=form,
        add_form=add_form,
        links=user_links,
        avatar_emoji=AVATAR_EMOJI,
        avatar_gradients=AVATAR_GRADIENTS,
        t=resolve_theme(stored_theme),
        theme_preset=stored_theme["preset"],
        theme_overridden=bool(stored_theme.get("overrides")),
        presets=list(PRESETS),
        enums=ENUM_KEYS,
        open_section=open_section,
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

    # Tombstone gate: purge expired rows, then check the survivor list.
    cutoff = int(time.time()) - TOMBSTONE_DAYS * 86400
    db.execute("DELETE FROM username_tombstones WHERE freed_at <= ?", (cutoff,))
    db.commit()
    if db.execute(
        "SELECT 1 FROM username_tombstones WHERE username = ?", (username,)
    ).fetchone():
        flash("that username was set free recently and is resting for a bit — try another? 🌱", "error")
        return redirect(url_for("dash.home"))

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
    valid_avatar = (
        (kind == "emoji" and value in AVATAR_EMOJI)
        or (kind == "gradient" and value in AVATAR_GRADIENTS)
        or (kind == "image" and value == "keep" and g.user["avatar_kind"] == "image")
    )
    if not valid_avatar:
        return "that avatar isn't one of ours — pick one from the grid 🎀", None, None
    if kind == "image":
        value = g.user["avatar_value"]  # keep the existing upload
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

    upload = request.files.get("avatar_file")
    if upload is not None and upload.filename:
        # A fresh upload wins over whatever radio is checked.
        try:
            blob = process_avatar(upload.stream)
        except AvatarError as exc:
            flash(str(exc), "error")
            return _render_home(
                form={
                    "display_name": display_name,
                    "bio": bio,
                    "pronouns": pronouns,
                    "avatar": avatar,
                },
                open_section="profile",
            )
        error, kind, value = None, "image", store_avatar(g.user["id"], blob)
    else:
        error, kind, value = _validate_profile(display_name, bio, pronouns, avatar)
    if error:
        flash(error, "error")
        return _render_home(
            form={
                "display_name": display_name,
                "bio": bio,
                "pronouns": pronouns,
                "avatar": avatar,
            },
            open_section="profile",
        )

    # Data minimization: an uploaded photo that's been replaced or switched
    # away from gets deleted, not orphaned (DECISIONS.md #31).
    old_kind, old_value = g.user["avatar_kind"], g.user["avatar_value"]
    if old_kind == "image" and (kind != "image" or value != old_value):
        delete_avatar_file(old_value)

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
    return redirect(url_for("dash.home", open="profile", _anchor="profile"))


import json as _json


@bp.post("/dash/theme")
@limiter.limit("30 per 15 minutes")
@login_required
def theme_save():
    if not g.user["username"]:
        flash("claim your username first — then we'll make it pretty 🌱", "error")
        return redirect(url_for("dash.home"))


    action = request.form.get("action")
    preset = request.form.get("preset") or ""

    if action in ("preset", "reset"):
        # Applying a preset (or resetting) clears all fine-tuning.
        candidate = {"version": THEME_VERSION, "preset": preset, "overrides": {}}
    elif action == "save":
        overrides = {}
        for key in COLOR_KEYS:
            value = (request.form.get(key) or "").strip().lower()
            if value:
                overrides[key] = value
        for key in ENUM_KEYS:
            value = (request.form.get(key) or "").strip()
            if value:
                overrides[key] = value
        candidate = {"version": THEME_VERSION, "preset": preset, "overrides": overrides}
    else:
        abort(400)

    clean, error = validate_theme(candidate)
    if error:
        flash(error, "error")
        return redirect(url_for("dash.home", open="theme", _anchor="theme"))

    db = get_db()
    db.execute(
        "UPDATE users SET theme_json = ?, theme_version = ? WHERE id = ?",
        (_json.dumps(clean, separators=(",", ":")), clean["version"], g.user["id"]),
    )
    db.commit()
    flash("theme saved — your page is looking adorable 🎨", "success")
    return redirect(url_for("dash.home", open="theme", _anchor="theme"))


# ------------------------------------------------------------------ account

@bp.get("/dash/account")
@login_required
def account():
    return render_template("dash_account.html")

@bp.post("/dash/account/delete")
@limiter.limit("5 per hour")
@login_required
def account_delete():
    """Hard delete, immediately: user row goes, links cascade via the FK.
    Gated by the current password (the JS confirm is convenience, not the
    gate). The username becomes claimable again — see DECISIONS.md #29."""
    password = (request.form.get("password") or "").encode("utf-8")
    ok = False
    if 0 < len(password) <= PASSWORD_MAX_BYTES:
        ok = bcrypt.checkpw(password, g.user["password_hash"].encode("ascii"))
    if not ok:
        flash("that password doesn't match — nothing was deleted 💚", "error")
        return redirect(url_for("dash.account"))

    if g.user["avatar_kind"] == "image":
        delete_avatar_file(g.user["avatar_value"])
    db = get_db()
    if g.user["username"]:
        db.execute(
            "INSERT OR REPLACE INTO username_tombstones (username, freed_at)"
            " VALUES (?, ?)",
            (g.user["username"], int(time.time())),
        )
    db.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))
    db.commit()
    session.clear()
    flash("your account is deleted — everything is gone. take care out there 💚", "success")
    return redirect(url_for("auth.login"))
