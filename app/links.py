"""Link CRUD. New links append to the bottom; drag-to-reorder ships with the
editor-JS session.

Hard rules in this module:
- Every query carries `AND user_id = ?` (or keys on it). This is the IDOR line.
- No URL is stored without passing validate_link_url(); public.py runs the
  same check again at render. Save AND render, always.
- One form per link: the save and delete buttons share it via name="action".
"""

from flask import Blueprint, abort, flash, g, redirect, request, url_for

from .constants import (
    LINK_EMOJI_MAX,
    LINK_TITLE_MAX,
    MAX_LINKS_PER_PAGE,
    validate_link_url,
)
from .db import get_db
from .extensions import limiter
from .security import login_required

bp = Blueprint("links", __name__)


def _clean(form) -> tuple[str, str, str]:
    title = (form.get("title") or "").strip()
    url = (form.get("url") or "").strip()
    emoji = (form.get("emoji") or "").strip()
    return title, url, emoji


def _validate(title: str, url: str, emoji: str) -> tuple[str | None, str | None]:
    """Returns (normalized_url, error). error is None when everything is ok."""
    if not title:
        return None, "links need a title — what should people tap? 🌷"
    if len(title) > LINK_TITLE_MAX:
        return None, f"titles max out at {LINK_TITLE_MAX} characters ✂️"
    if len(emoji) > LINK_EMOJI_MAX:
        return None, "that emoji is a little much — keep it tiny 🤏"
    return validate_link_url(url)


@bp.post("/dash/links")
@limiter.limit("60 per 15 minutes")
@login_required
def add():
    from .dash import _render_home  # local import: dash imports nothing from here

    if not g.user["username"]:
        flash("claim your username first — then come add your links 🌱", "error")
        return redirect(url_for("dash.home"))

    title, url, emoji = _clean(request.form)
    db = get_db()

    count = db.execute(
        "SELECT COUNT(*) AS n FROM links WHERE user_id = ?", (g.user["id"],)
    ).fetchone()["n"]
    if count >= MAX_LINKS_PER_PAGE:
        flash(
            f"you've hit the {MAX_LINKS_PER_PAGE}-link limit — maybe prune a few? 🍂",
            "error",
        )
        return redirect(url_for("dash.home", open="links", _anchor="links"))

    normalized, error = _validate(title, url, emoji)
    if error:
        flash(error, "error")
        # Re-render with the submitted values so a pasted URL isn't lost.
        return _render_home(
            add_form={"title": title, "url": url, "emoji": emoji},
            open_section="links",
        )

    db.execute(
        "INSERT INTO links (user_id, title, url, emoji, position)"
        " SELECT ?, ?, ?, ?, COALESCE(MAX(position) + 1, 0)"
        " FROM links WHERE user_id = ?",
        (g.user["id"], title, normalized, emoji or None, g.user["id"]),
    )
    db.commit()
    flash("link added! ✨", "success")
    return redirect(url_for("dash.home", open="links", _anchor="links"))


@bp.post("/dash/links/reorder")
@limiter.limit("60 per 15 minutes")
@login_required
def reorder():
    """Persist a new link order submitted as a comma-separated list of ids.

    The submitted ids must be an EXACT permutation of this user's link ids —
    that simultaneously blocks foreign ids (IDOR), dropped/duplicated links,
    and stale tabs where a link was deleted elsewhere mid-drag.
    """
    raw = (request.form.get("order") or "").strip()
    try:
        ids = [int(part) for part in raw.split(",")] if raw else []
    except ValueError:
        abort(400)

    db = get_db()
    current = [
        row["id"]
        for row in db.execute(
            "SELECT id FROM links WHERE user_id = ?", (g.user["id"],)
        )
    ]
    if sorted(ids) != sorted(current):
        flash("that order looks out of date — refresh the page and try again 🌀", "error")
        return redirect(url_for("dash.home", open="links", _anchor="links"))

    db.executemany(
        "UPDATE links SET position = ? WHERE id = ? AND user_id = ?",
        [(position, link_id, g.user["id"]) for position, link_id in enumerate(ids)],
    )
    db.commit()
    flash("order saved ✨", "success")
    return redirect(url_for("dash.home", open="links", _anchor="links"))


@bp.post("/dash/links/<int:link_id>")
@limiter.limit("60 per 15 minutes")
@login_required
def modify(link_id: int):
    action = request.form.get("action")
    db = get_db()

    if action == "delete":
        cursor = db.execute(
            "DELETE FROM links WHERE id = ? AND user_id = ?",
            (link_id, g.user["id"]),
        )
        db.commit()
        if cursor.rowcount:
            flash("link deleted 🍂", "success")
        else:
            flash("hmm, we couldn't find that link 🤔", "error")
        return redirect(url_for("dash.home", open="links", _anchor="links"))

    if action == "save":
        title, url, emoji = _clean(request.form)
        normalized, error = _validate(title, url, emoji)
        if error:
            flash(error, "error")
            return redirect(url_for("dash.home", open="links", _anchor="links"))
        cursor = db.execute(
            "UPDATE links SET title = ?, url = ?, emoji = ?"
            " WHERE id = ? AND user_id = ?",
            (title, normalized, emoji or None, link_id, g.user["id"]),
        )
        db.commit()
        if cursor.rowcount:
            flash("link updated 💾", "success")
        else:
            flash("hmm, we couldn't find that link 🤔", "error")
        return redirect(url_for("dash.home", open="links", _anchor="links"))

    abort(400)
