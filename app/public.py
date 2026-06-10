"""Public pages: landing (/) and profile pages (/<username>).

Hard rules for everything in this blueprint:
- Server-rendered HTML only. Zero JavaScript. Zero third-party requests.
- No cookies are set for anonymous visitors: these views never touch the
  session, and their templates never call csrf_token().
- OG tags in the initial HTML — crawlers don't run JS, and link unfurls in
  bios are the whole point.
- Strict CSP (default-src 'none') with a per-request nonce for the single
  inline <style> block, which is also where per-user theming will land.
"""

from flask import Blueprint, current_app, redirect, render_template

from .constants import RESERVED_USERNAMES, USERNAME_RE
from .db import get_db
from .security import use_public_csp

bp = Blueprint("public", __name__)

DEFAULT_DESCRIPTION = "✨ all my links, one cute little page ✨"
DESCRIPTION_MAX = 200  # OG description trim; full bio still renders on-page


@bp.get("/")
def index():
    return render_template("index.html", csp_nonce=use_public_csp())


@bp.get("/<username>")
def profile(username: str):
    # Case-insensitive URLs, one canonical form: redirect AnyCase -> lowercase.
    lowered = username.lower()
    if lowered != username:
        return redirect("/" + lowered, code=301)

    # Cheap shape check before touching the DB; reserved names 404 here even
    # if a route for them doesn't exist yet.
    if not USERNAME_RE.match(lowered) or lowered in RESERVED_USERNAMES:
        return _not_found()

    user = (
        get_db()
        .execute(
            "SELECT username, display_name, bio, pronouns FROM users"
            " WHERE username = ?",
            (lowered,),
        )
        .fetchone()
    )
    if user is None:
        return _not_found()

    title = user["display_name"] or f"@{user['username']}"
    description = (user["bio"] or DEFAULT_DESCRIPTION).strip()
    if len(description) > DESCRIPTION_MAX:
        description = description[: DESCRIPTION_MAX - 1].rstrip() + "…"

    canonical = f"{current_app.config['SITE_ORIGIN']}/{user['username']}"

    return render_template(
        "public_page.html",
        user=user,
        title=title,
        description=description,
        canonical=canonical,
        csp_nonce=use_public_csp(),
    )


def _not_found():
    return render_template("public_404.html", csp_nonce=use_public_csp()), 404
