"""Page-builder editor (dash surface) — STAGING, behind BUILDER_ENABLED.

Access requires BOTH the flag AND membership in BUILDER_ALLOWLIST; anyone else
gets a plain 404 (no hint the surface exists). The editor edits a DRAFT
(users.sections_draft_json); publish copies the draft to the LIVE column
(users.sections_live_json), which is what the public page renders.

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

from .db import get_db
from .sections import (
    default_sections_from_profile,
    load_sections,
    resolve_sections,
    validate_sections,
)
from .security import login_required, use_public_csp

bp = Blueprint("builder", __name__)


def builder_required(view):
    """login + staging flag + allowlist. A non-allowlisted user must not be able
    to tell the surface exists, so every failure is the same 404."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_app.config.get("BUILDER_ENABLED"):
            abort(404)
        email = (g.user["email"] or "").lower()
        if email not in current_app.config.get("BUILDER_ALLOWLIST", frozenset()):
            abort(404)
        return view(*args, **kwargs)

    return wrapped


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
    return render_template(
        "dash_builder.html",
        draft_json=json.dumps(draft, separators=(",", ":")),
        plan=g.user["plan"],
        username=g.user["username"],
        is_published=published is not None,
    )


@bp.post("/dash/builder/save")
@builder_required
def save():
    """Autosave the draft. Returns {ok, error?} as JSON — the editor surfaces
    the error inline rather than navigating."""
    try:
        data = json.loads(request.form.get("sections") or "null")
    except ValueError:
        return jsonify(ok=False, error="that didn't parse 🤔"), 200
    clean, error = validate_sections(data, plan=g.user["plan"])
    if error:
        return jsonify(ok=False, error=error), 200
    db = get_db()
    db.execute(
        "UPDATE users SET sections_draft_json = ? WHERE id = ?",
        (json.dumps(clean, separators=(",", ":")), g.user["id"]),
    )
    db.commit()
    return jsonify(ok=True)


@bp.post("/dash/builder/publish")
@builder_required
def publish():
    """Validate the draft and copy it to the live column (and normalise the
    stored draft to the cleaned shape)."""
    try:
        data = json.loads(request.form.get("sections") or "null")
    except ValueError:
        return jsonify(ok=False, error="that didn't parse 🤔"), 200
    clean, error = validate_sections(data, plan=g.user["plan"])
    if error:
        return jsonify(ok=False, error=error), 200
    payload = json.dumps(clean, separators=(",", ":"))
    db = get_db()
    db.execute(
        "UPDATE users SET sections_draft_json = ?, sections_live_json = ? WHERE id = ?",
        (payload, payload, g.user["id"]),
    )
    db.commit()
    return jsonify(ok=True, url=f"/{g.user['username']}")


@bp.get("/dash/builder/preview")
@builder_required
def preview():
    """The live-preview iframe target: the REAL public section template rendered
    from the current draft, so the editor shows exactly what visitors get. Arms
    the public CSP (nonce'd inline style) so it styles correctly, and
    frame-ancestors 'self' lets our own dash embed it."""
    from .theme import load_theme, resolve_theme

    theme = resolve_theme(load_theme(g.user["theme_json"]))
    sections = resolve_sections(g.user["sections_draft_json"]) or _preview_sections()
    return render_template(
        "public_page_sections.html",
        t=theme,
        sections=sections,
        user=g.user,
        title=g.user["display_name"] or f"@{g.user['username']}",
        description="",
        canonical=f"{current_app.config['SITE_ORIGIN']}/{g.user['username']}",
        csp_nonce=use_public_csp(),
        preview_empty=not sections,
    )


def _preview_sections():
    # When the draft isn't saved yet, preview the in-memory synthesised default
    # so a first-time editor sees something rather than an empty frame.
    return resolve_sections(json.dumps(_current_draft()))
