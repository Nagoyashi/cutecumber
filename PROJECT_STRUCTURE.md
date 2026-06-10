# PROJECT_STRUCTURE.md — cutecumber.cc

> Read this first, every session. Companion doc: `DECISIONS.md` (the *why* +
> revisit conditions). Update both proactively when changes warrant it.

**Status:** v0 feature-complete — skeleton, profile, links, editor JS, and
the theming engine (6 AA-verified presets, token overrides, 2 self-hosted
display fonts). Remaining: the perf/polish pass, then launch prep.

## File map

```
cutecumber/
├── wsgi.py                  WSGI entrypoint. Dev: flask --app wsgi run --debug
├── requirements.txt         flask, bcrypt, python-dotenv, flask-limiter, gunicorn — closed list
├── .env.example             SECRET_KEY (mandatory), DATABASE, SITE_ORIGIN, COOKIE_SECURE, TRUST_PROXY
├── README.md                quickstart
├── PROJECT_STRUCTURE.md     this file
├── DECISIONS.md             decisions + revisit conditions
└── app/
    ├── __init__.py          create_app(): config, loud SECRET_KEY failure, blueprint
    │                        registration, g.user loader, error handlers (400/404/413/429/500)
    ├── constants.py         RESERVED_USERNAMES, USERNAME_RE, all length caps,
    │                        validate_username(), AVATAR_EMOJI + AVATAR_GRADIENTS
    │                        allowlists. ONE source of truth for limits.
    ├── db.py                get_db() (per-request conn, WAL, busy_timeout),
    │                        init-db CLI command (also runs idempotent column
    │                        upgrades — always safe to re-run)
    ├── schema.sql           users + links (links table pre-created, CRUD later)
    ├── theme.py             THE theming engine: PRESETS (6, AA-enforced by
    │                        tests), validate_theme (save path, strict),
    │                        resolve_theme (render path, tolerant), computed
    │                        muted/accent_text/shadow, CSS + SVG-data-URI
    │                        builders, load_theme + MIGRATIONS registry.
    ├── security.py          CSRF (get_csrf_token/check_csrf), security headers,
    │                        DASH_CSP / PUBLIC_CSP + use_public_csp(), login_required
    ├── extensions.py        limiter (flask-limiter, memory storage)
    ├── auth.py              /signup /login (GET+POST, rate-limited POSTs), POST /logout
    ├── dash.py              GET /dash, POST /dash/claim (one-shot, race-safe),
    │                        POST /dash/profile (re-renders form on error)
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
    └── static/
        ├── dash.css             dash side ONLY (public pages: inline CSS only).
        ├── fonts/               2 subsetted WOFF2 display fonts (fontsource
        │                        via npm). At most ONE loads per public page.
        └── dash.js              the ONLY JS in the product: reorder, live
                                 preview, delete confirm. HARD 200-line budget
                                 (currently 130) — count before adding.
tests/
    ├── test_url_validation.py   run: python -m unittest -v  (from repo root)
    └── test_theme.py            validator, migrations, WCAG AA on all presets
```

## Conventions

**Two worlds, two rule sets.**
- *Public templates* (`public_page`, `public_404`, `index`): standalone files,
  no `extends`, no static assets, one inline `<style nonce="{{ csp_nonce }}">`
  block, system fonts, zero JS, zero cookies. Routes that render them call
  `use_public_csp()` and pass the nonce. They never call `csrf_token()`.
- *Dash templates*: extend `dash_base.html`, load `static/dash.css`, get the
  default strict `DASH_CSP`.

**Forms.** Every mutating route is a classic POST + redirect with flash. Every
form includes `<input type="hidden" name="_csrf" value="{{ csrf_token() }}">`.
The CSRF check is a global before_request hook — there is no opt-out.

**Queries.** Raw SQL, always parameterised (`?`), never f-strings. Any query
touching a user-scoped table includes `AND user_id = ?` (or keys on it).

**Limits and patterns** live in `constants.py` only. New top-level route ⇒ add
its name to `RESERVED_USERNAMES` in the same commit.

**Stored JSON shapes** (currently `theme_json`) always carry `version` and load
through `theme.load_theme()`'s migration registry. Shape change ⇒ version bump
+ migration function, same commit.

**JavaScript.** One file (`static/dash.js`), vanilla, no dependencies, dash
side only, progressive enhancement (everything except reordering works with
JS off). 200-line hard budget; if a change would cross it, redesign first.
Public pages never load a script, full stop.

**Tests.** Stdlib unittest, `python -m unittest -v` from the repo root.
Only the URL validator, theme validator, and saved-shape migrations get
tests; trivial code does not.

**Copy voice.** Warm, soft, lowercase-ish, a little silly, never corporate.
Errors are kind and say what to do next.

**Rate limits** decorate POST handlers via `@limiter.limit(..., methods=["POST"])`
(or plain `@limiter.limit` on POST-only routes). Current: signup 5/hour,
login 10/15min, claim 10/hour, profile save 30/15min, link add/edit/delete
60/15min each, theme save 30/15min.

## How it runs

Dev: `flask --app wsgi init-db` then `flask --app wsgi run --debug`. Needs
`.env` with a ≥32-char `SECRET_KEY` or it refuses to start (on purpose).
Prod: `gunicorn -w 1 'wsgi:app'` behind Caddy; `TRUST_PROXY=1`, `COOKIE_SECURE=1`.

## v0 roadmap (ship in this order)

1. ~~Walking skeleton~~ ✅ this session
2. ~~Profile editing~~ ✅ — `avatar_value` column added; curated emoji +
   gradient allowlists (DECISIONS.md #13).
3. ~~Links CRUD~~ ✅ — validator at save AND render, IDOR-checked queries,
   50-link cap, URL-validator tests (DECISIONS.md #15–17).
4. ~~Reorder + live preview~~ ✅ — pointer-events drag + arrow keys, iframe
   preview of the real page, delete confirm (DECISIONS.md #19–20).
5. ~~Theming engine~~ ✅ — validator at save AND render, 6 presets with
   AA enforced by tests, fonts, backgrounds, decorations (DECISIONS.md #21–23).
   Scalloped button shape deferred (#22).
6. **Perf + polish pass** — verify ≤15 KB gzipped budget per public page,
   Lighthouse 100, LCP < 1.0s on simulated 4G.

Pre-launch blockers that aren't features: password reset story (DECISIONS.md
#9) and the deploy-target decision (DECISIONS.md #11).
