# PROJECT_STRUCTURE.md — cutecumber.cc

> Read this first, every session. Companion doc: `DECISIONS.md` (the *why* +
> revisit conditions). Update both proactively when changes warrant it.

**Status:** walking skeleton + profile editing complete (display name, bio,
pronouns, curated emoji/gradient avatar, rendered on the public page).
Links CRUD, preview/reorder JS, and the theming engine not started.

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
    ├── theme.py             versioned theme_json: default_theme(), load_theme(),
    │                        MIGRATIONS registry. Engine/validator: not yet built.
    ├── security.py          CSRF (get_csrf_token/check_csrf), security headers,
    │                        DASH_CSP / PUBLIC_CSP + use_public_csp(), login_required
    ├── extensions.py        limiter (flask-limiter, memory storage)
    ├── auth.py              /signup /login (GET+POST, rate-limited POSTs), POST /logout
    ├── dash.py              GET /dash, POST /dash/claim (one-shot, race-safe),
    │                        POST /dash/profile (re-renders form on error)
    ├── public.py            GET /, GET /<username> (OG tags), cute 404
    ├── templates/
    │   ├── public_page.html     standalone; inline nonce'd CSS; OG tags; ZERO JS
    │   ├── public_404.html      standalone; same rules
    │   ├── index.html           landing; same rules
    │   ├── dash_base.html       layout for everything logged-in/auth
    │   ├── auth_signup.html / auth_login.html / dash_home.html / error.html
    └── static/
        └── dash.css             dash side ONLY. Public pages never load static files.
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

**Copy voice.** Warm, soft, lowercase-ish, a little silly, never corporate.
Errors are kind and say what to do next.

**Rate limits** decorate POST handlers via `@limiter.limit(..., methods=["POST"])`
(or plain `@limiter.limit` on POST-only routes). Current: signup 5/hour,
login 10/15min, claim 10/hour, profile save 30/15min.

## How it runs

Dev: `flask --app wsgi init-db` then `flask --app wsgi run --debug`. Needs
`.env` with a ≥32-char `SECRET_KEY` or it refuses to start (on purpose).
Prod: `gunicorn -w 1 'wsgi:app'` behind Caddy; `TRUST_PROXY=1`, `COOKIE_SECURE=1`.

## v0 roadmap (ship in this order)

1. ~~Walking skeleton~~ ✅ this session
2. ~~Profile editing~~ ✅ — `avatar_value` column added; curated emoji +
   gradient allowlists (DECISIONS.md #13).
3. **Links CRUD** — add/edit/delete with title/url/emoji; URL scheme allowlist
   validated at save AND render; `rel="noopener noreferrer nofollow"`;
   **tests for the URL validator** (first tests in the repo).
4. **Reorder + live preview** — the only JS in the product, ≤200 lines total.
5. **Theming engine** — token validator (server-side, hex colors, allowlisted
   values), presets, per-user `<style>` rendering into the public page;
   **tests for the validator and for theme migrations**.
6. **Perf + polish pass** — verify ≤15 KB gzipped budget per public page,
   Lighthouse 100, LCP < 1.0s on simulated 4G.

Pre-launch blockers that aren't features: password reset story (DECISIONS.md
#9) and the deploy-target decision (DECISIONS.md #11).
