# PROJECT_STRUCTURE.md — cutecumber.cc

> Canonical file tree + code-placement conventions. Roadmap & status live in
> `project.md`; hard invariants (perf budget, security, stack, voice) in
> `RULES.md`; architectural *why* in `DECISIONS.md`. Update this file when the
> tree or a placement convention changes.

## File map

```
cutecumber/
├── wsgi.py                  WSGI entrypoint. Dev: flask --app wsgi run --debug
├── Dockerfile / entrypoint.sh / fly.toml / .dockerignore
│                            Fly.io deploy (DEPLOY.md is the runbook):
│                            restore-if-empty → init-db → gunicorn -w 1,
│                            Litestream wraps it when configured
├── gunicorn.conf.py         gunicorn config: access logger that redacts the
│                            reset token from logged paths (issue #11)
├── DEPLOY.md                Fly.io deploy + backup + launch-day runbook
├── requirements.txt         flask, bcrypt, python-dotenv, flask-limiter, gunicorn, pillow — closed list
├── .env.example             SECRET_KEY (mandatory), DATABASE, AVATAR_DIR, SITE_ORIGIN, COOKIE_SECURE, TRUST_PROXY
├── README.md                what it is + quickstart (public-facing)
├── project.md               canonical roadmap & phase log
├── RULES.md                 hard invariants: perf budget, security, stack, voice
├── CLAUDE.md                agent operating manual + task tracking (lean)
├── DESIGN_PACKS.md          spec for designer decoration packs
├── PROJECT_STRUCTURE.md     this file — tree + placement conventions
├── DECISIONS.md             architectural decisions + revisit conditions
└── app/
    ├── __init__.py          create_app(): config, loud SECRET_KEY failure, blueprint
    │                        registration, g.user loader, error handlers (400/404/413/429/500)
    ├── constants.py         RESERVED_USERNAMES, USERNAME_RE, all length caps,
    │                        validate_username(), AVATAR_SETS registry +
    │                        AVATAR_GRADIENTS, freeform-emoji validator. ONE
    │                        source of truth for limits.
    ├── db.py                get_db() (per-request conn, WAL, busy_timeout),
    │                        init-db CLI command (also runs idempotent column
    │                        upgrades — always safe to re-run)
    ├── schema.sql           users + links + username_tombstones (idempotent)
    ├── theme.py             THE theming engine (shape v2): PRESETS (6, AA-
    │                        enforced), validate_theme (save, strict),
    │                        resolve_theme (render, tolerant), computed
    │                        muted/accent_text/shadow, CSS + SVG-data-URI
    │                        builders, DECORATION_PACKS registry (multi, cap 5),
    │                        load_theme + MIGRATIONS (v1→v2 string→list).
    ├── security.py          CSRF (get_csrf_token/check_csrf), security headers,
    │                        DASH_CSP / PUBLIC_CSP + use_public_csp(), login_required
    ├── extensions.py        limiter (flask-limiter, memory storage)
    ├── avatars.py           uploaded-avatar pipeline: byte-identified,
    │                        EXIF/GPS stripped (test-enforced), 176px WebP,
    │                        ≤30 KB. Files in AVATAR_DIR (the volume in prod),
    │                        served at /a/.
    ├── auth.py              /signup /login (GET+POST, rate-limited POSTs),
    │                        POST /logout, /reset + /reset/<token> (password
    │                        reset: hashed single-use tokens, anti-enumeration)
    ├── mail.py              send_email() via Resend HTTP API (stdlib urllib,
    │                        no SDK). Dev mode: logs instead of sending.
    ├── monitoring.py        optional error reporting: POSTs unhandled-exception
    │                        JSON to ERROR_WEBHOOK_URL (stdlib urllib, no SDK,
    │                        no-op when unset). DECISIONS #36.
    ├── dash.py              GET /dash, POST /dash/claim (one-shot, race-safe),
    │                        POST /dash/profile (re-renders form on error),
    │                        GET /dash/account + POST /dash/account/delete
    │                        (password-gated hard delete)
    ├── links.py             POST /dash/links (add), POST /dash/links/<id>
    │                        (action=save|delete), POST /dash/links/reorder
    │                        (exact-permutation check). IDOR rule everywhere.
    ├── public.py            GET /, GET /<username> (OG tags), cute 404
    ├── templates/
    │   ├── public_page.html     standalone; inline nonce'd CSS; OG tags; ZERO JS
    │   ├── public_404.html      standalone; same rules
    │   ├── index.html           landing; same rules
    │   ├── dash_base.html       layout for everything logged-in/auth
    │   ├── auth_signup.html / auth_login.html / dash_home.html / error.html
    │   ├── imprint.html / privacy.html   legal pages (§5 DDG / GDPR)
    └── static/
        ├── favicon.svg          brand slice mark (also the inlined landing
        │                        logo); fixed colors, never themed (DECISIONS #34).
        ├── avatars/             12 curated kawaii SVG tiles = the 'set' avatar
        │                        kind; AVATAR_SETS in constants is the boundary
        │                        (DECISIONS #13 addendum). Served as static <img>.
        ├── packs/               decoration tiles, <pack>/<slug>.svg: 'basic'
        │                        (glyph picker thumbs) + 4 house packs.
        │                        DECORATION_PACKS in theme.py is the boundary
        │                        (DECISIONS #21/#30 addenda). url() backgrounds.
        ├── dash.css             dash side ONLY (public pages: inline CSS only).
        ├── fonts/               2 subsetted WOFF2 display fonts (fontsource via
        │                        npm). One loads per public page (h1); Fredoka
        │                        is also the chrome wordmark (DECISIONS #34).
        └── dash.js              the ONLY JS in the product: reorder, live
                                 preview, delete confirm. HARD 200-line budget
                                 (currently 130) — count before adding.
tests/
    ├── test_url_validation.py   run: python -m unittest -v  (from repo root)
    ├── test_theme.py            validator, migrations, WCAG AA on all presets
    └── test_avatar.py           EXIF/GPS stripping, sizing, rejection, storage dir
.github/
    ├── dependabot.yml           weekly pip + docker + github-actions updates
    │                            (no npm — 0-JS); targets main, grouped, chore:
    └── workflows/
        ├── ci.yml               runs the unittest suite + blocking pip-audit on
        │                        push + PRs to main (check name: `test` —
        │                        required on main; DECISIONS #35)
        └── release.yml          on a vX.Y.Z tag push, publishes the GitHub
                                 Release from docs/releases/<tag>.md + closes the
                                 same-named milestone. Canonical/unedited copy.
docs/releases/
    ├── README.md                release-notes index + the write-before-tag rule
    └── vX.Y.Z.md                one per release; H1 → Release title, body → notes
```

## Conventions

These are code-placement and pattern conventions. The hard invariants they
serve — the perf budget, the XSS/CSRF/IDOR security rules, the fixed stack, the
versioned-data rule, and the copy voice — are defined ONCE in `RULES.md` and are
not restated here.

**Two worlds, two rule sets.**
- *Public templates* (`public_page`, `public_404`, `index`): standalone, no
  `extends`, no static assets, one inline `<style nonce="{{ csp_nonce }}">`
  block, system fonts. Routes call `use_public_csp()` and pass the nonce; they
  never call `csrf_token()`.
- *Dash templates*: extend `dash_base.html`, load `static/dash.css`, get the
  strict `DASH_CSP`.

**Forms.** Every mutating route is a classic POST + redirect + flash carrying
the hidden `_csrf` field (enforcement lives in `security.py`; the rule in
`RULES.md`).

**Source of truth.** Limits, caps, and shared patterns live in `constants.py`
only. A new top-level route ⇒ add its name to `RESERVED_USERNAMES` in the same
commit.

**Queries.** Raw parameterised SQL only (never f-strings); every user-scoped
query carries `AND user_id = ?` — the IDOR line (`RULES.md`).

**Dash IA.** One slim page-live banner, then collapsible sections (`#links`,
`#profile`, `#theme`). Every mutating route redirects back to its own section
via `url_for("dash.home", open="<section>", _anchor="<section>")` — the query
param expands it server-side (fragments never reach the server), the anchor
scrolls there, the sticky flash persists. Any new dash section MUST follow this.

**Rate limits.** POST handlers decorate with `@limiter.limit(...)`. Current:
signup 5/hour, login 10/15min, claim 10/hour, profile 30/15min, link
add/edit/delete 60/15min each, theme 30/15min.

## How it runs

Dev: `flask --app wsgi init-db` then `flask --app wsgi run --debug`. Needs
`.env` with a ≥32-char `SECRET_KEY` or it refuses to start (on purpose).
Prod: `gunicorn -w 1 'wsgi:app'` on Fly.io (Fly terminates TLS; the app sets
HSTS). See `DEPLOY.md`. `TRUST_PROXY=1`, `COOKIE_SECURE=1` in prod.
