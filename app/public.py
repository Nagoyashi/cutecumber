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
from .sections import has_code, has_embed, resolve_sections
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
            " avatar_value, theme_json, sections_live_json FROM users"
            " WHERE username = ?",
            (lowered,),
        )
        .fetchone()
    )
    if user is None:
        # A well-formed, non-reserved, unclaimed name → funnel: offer to claim it.
        return _not_found(claim_name=lowered)

    # Theme + OG metadata are needed by both render paths.
    theme = resolve_theme(load_theme(user["theme_json"]))
    title = user["display_name"] or f"@{user['username']}"
    description = (user["bio"] or DEFAULT_DESCRIPTION).strip()
    if len(description) > DESCRIPTION_MAX:
        description = description[: DESCRIPTION_MAX - 1].rstrip() + "…"
    canonical = f"{current_app.config['SITE_ORIGIN']}/{user['username']}"

    # The page builder is gated behind BUILDER_ENABLED on EVERY surface — creator
    # (dash) and visitor (here) alike — so flipping the flag off hides it entirely
    # while the code + data keep cooking. Off => the legacy links page renders and
    # there are no subpages / no site nav; the builder's home data is untouched and
    # comes straight back when the flag is on again.
    if current_app.config.get("BUILDER_ENABLED"):
        # Home + published subpages, for the zero-JS site nav (empty => only home).
        nav = _site_nav(get_db(), user, None)
        # When a live section stack exists, render it and skip the legacy links
        # path. resolve_sections is tolerant — a bad column yields [] and we fall
        # through to the legacy page.
        sections = resolve_sections(user["sections_live_json"])
        if sections:
            return _render_section_page(
                user, theme, sections, title, description, canonical, nav
            )
    else:
        nav = []

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
        nav=nav,
        csp_nonce=use_public_csp(),
    )


def _site_nav(db, user, current_slug):
    """Home + the user's PUBLISHED subpages, for the server-rendered site nav.
    current_slug is None on the home page. Returns [] when there's nothing to
    navigate to (only home) so the nav is hidden."""
    subs = db.execute(
        "SELECT slug, title FROM pages WHERE user_id = ?"
        " AND sections_live_json IS NOT NULL ORDER BY position, id",
        (user["id"],),
    ).fetchall()
    if not subs:
        return []
    base = "/" + user["username"]
    nav = [{"title": "home", "url": base, "current": current_slug is None}]
    for s in subs:
        nav.append({
            "title": s["title"],
            "url": f"{base}/{s['slug']}",
            "current": s["slug"] == current_slug,
        })
    return nav


def _render_section_page(user, theme, sections, title, description, canonical, nav):
    """Render a builder section stack (home or a subpage). CSP exceptions are
    armed ONLY for the section types actually present."""
    embeds, code = has_embed(sections), has_code(sections)
    return render_template(
        "public_page_sections.html",
        t=theme,
        sections=sections,
        user=user,
        title=title,
        description=description,
        canonical=canonical,
        has_embed=embeds,
        nav=nav,
        csp_nonce=use_public_csp(embeds=embeds, code=code),
    )


@bp.get("/<username>/<slug>")
def subpage(username: str, slug: str):
    """A creator's subpage at /<username>/<slug> — renders its published section
    stack, or the cute 404 if the page doesn't exist or isn't published yet."""
    if not current_app.config.get("BUILDER_ENABLED"):
        return _not_found()  # subpages don't exist while the builder is hidden
    lowered, lslug = username.lower(), slug.lower()
    if lowered != username or lslug != slug:
        return redirect(f"/{lowered}/{lslug}", code=301)
    if not USERNAME_RE.match(lowered) or lowered in RESERVED_USERNAMES:
        return _not_found()
    db = get_db()
    user = db.execute(
        "SELECT id, username, bio, theme_json FROM users WHERE username = ?",
        (lowered,),
    ).fetchone()
    if user is None:
        return _not_found()
    page = db.execute(
        "SELECT title, sections_live_json FROM pages WHERE user_id = ? AND slug = ?",
        (user["id"], lslug),
    ).fetchone()
    sections = resolve_sections(page["sections_live_json"]) if page else None
    if not sections:
        return _not_found()  # unknown or not-yet-published subpage
    theme = resolve_theme(load_theme(user["theme_json"]))
    title = f"{page['title']} · @{user['username']}"
    description = (user["bio"] or DEFAULT_DESCRIPTION).strip()
    if len(description) > DESCRIPTION_MAX:
        description = description[: DESCRIPTION_MAX - 1].rstrip() + "…"
    canonical = f"{current_app.config['SITE_ORIGIN']}/{user['username']}/{lslug}"
    nav = _site_nav(db, user, lslug)
    return _render_section_page(user, theme, sections, title, description, canonical, nav)


def _not_found(claim_name: str | None = None):
    # claim_name set => the path was a free, claimable username (funnel state);
    # None => a generic miss (reserved/malformed name, or a non-username path).
    return (
        render_template(
            "public_404.html", claim_name=claim_name, csp_nonce=use_public_csp()
        ),
        404,
    )
