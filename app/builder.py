"""Page-builder editor (dash surface) — behind BUILDER_ENABLED.

Open to every authenticated creator when the flag is on; a flag-off request gets
a plain 404 (no hint the surface exists). BUILDER_ALLOWLIST is no longer the
access gate — it's the INTERNAL-TEST set, the only accounts that may flip their
own plan to exercise the premium tier before billing exists (see set_plan). The
editor edits a DRAFT (users.sections_draft_json); publish copies the draft to the
LIVE column (users.sections_live_json), which is what the public page renders.

The editor UI is vanilla JS (static/builder.js) under the dash CSP (script-src
'self'); the live preview is an <iframe> of /dash/builder/preview, which renders
the real public template from the draft so what you see is what visitors get.
"""

import json
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    render_template,
    request,
)

from .avatars import AvatarError, process_gallery_photo, store_avatar
from .db import get_db
from .extensions import limiter
from .sections import (
    default_sections_from_profile,
    has_code,
    has_embed,
    load_sections,
    resolve_sections,
    validate_sections_detailed,
)
from .security import login_required, use_public_csp
from .theme import THEME_VERSION, load_theme, resolve_theme, validate_theme

bp = Blueprint("builder", __name__)


def builder_required(view):
    """login + the BUILDER_ENABLED flag. Open to every authenticated creator; a
    flag-off request gets the same plain 404 (no hint the surface exists)."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_app.config.get("BUILDER_ENABLED"):
            abort(404)
        return view(*args, **kwargs)

    return wrapped


def _is_internal_tester() -> bool:
    """BUILDER_ALLOWLIST is no longer the access gate — it's the internal-test
    set: the only accounts allowed to flip their own plan to exercise the premium
    tier while it's 'coming soon' (real billing is a later cycle)."""
    email = (g.user["email"] or "").lower()
    return email in current_app.config.get("BUILDER_ALLOWLIST", frozenset())


def _current_draft():
    """The user's stored draft, or a freshly synthesised one from their profile
    on first visit (NOT persisted until they save). Always returns a dict."""
    draft = load_sections(g.user["sections_draft_json"])
    if draft is not None:
        return draft
    links = get_db().execute(
        "SELECT title, url, emoji FROM links WHERE user_id = ? ORDER BY position, id",
        (g.user["id"],),
    ).fetchall()
    return default_sections_from_profile(g.user, links)


@bp.get("/dash/builder")
@builder_required
def editor():
    draft = _current_draft()
    published = g.user["sections_live_json"]
    stored = load_theme(g.user["theme_json"])
    theme = resolve_theme(stored)
    # Page-theme CSS vars the in-document canvas paints itself with (theme.py is
    # the source of truth; the prototype's own palette is ignored).
    pg_vars = {
        "--pg-bg": theme["bg"], "--pg-bg2": theme["bg2"], "--pg-text": theme["text"],
        "--pg-muted": theme["muted"], "--pg-accent": theme["accent"],
        "--pg-accent-text": theme["accent_text"], "--pg-card": theme["surface"],
        "--pg-line": theme["line"],
    }
    return render_template(
        "dash_builder.html",
        draft_json=json.dumps(draft, separators=(",", ":")),
        plan=g.user["plan"],
        username=g.user["username"],
        is_published=published is not None,
        pg_vars=json.dumps(pg_vars, separators=(",", ":")),
        current_preset=stored.get("preset", ""),
        is_internal_tester=_is_internal_tester(),
    )


@bp.post("/dash/builder/save")
@limiter.limit("300 per hour")
@builder_required
def save():
    """Autosave the draft. Returns {ok, error?} as JSON — the editor surfaces
    the error inline rather than navigating."""
    try:
        data = json.loads(request.form.get("sections") or "null")
    except ValueError:
        return jsonify(ok=False, error="that didn't parse 🤔"), 200
    clean, error, at = validate_sections_detailed(data, plan=g.user["plan"])
    if error:
        return jsonify(ok=False, error=error, at=at), 200
    db = get_db()
    db.execute(
        "UPDATE users SET sections_draft_json = ? WHERE id = ?",
        (json.dumps(clean, separators=(",", ":")), g.user["id"]),
    )
    db.commit()
    return jsonify(ok=True)


@bp.post("/dash/builder/publish")
@limiter.limit("60 per hour")
@builder_required
def publish():
    """Validate the draft and copy it to the live column (and normalise the
    stored draft to the cleaned shape)."""
    try:
        data = json.loads(request.form.get("sections") or "null")
    except ValueError:
        return jsonify(ok=False, error="that didn't parse 🤔"), 200
    clean, error, at = validate_sections_detailed(data, plan=g.user["plan"])
    if error:
        return jsonify(ok=False, error=error, at=at), 200
    payload = json.dumps(clean, separators=(",", ":"))
    db = get_db()
    db.execute(
        "UPDATE users SET sections_draft_json = ?, sections_live_json = ? WHERE id = ?",
        (payload, payload, g.user["id"]),
    )
    db.commit()
    return jsonify(ok=True, url=f"/{g.user['username']}")


@bp.post("/dash/builder/upload")
@limiter.limit("40 per hour")
@builder_required
def upload():
    """Process one gallery photo through the avatar pipeline (re-encode strips
    EXIF/GPS) and return its stored filename for the editor to attach to a photo.
    The file is never served as-received; served from /a/ like avatars."""
    file = request.files.get("photo")
    if file is None or not file.filename:
        return jsonify(ok=False, error="pick a photo to upload 🌱"), 200
    try:
        blob = process_gallery_photo(file.stream)
    except AvatarError as exc:
        return jsonify(ok=False, error=str(exc)), 200
    filename = store_avatar(g.user["id"], blob)
    return jsonify(ok=True, filename=filename)


@bp.post("/dash/builder/preset")
@limiter.limit("120 per hour")
@builder_required
def set_preset():
    """Apply a theme preset (used by the starter-template picker). Plan-gated:
    a premium preset on a free plan is rejected, same as the dash theme save."""
    preset = request.form.get("preset") or ""
    clean, error = validate_theme(
        {"version": THEME_VERSION, "preset": preset, "overrides": {}},
        plan=g.user["plan"],
    )
    if error:
        return jsonify(ok=False, error=error), 200
    db = get_db()
    db.execute(
        "UPDATE users SET theme_json = ?, theme_version = ? WHERE id = ?",
        (json.dumps(clean, separators=(",", ":")), clean["version"], g.user["id"]),
    )
    db.commit()
    return jsonify(ok=True)


@bp.post("/dash/builder/plan")
@limiter.limit("30 per hour")
@builder_required
def set_plan():
    """INTERNAL-TEST ONLY: let an allowlisted tester flip their own plan so the
    premium tier can be exercised while it's 'coming soon'. Restricted to the
    BUILDER_ALLOWLIST — everyone else gets a 404 (they never see the toggle) — and
    it is NOT a real upgrade path; Stripe is a later decision."""
    if not _is_internal_tester():
        abort(404)
    plan = request.form.get("plan")
    if plan not in ("free", "sprout"):
        return jsonify(ok=False, error="unknown plan"), 200
    db = get_db()
    db.execute("UPDATE users SET plan = ? WHERE id = ?", (plan, g.user["id"]))
    db.commit()
    return jsonify(ok=True, plan=plan)


@bp.get("/dash/builder/preview")
@builder_required
def preview():
    """The live-preview iframe target: the REAL public section template rendered
    from the current draft, so the editor shows exactly what visitors get. Arms
    the public CSP (nonce'd inline style) so it styles correctly, and
    frame-ancestors 'self' lets our own dash embed it."""
    theme = resolve_theme(load_theme(g.user["theme_json"]))
    sections = resolve_sections(g.user["sections_draft_json"]) or _preview_sections()
    embeds, code = has_embed(sections), has_code(sections)
    return render_template(
        "public_page_sections.html",
        t=theme,
        sections=sections,
        user=g.user,
        title=g.user["display_name"] or f"@{g.user['username']}",
        description="",
        canonical=f"{current_app.config['SITE_ORIGIN']}/{g.user['username']}",
        has_embed=embeds,
        csp_nonce=use_public_csp(embeds=embeds, code=code),
        preview_empty=not sections,
    )


def _preview_sections():
    # When the draft isn't saved yet, preview the in-memory synthesised default
    # so a first-time editor sees something rather than an empty frame.
    return resolve_sections(json.dumps(_current_draft()))
