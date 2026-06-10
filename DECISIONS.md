# DECISIONS.md — cutecumber.cc

> The *why* behind each choice, with the condition that would reopen it.
> If you're about to argue with a pattern, read its entry first.

## 1. App factory + blueprints (`create_app()`)

Three blueprints (auth, dash, public) matching the product's two worlds plus
auth. Factory pattern so tests can build isolated apps with their own config.
**Revisit:** never, realistically — this is load-bearing and cheap.

## 2. Raw sqlite3, WAL, per-request connections, no ORM

Read-heavy workload, one box, tiny schema. WAL gives concurrent readers during
writes; `busy_timeout=5000` absorbs writer contention. Per-request connections
opened lazily in `g` — SQLite connections are cheap and this avoids
threading/pooling complexity entirely.
**Revisit (Postgres):** only with a MEASURED trigger: sustained SQLITE_BUSY
errors under real traffic, or a demonstrated need for a second app server.
If either fires, the migration gets proposed unprompted.
**Portability guardrails (added after re-litigating this, June 2026):** to
keep the exit an afternoon — standard SQL only (no SQLite-only features in
app queries), strict column typing (ints as ints, ISO timestamps), all SQL
lives in the modules. The migration cost analysis: ~a day of driver/DDL work
at any point in time, plus an hours-long cutover ceremony if users exist;
data volumes (10k users ≈ tens of MB) copy in under a minute.

## 3. Usernames are immutable after claim (v0)

The URL *is* the product; renames break every bio link the user has pasted,
free old names for impersonation, and complicate the reserved/unique logic.
One-shot claim is race-safe twice: `UPDATE ... WHERE username IS NULL` plus
the UNIQUE constraint.
**Revisit:** real users asking for renames. If granted: cooldown + old-name
tombstone to block instant impersonation.

## 4. Home-rolled CSRF (no flask-wtf)

flask-wtf isn't on the dependency list and drags in WTForms for what is ~20
lines: random token in the signed session, hidden field, constant-time compare
in a global before_request hook. No exemption mechanism exists on purpose.
**Revisit:** if we ever serve a JSON API (would need header-token variant).

## 5. theme_json is versioned from day one; links table pre-created

Every stored theme blob carries `version: 1` and loads through a migration
registry (`app/theme.py`), even though the theming engine doesn't exist yet —
retrofitting versioning after real rows exist is exactly the migration pain
this avoids. Same logic for creating `links` in the initial schema: an empty
table is free; an early-v0 migration is not.
**Rule, not revisitable:** no stored-shape change without version bump +
migration in the same commit.

## 6. bcrypt with a hard 72-byte password cap

bcrypt 5 **raises ValueError** past 72 bytes in both `hashpw` and `checkpw`
(verified against 5.0.0, not assumed). So: signup rejects >72 bytes with kind
copy; login short-circuits >72-byte attempts and burns a dummy `checkpw` to
keep timing uniform. Unknown emails also get a dummy check (no email-existence
oracle). Min length 8.
**Revisit:** bcrypt major-version bumps — re-verify the >72-byte behavior.

## 7. flask-limiter with in-memory storage

Zero-infrastructure rate limiting, correct for a single process. **Known
limitation:** counters are per-process, so `gunicorn -w 4` would multiply
every limit by 4. Hence `-w 1` in the README.
**Revisit:** at deploy, if one worker can't carry the load — options are
SQLite/Redis-backed storage (new dependency, needs a written justification
here) or accepting N× limits. Decide then, with numbers.

## 8. Public pages set zero cookies for anonymous visitors

Privacy is the brand. Public routes never touch the session; public templates
never call `csrf_token()` (the only thing that lazily creates one). Verified
in the smoke test: no `Set-Cookie` on `GET /<username>`. The dash side uses
Flask's signed session cookie — first-party, HttpOnly, SameSite=Lax,
Secure-by-default (`COOKIE_SECURE=0` is a dev-only opt-out).
**Rule, not revisitable.**

## 9. No email verification / password reset in v0 scaffold

Sending email costs money or a third-party dependency; neither is justified
pre-launch. Consequence: **a forgotten password currently means a lost
account.** Acceptable while testers are the only users.
**Revisit: BEFORE public launch — this is a launch blocker**, not a nice-to-
have. Cheapest path at that point is a transactional-email free tier; needs a
written justification here when chosen.

## 10. CSP split: nonce'd inline style on public, external-only on dash

Public pages: `default-src 'none'` + per-request `style-src 'nonce-…'` — the
single inline `<style>` block is where per-user theme tokens will render, and
the nonce avoids `'unsafe-inline'` entirely. Even injected markup can't run
scripts or load anything. Dash: `style-src 'self'`, and `script-src 'self'`
gets added only when the ≤200-line editor JS ships.
**Revisit:** only to tighten.

## 11. Deploy target — OPEN

Single VPS + Caddy vs Fly.io/Render. SQLite either way; backups via Litestream
or snapshot cron. App is deploy-agnostic: `TRUST_PROXY` env flag wires
ProxyFix so rate limiting keys on real client IPs behind a proxy.
**Decide before the first public user.**
**Addendum (June 2026):** budget constraint is $0 for now; deploy deferred
until v0 is done. Candidates at that point: Fly.io (~$3–5/mo, least ops),
Oracle Always Free ARM ($0, signup/capacity friction, pair with Litestream so
the host is disposable), Render paid (works, pricier). Render FREE is
disqualified permanently: ephemeral filesystem deletes the SQLite file on
every restart. Vercel hosts nothing we have. In the meantime, OG-unfurl and
phone testing run through a Codespaces public forwarded port.

## 12. OG/canonical URLs come from SITE_ORIGIN config, not the Host header

Host headers are attacker-influenced; canonical URLs and OG tags must never
be. One env var, set once per environment.
**Revisit:** never.

## 13. Avatars: `avatar_value` column + curated allowlists (no freeform emoji)

`avatar_kind` ('emoji' | 'gradient') plus `avatar_value` (the emoji character
or the gradient name). Both validated against allowlists in `constants.py` at
save AND at render; render falls back to 🥒 on anything unrecognised so a bad
row can never break a public page. Freeform emoji input was rejected because
validating "is this actually an emoji" across ZWJ sequences is a swamp, and a
curated picker matches the brand (deep-but-curated) and the validated-tokens
philosophy. Gradient names intentionally mirror the working theme-preset list.
Known small duplication: swatch colors repeat in `static/dash.css` (dash CSP
forbids inline styles) — sync comment in both files.
**Revisit (freeform emoji):** real user demand. It's a validation-rule change,
not a schema change.

## 14. Schema upgrades via idempotent `init-db` column checks

`init_db()` applies `schema.sql` (CREATE IF NOT EXISTS) then adds any missing
columns via `_ensure_column` (PRAGMA table_info + ALTER). Re-running
`flask init-db` is always safe and is the upgrade mechanism between sessions
pre-launch. This is deliberately NOT a migration framework.
**Revisit:** first destructive change (column drop/rename/type change) or
first real users — that's when numbered migration scripts earn their keep.

## 15. Link URLs: scheme allowlist + auto-https, validated at save AND render

`validate_link_url()` in constants.py is the XSS front line for hrefs: only
http/https to a dotted host; javascript:/data:/file:/protocol-relative, spaces
and control characters all rejected. Scheme-less input gets https:// prepended
because that's what people paste. The same validator runs again in public.py
before render — a stored URL that stops passing (corrupted row, rule tightened
later) is silently dropped from the public page. Every outbound link carries
`rel="noopener noreferrer nofollow"` and `target="_blank"`.
Known limitation: scheme-less host:port ("example.com:8080") is rejected
because urlsplit reads the host as a scheme; users add http(s):// for
non-standard ports. **Revisit:** never loosen the allowlist.

## 16. Link emoji is a tiny freeform text field (unlike avatars)

8-char cap, rendered escaped like any other text content. Avatars are curated
because they feed a constrained visual system; a link emoji is just an inline
text prefix — same injection class as the title, which is also freeform. A
curated picker per link row would be UI bloat for zero security gain.
**Revisit:** only if rendering ever becomes non-text (e.g. emoji-to-image).

## 17. Tests use stdlib unittest, not pytest

pytest isn't on the dependency list and the closed list is the point. unittest
covers assert-style validator tests fine. `python -m unittest -v` from the
repo root; tests/ is a package so discovery just works.
**Revisit:** if fixtures/parametrization pain becomes real — that's the
written-justification trigger for adding pytest as a dev dependency.

## 18. Link deletes are one click, no confirmation step

No JS means no confirm dialog, and a no-JS two-step confirm page is friction
for a v0. The delete button is visually separated and styled as the danger
action. **Resolved in the editor-JS session:** delete buttons now carry a
data-confirm dialog (~8 lines of the JS budget). No-JS users keep one-click
delete — acceptable residual.

## 19. Reordering: Pointer Events drag + arrow keys, batched, exact permutation

HTML5 drag-and-drop doesn't fire on touchscreens, and the ICP edits from
phones — so the drag handle uses Pointer Events (one code path for mouse and
touch, `touch-action: none` on the handle). The same handle moves rows with
ArrowUp/ArrowDown for keyboard users. Changes batch in the DOM; a "save this
order" button appears only when the order differs from saved, and submits a
comma-separated id list as a classic form POST — no fetch, no JSON API. The
server requires the submitted ids to be an EXACT permutation of the user's
link ids: that one check blocks foreign ids (IDOR), duplicates, and stale
tabs. With JS disabled, reordering is unavailable (new links append); all
other CRUD still works. **Revisit:** complaints from no-JS users would add
up/down buttons as a fallback.

## 20. Live preview = same-origin iframe of the REAL public page

The dash embeds `/username` in an iframe and the editor JS updates text nodes
inside it (same-origin DOM access) as the person types name/pronouns/bio.
Why: zero markup duplication, the preview can't drift from the real renderer,
and the public page still ships zero script. Cost: public-page CSP loosened
from `frame-ancestors 'none'` to `'self'` and X-Frame-Options DENY →
SAMEORIGIN — third-party framing remains blocked. Avatar/theme/links preview
on save (the redirect reloads the iframe). **Revisit:** only to tighten if
the preview is ever redesigned away.
