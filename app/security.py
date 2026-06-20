"""CSRF protection, security headers, CSP, and the login_required decorator.

CSRF is home-rolled (DECISIONS.md #4): a random token stored in the signed
session, compared in constant time against a hidden `_csrf` form field on
EVERY mutating request, app-wide, via a before_request hook. There is no
exemption mechanism on purpose — if a route needs one, that's a design smell.
"""

import hashlib
import hmac
import re
import secrets
from functools import wraps

from flask import abort, current_app, g, redirect, request, session, url_for

# Dash/auth pages: self-hosted stylesheet + the single editor script, plus
# frame-src 'self' for the live-preview iframe of the public page. Nothing
# looser than 'self' for anything, ever.
DASH_CSP = (
    "default-src 'none'; style-src 'self'; script-src 'self'; img-src 'self'; "
    "frame-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
)

# Public pages: zero JS, zero external requests, one nonce'd inline <style>.
# default-src 'none' means scripts cannot run even if markup were injected.
# frame-ancestors 'self' (not 'none') so OUR dash can embed the page as the
# live preview; anyone else framing it stays blocked (DECISIONS.md #20).
# img-src includes data: for the curated theme SVG layers (dots pattern,
# sparkles/hearts/stars) inlined as data URIs — inert image data, built
# server-side from validated tokens only (DECISIONS.md #21). font-src 'self'
# for the one optional self-hosted display font.
PUBLIC_CSP = (
    "default-src 'none'; style-src 'nonce-{nonce}'; img-src 'self' data:; "
    "font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def use_public_csp() -> str:
    """Generate a per-request style nonce and arm the strict public CSP.

    Returns the nonce; templates put it on their single inline <style> tag.
    """
    nonce = secrets.token_urlsafe(16)
    g.csp = PUBLIC_CSP.format(nonce=nonce)
    return nonce


# The password-reset link carries a single-use token in the URL path
# (GET /reset/<token>). It's short-lived and Referrer-Policy already blocks
# referer leakage, but logging it is avoidable exposure — a log reader could
# replay it inside the 1h window (issue #11). gunicorn's access logger runs
# this over each request path before writing the line (see gunicorn.conf.py).
_RESET_TOKEN_PATH_RE = re.compile(r"^(/reset/)[^/?\s]+")


def scrub_sensitive_path(uri: str) -> str:
    """Redact the reset token from a request target so it never hits the logs."""
    return _RESET_TOKEN_PATH_RE.sub(r"\g<1>[redacted]", uri)


def session_auth_fragment(password_hash: str) -> str:
    """Derived from the password hash and stored in the session at login.
    load_user rejects sessions whose fragment no longer matches — so changing
    the password (e.g. via reset) invalidates every other session, despite
    sessions being stateless signed cookies."""
    return hashlib.sha256(password_hash.encode("ascii")).hexdigest()[:16]


def get_csrf_token() -> str:
    """Lazily create the per-session CSRF token.

    Only called from templates that render a form, so anonymous visits to
    public pages never create a session (and therefore never set a cookie).
    """
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def check_csrf() -> None:
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("_csrf", "")
        expected = session.get("_csrf", "")
        if not sent or not expected or not hmac.compare_digest(sent, expected):
            abort(400)


# Static asset prefixes that are safe to cache forever. Fonts carry their
# version in the filename (fontsource naming); avatar/pack tiles are curated
# art whose filename IS the contract (the registry in constants.py / theme.py
# maps a token to a fixed path). They never change in place — a future art
# swap ships a NEW filename + registry entry (DECISIONS.md), so old URLs can
# stay cached without going stale. css/js keep Flask's default max-age.
_IMMUTABLE_STATIC_PREFIXES = (
    "/static/fonts/",
    "/static/avatars/",
    "/static/packs/",
)


def apply_security_headers(response):
    if request.path.startswith(_IMMUTABLE_STATIC_PREFIXES):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    response.headers.setdefault(
        "Content-Security-Policy", getattr(g, "csp", DASH_CSP)
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    # SAMEORIGIN (not DENY): must agree with frame-ancestors 'self' above.
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Privacy is the brand: never leak where visitors came from or go.
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if current_app.config.get("SEND_HSTS"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
