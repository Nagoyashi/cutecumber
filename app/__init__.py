"""cutecumber.cc — application factory.

Run (dev):   flask --app wsgi run --debug
Init DB:     flask --app wsgi init-db
Run (prod):  gunicorn -w 1 'wsgi:app'   (see DECISIONS.md #7 before raising workers)
"""

import os

from dotenv import load_dotenv
from flask import Flask, g, render_template, session

from . import auth, dash, db, links, mail, monitoring, public
from .extensions import limiter
from .security import (
    apply_security_headers,
    check_csrf,
    get_csrf_token,
    session_auth_fragment,
)


def create_app() -> Flask:
    load_dotenv()

    secret = os.environ.get("SECRET_KEY", "")
    if len(secret) < 32:
        raise RuntimeError(
            "SECRET_KEY is missing or shorter than 32 characters. cutecumber refuses "
            "to start with a weak session secret. Generate one with:\n"
            '    python -c "import secrets; print(secrets.token_hex(32))"\n'
            "and put it in your .env file (see .env.example)."
        )

    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.update(
        SECRET_KEY=secret,
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "cutecumber.db")
        ),
        # Uploaded avatars MUST land on persistent storage. On Fly the app dir
        # is ephemeral (wiped every deploy/restart), so prod points this at the
        # mounted volume (AVATAR_DIR=/data/avatars in fly.toml). Local dev keeps
        # them in instance/avatars. See issue #2.
        AVATAR_DIR=os.environ.get(
            "AVATAR_DIR", os.path.join(app.instance_path, "avatars")
        ),
        # Used to build canonical/OG URLs; never trust the Host header for those.
        SITE_ORIGIN=os.environ.get("SITE_ORIGIN", "http://localhost:5000").rstrip("/"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Secure-by-default; dev opts out via COOKIE_SECURE=0 in .env.
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,  # 30 days
        # Stealth by default: robots.txt serves Disallow: / until launch day.
        ROBOTS_ALLOW=os.environ.get("ROBOTS_ALLOW", "0") == "1",
        # HSTS comes from the app in prod (Fly terminates TLS, no Caddy layer).
        SEND_HSTS=os.environ.get("HSTS", "0") == "1",
        # Raised from 64 KB when avatar uploads shipped; the CSRF hook parses
        # the body before routes run, so this cap must be global (DECISIONS #31).
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )

    os.makedirs(app.config["AVATAR_DIR"], exist_ok=True)

    # Behind Caddy/nginx in prod, set TRUST_PROXY=1 so rate limiting keys on the
    # real client IP instead of the proxy's. Never set this when directly exposed.
    if os.environ.get("TRUST_PROXY") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    monitoring.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(dash.bp)
    app.register_blueprint(links.bp)
    app.register_blueprint(public.bp)

    app.jinja_env.globals["csrf_token"] = get_csrf_token

    @app.before_request
    def load_user() -> None:
        """Attach the logged-in user's row to g.user (None for anonymous).

        Anonymous visits to public pages never touch the DB or the session
        store here — public pages must stay cookie-free for visitors.
        """
        g.user = None
        uid = session.get("user_id")
        if uid is not None:
            g.user = (
                db.get_db()
                .execute("SELECT * FROM users WHERE id = ?", (uid,))
                .fetchone()
            )
            if g.user is None:  # stale cookie for a deleted account
                session.clear()
            elif session.get("auth") != session_auth_fragment(g.user["password_hash"]):
                # password changed since this session was issued — sign out
                session.clear()
                g.user = None

    app.before_request(check_csrf)
    app.after_request(apply_security_headers)

    @app.errorhandler(400)
    def bad_request(_e):
        return (
            render_template(
                "error.html",
                code=400,
                message="that didn't quite go through — mind refreshing the page and trying again? 🌱",
            ),
            400,
        )

    @app.errorhandler(404)
    def not_found(_e):
        return (
            render_template(
                "error.html",
                code=404,
                message="we looked everywhere and couldn't find that page 🍃",
            ),
            404,
        )

    @app.errorhandler(413)
    def too_large(_e):
        return (
            render_template(
                "error.html",
                code=413,
                message="that's a little too much for us to carry — try something smaller 🎒",
            ),
            413,
        )

    @app.errorhandler(429)
    def too_many_requests(_e):
        return (
            render_template(
                "error.html",
                code=429,
                message="whoa, that's a lot of tries — take a little breather and come back in a bit 🌸",
            ),
            429,
        )

    @app.errorhandler(500)
    def server_error(_e):
        return (
            render_template(
                "error.html",
                code=500,
                message="something went wrong on our side — it's not you, we promise 💚",
            ),
            500,
        )

    return app
