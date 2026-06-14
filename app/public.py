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

from flask import (
    Blueprint,
    Response,
    current_app,
    redirect,
    render_template,
    send_from_directory,
)

from .constants import (
    AVATAR_EMOJI_MAX,
    AVATAR_GRADIENTS,
    AVATAR_SETS,
    DEFAULT_AVATAR_EMOJI,
    RESERVED_USERNAMES,
    USERNAME_RE,
    validate_link_url,
)
from .db import get_db
from .avatars import AVATAR_FILE_RE, avatar_dir
from .security import use_public_csp
from .theme import load_theme, resolve_theme

bp = Blueprint("public", __name__)

DEFAULT_DESCRIPTION = "✨ all my links, one cute little page ✨"
DESCRIPTION_MAX = 200  # OG description trim; full bio still renders on-page


@bp.get("/robots.txt")
def robots():
    """Stealth by default (DECISIONS.md #25): Disallow everything until
    ROBOTS_ALLOW=1 is set at launch. Can't collide with usernames — dots
    aren't in the username alphabet."""
    if current_app.config["ROBOTS_ALLOW"]:
        body = "User-agent: *\nDisallow:\n"
    else:
        body = "User-agent: *\nDisallow: /\n"
    return Response(body, mimetype="text/plain")


@bp.get("/a/<filename>")
def avatar_file(filename: str):
    """Processed avatars only — filenames are validated against our own
    pattern, and every file in that directory was produced by our pipeline.
    Filenames rotate on every upload, so immutable caching is safe."""
    if not AVATAR_FILE_RE.match(filename):
        return _not_found()
    response = send_from_directory(avatar_dir(), filename, mimetype="image/webp")
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@bp.get("/favicon.ico")
def favicon():
    """Browsers and crawlers request this unconditionally; without it every
    visit logged a 404 through the username route."""
    return current_app.send_static_file("favicon.svg")


@bp.get("/imprint")
def imprint():
    return render_template("imprint.html")


@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


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
            "SELECT id, username, display_name, bio, pronouns, avatar_kind,"
            " avatar_value, theme_json FROM users WHERE username = ?",
            (lowered,),
        )
        .fetchone()
    )
    if user is None:
        return _not_found()

    rows = (
        get_db()
        .execute(
            "SELECT title, url, emoji FROM links WHERE user_id = ?"
            " ORDER BY position, id",
            (user["id"],),
        )
        .fetchall()
    )
    # Validate at save AND render: a URL that no longer passes the allowlist
    # (corrupted row, rule tightened since save) is silently dropped — a bad
    # link must never reach a visitor's browser.
    links = [r for r in rows if validate_link_url(r["url"])[0] == r["url"]]

    # Resolve the avatar against the allowlists (validate at save AND render);
    # anything unrecognised falls back to the default emoji — a bad row must
    # never break a public page.
    gradient = None
    avatar_image = None
    avatar_set = None
    avatar_emoji = DEFAULT_AVATAR_EMOJI
    kind, value = user["avatar_kind"], user["avatar_value"] or ""
    if kind == "gradient":
        gradient = AVATAR_GRADIENTS.get(value)
    elif kind == "image" and AVATAR_FILE_RE.match(value):
        avatar_image = value
    elif kind == "set" and value in AVATAR_SETS:
        avatar_set = value
    elif kind == "emoji" and 0 < len(value) <= AVATAR_EMOJI_MAX:
        avatar_emoji = value

    title = user["display_name"] or f"@{user['username']}"
    description = (user["bio"] or DEFAULT_DESCRIPTION).strip()
    if len(description) > DESCRIPTION_MAX:
        description = description[: DESCRIPTION_MAX - 1].rstrip() + "…"

    canonical = f"{current_app.config['SITE_ORIGIN']}/{user['username']}"

    # Theme tokens: validated at save (dash) AND resolved tolerantly here —
    # a corrupted theme_json row falls back to the default preset.
    theme = resolve_theme(load_theme(user["theme_json"]))

    return render_template(
        "public_page.html",
        t=theme,
        user=user,
        title=title,
        description=description,
        canonical=canonical,
        gradient=gradient,
        avatar_image=avatar_image,
        avatar_set=avatar_set,
        avatar_emoji=avatar_emoji,
        links=links,
        csp_nonce=use_public_csp(),
    )


def _not_found():
    return render_template("public_404.html", csp_nonce=use_public_csp()), 404
