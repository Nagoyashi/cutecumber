"""CSRF protection, security headers, CSP, and the login_required decorator.

CSRF is home-rolled (DECISIONS.md #4): a random token stored in the signed
session, compared in constant time against a hidden `_csrf` form field on
EVERY mutating request, app-wide, via a before_request hook. There is no
exemption mechanism on purpose — if a route needs one, that's a design smell.
"""

import hmac
import secrets
from functools import wraps

from flask import abort, g, redirect, request, session, url_for

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
PUBLIC_CSP = (
    "default-src 'none'; style-src 'nonce-{nonce}'; img-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def use_public_csp() -> str:
    """Generate a per-request style nonce and arm the strict public CSP.

    Returns the nonce; templates put it on their single inline <style> tag.
    """
    nonce = secrets.token_urlsafe(16)
    g.csp = PUBLIC_CSP.format(nonce=nonce)
    return nonce


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


def apply_security_headers(response):
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
    # HSTS is added by the TLS-terminating proxy (Caddy) at deploy time.
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
