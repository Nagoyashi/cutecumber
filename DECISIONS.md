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
**Resolved (June 2026, #26):** password reset shipped via Resend's free
tier. Email verification at signup remains deliberately absent — it adds
signup friction for no v0 benefit. Revisit if spam signups become real.

## 10. CSP split: nonce'd inline style on public, external-only on dash

Public pages: `default-src 'none'` + per-request `style-src 'nonce-…'` — the
single inline `<style>` block is where per-user theme tokens will render, and
the nonce avoids `'unsafe-inline'` entirely. Even injected markup can't run
scripts or load anything. Dash: `style-src 'self'`, and `script-src 'self'`
gets added only when the ≤200-line editor JS ships.
**Revisit:** only to tighten.

## 11. Deploy target — RESOLVED (Fly.io)

Single VPS + Caddy vs Fly.io/Render. SQLite either way; backups via Litestream
or snapshot cron. App is deploy-agnostic: `TRUST_PROXY` env flag wires
ProxyFix so rate limiting keys on real client IPs behind a proxy.
**RESOLVED (June 2026): Fly.io** — see #33 and DEPLOY.md.
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

### Addendum (frontend-refactor, June 2026): freeform emoji + designer set
Both shipped together, both ADDITIVE — `avatar_kind` has no DB CHECK, so adding
'set' is pure app validation: no schema change, no theme-version bump, no data
migration. Emoji + gradient + photo + set all coexist (owner's call).
- **Freeform emoji** acts on this entry's own "real user demand" revisit
  trigger (owner request). The emoji is now any value from the OS keyboard,
  capped at `AVATAR_EMOJI_MAX` (8) and rendered escaped — same injection class
  as the link emoji (#16) and the display name, so NO new XSS surface (a render
  test confirms `<b>x` stays escaped). We deliberately do NOT validate "is it
  really an emoji" (the ZWJ swamp this entry named); length is the only bound.
  `validate_avatar_emoji()` runs at save, `public.py` re-checks length at render.
  The curated emoji grid is gone — no predefined emoji.
- **Designer avatar set** ('set' kind, value = slug) = the 12 kawaii SVG tiles
  from the design spec, served as cached static `<img>` from `app/static/avatars/`
  and validated against the `AVATAR_SETS` registry at save AND render (the
  registry IS the boundary; an unknown slug falls back to 🥒). Tiles render
  SQUARE so they stay visually distinct from circle-cropped photos (per the
  design spec). `tests/test_avatar.py` enforces registry↔file parity and the
  no-script / ≤8 KB tile rules, the way EXIF/AA are enforced.

### Addendum (design refresh v2, June 2026): set is the default; emoji/gradient leave the picker
The v2 dashboard leads with the drawn set, so two changes (issue #43, owner-approved):
- **Default avatar is now `set:sprout`, not the 🥒 emoji.** `signup` sets
  `avatar_kind`/`avatar_value` explicitly (`DEFAULT_AVATAR_KIND`/`_VALUE` in
  `constants.py`), so the change reaches the existing prod table without an
  ALTER — the schema column default (also moved to `set`/`sprout`) is just a
  backstop. `DEFAULT_AVATAR_EMOJI` (🥒) stays the render-time fallback for an
  unrecognised/corrupt row.
- **Freeform emoji + flat gradients leave the *picker*, but NOT render/save.**
  The picker now offers the 12 set tiles + a photo upload only. Existing users
  whose avatar is an emoji or gradient keep it — the registry still validates
  and renders those values, and the editor shows the current one as a "keep"
  option so editing a profile never silently changes their avatar. This is a
  UI retirement, **not** a data migration: no theme-version bump, no stored-shape
  change (RULES "things to RAISE #3" — the visible-change risk is avoided by
  keeping render support). **Revisit:** if we ever want to fully drop the
  legacy kinds, that becomes a real migration with a fallback + tests.

### Addendum (design refresh v2 public pages, June 2026): avatars go circle (#55)
The earlier addendum rendered set tiles **square** to distinguish them from
circle-cropped photos. The public-page refresh **reverses that**: all avatars —
set tiles and uploaded photos alike — render **circle-cropped** (one shape), per
the design spec. It's a render-only CSS change (`public_page.html`
`.avatar-set` gains `border-radius:50%`); the stored shape and the registry are
untouched, so no migration. The dashboard picker still shows the set tiles
rounded-square (a picker affordance), only the public render is circular.
**Revisit:** if a future design wants shape to signal source again.

## 13b. Page settings live in the versioned theme (layout / ambient / show_credit)

The public-page refresh (#55) adds three per-user **page settings**: `layout`
(`centered`|`wide`), `ambient` (decorative motif background, **default off** to
protect the public page's ~2 KB budget), and `show_credit` (footer credit). They
are stored as theme **overrides** but are NOT colour-preset properties — their
defaults live in `theme.py` `PAGE_DEFAULTS`, not in `PRESETS`. Adding them is a
**stored-shape change**, so it carries a theme-version bump (**v2 → v3**) with a
migration + validator + resolver + tests, exactly like the decoration multi-list
(DECISIONS #21 addendum). The v2→v3 migration only stamps the version: existing
themes gain the new settings via `PAGE_DEFAULTS` at resolve, no override rewrite.
**Rule (unchanged):** no stored-shape change without a version bump + migration + test.

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

### Addendum to the reorder decision (field note, launch prep)
Real-iPhone testing surfaced a WebKit trap: pointer capture set on the drag
HANDLE dies silently when the captured element is moved in the DOM — which
reordering does on every step — so pointerup never fires and UI driven by
drag-end stalls until the next tap. Fix: capture on the LIST (never moves),
`touch-action: none` on the handle in CSS (preventDefault alone does NOT stop
iOS scroll-panning — that was the jank), a lostpointercapture safety net, and
the save button now reveals on first order change, not on release.

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

## 21. Theme SVG layers are inline data: URIs; public img-src gains `data:`

Dot patterns and decorations (sparkles/hearts/stars) are tiny SVGs built
server-side from validated hex tokens, percent-encoded into CSS data URIs —
zero extra requests, a few hundred bytes each. CSP cost: `img-src 'self'
data:` on public pages. data: URIs are inert image data; scripts still cannot
run (`default-src 'none'`), so this is a cosmetic loosening, not a security
one. Generated CSS deliberately contains no quotes/ampersands/angle brackets,
which keeps every template insert autoescape-transparent — `|safe` remains
banned project-wide (a test enforces the character set).

### Addendum (frontend-refactor, June 2026): decorations went multi (v2)
`decoration` is now a LIST of `<pack>/<slug>` tokens (was a single string),
capped at `MAX_DECORATIONS` (5), validated against the `DECORATION_PACKS`
registry at save AND render. **`THEME_VERSION` 1→2** with a migration
(string→list: `"hearts"`→`["basic/hearts"]`, `"none"`→`[]`) — the first real
entry in `MIGRATIONS`, with tests, exactly as the versioned-data rule requires.
Two render paths: `basic/*` stay accent-tinted inline `data:` URIs (this entry);
designer-pack tiles are full_color STATIC svgs referenced as
`url(/static/packs/<pack>/<slug>.svg)`. Static over inlined was deliberate — it
protects the ≤15 KB page budget: a 5-decoration page is ~1.3 KB gzipped because
only the `url()` refs are inline; the tiles are separate cached requests under
`img-src 'self'`. The picker is a no-JS checkbox catalog grouped by pack, and
the cap of 5 is enforced server-side in `validate_theme`, not just in the UI.
An explicit empty list is a real choice (`[]` = no decorations) distinct from a
preset's default. **Revisit:** stagger tile positions when stacking many (a
browser-verified polish pass), and re-check the gzipped budget if tiles grow.

## 22. Scalloped button shape: deferred, not faked

The spec lists pill/rounded/square/scalloped. There's no clean CSS scallop
that fits the budget (mask-based techniques are fiddly and brittle), and
shipping a dotted-outline imitation under the name "scalloped" is worse than
shipping three honest shapes. Enum ships as pill/rounded/square.
**Revisit:** at the polish pass; a stored-shape version bump is NOT needed to
add an enum value later (additive change).

## 23. Display fonts: fontsource subsets via npm, one per page, h1 only

Fredoka 600 (16.4 KB) and Comfortaa 700 (13.4 KB), latin subset WOFF2,
self-hosted in static/fonts — under the 30 KB budget with room to spare. Body
text is always the system stack; the display font applies to the h1 only and
is preloaded. `font: system` skips the font entirely. Derived theme values
(muted text, accent-button label color, shadow tint) are computed from the
palette at render time rather than stored — they can't be set to something
unreadable, and preset AA is enforced by tests/test_theme.py, not eyeballs.
**Revisit (more fonts):** only via the same fontsource/npm pipeline, same
budget per file.

## 24. Dash IA: collapsible sections, anchored save redirects, sticky flash

The dash is a slim page-live banner plus three native <details> sections with
ids (#links/#profile/#theme) — zero JS spent. Saves redirect to
`?open=<section>#<section>`: the query param tells the server which section to
render expanded (URL fragments never reach the server, so the param is
mandatory), the fragment scrolls the browser there, and `.flash` is
position:sticky so the confirmation stays visible after the jump. Fixes the
"page jumps to top after every save" complaint at zero JS cost. Default open
section: links.
**Rule:** any future dash section follows this exact pattern.

## 25. Stealth robots.txt, SVG favicon, immutable font caching

robots.txt serves `Disallow: /` until ROBOTS_ALLOW=1 (launch-day flip,
documented in .env.example) — supports the soft-launch plan without code
changes. Favicon is one ~120-byte first-party SVG (🥒), also served at
/favicon.ico, which kills the 404 every browser was generating through the
username route. Font files carry their version in the filename (fontsource
naming), so they get `Cache-Control: immutable, max-age=1y`; dash.css/js are
unversioned and keep Flask's default. Real Lighthouse requires a real
browser: structural proxies (preload order, font-display swap, inline-only
CSS, viewport meta) are asserted in smoke tests; the actual score gets
checked in Chrome DevTools against the forwarded/deployed URL.

## 26. Password reset: Resend over raw HTTPS, hashed tokens, session kill

Resend is called with a stdlib urllib POST — a JSON request does not justify
an SDK dependency (the closed list stands). Dev mode (no RESEND_API_KEY) logs
the reset link to the console so the flow works locally. Security shape:
tokens are 32-byte urlsafe randoms stored as SHA-256 (a DB leak leaks nothing
usable), single-use, 1-hour expiry, latest-token-wins; the request endpoint
returns an identical message whether the email exists or not (no account
enumeration) and is rate-limited 5/hour. A password change also rotates a
session "auth fragment" (derived from the password hash, checked in
load_user), which invalidates every existing session despite sessions being
stateless cookies. Deliverability: the cutecumber.cc domain is verified in the
Resend dashboard, so the configured sender delivers to any recipient (reset
email verified end-to-end in production, #4) — the early "owner-only until the
domain is verified" free-tier caveat no longer applies.

## 27. Legal pages: honest drafts with placeholders, footer links everywhere

/imprint (§5 DDG shape) and /privacy (GDPR shape) ship with [PLACEHOLDER]
markers for legal identity, address, hosting provider, and the US-transfer
safeguard for Resend. The privacy page describes only what the app actually
does — which is verifiable from this repo. Legal links sit in the site footer
on dash/auth/landing pages AND as tiny muted links on public profile footers
(German "immediately reachable" practice favors this; **revisit** removing
them from profile pages only if qualified counsel says the two-click path via
the landing page suffices). Self-service account deletion shipped (#29: a
password-gated delete button under /dash/account), so the privacy page describes
that path rather than a manual-by-email gap. These pages are drafts by a
software project, not legal advice.

## 28. Landing "why" claims must stay literally true

The why-section claims (zero trackers/cookies on public pages, ~2 KB pages,
every preset passes WCAG AA contrast) are each backed by an automated test in
this repo. **Rule:** no marketing claim ships on the landing page unless a
test or measurable property backs it; if a feature ever weakens a claim, the
landing copy changes in the same commit.

## 29. Account deletion: password-gated, immediate, hard

One button on /dash/account behind the current password (the JS confirm is
courtesy; the password is the gate). DELETE on the user row; links cascade
via the FK; the session dies. No soft-delete, no grace period — privacy-first
means gone-means-gone, and it keeps the GDPR erasure story one sentence long.
**Resolved at launch prep:** freed usernames now rest in a
username_tombstones table for TOMBSTONE_DAYS (30) before re-claim — recorded
at deletion, enforced at claim, expired rows purged opportunistically during
claims (no cron). Known acceptable edge: a person who deletes and regrets it
cannot re-claim their own name for 30 days either; the kind error explains
the rest period.

## 30. Kawaii decorations: curated pack registry, never user uploads

Direction settled (build pending first assets): designer-made SVG decoration
packs per DESIGN_PACKS.md — 130×130 tiles, ≤8 KB, accent-tinted or
full-color, automated safety checks (no scripts/foreignObject/raster), served
as cached static files, validated against a registry like every other theme
token. End users PICK packs; they never upload SVG (script-bearing format +
moderation burden + page-weight risk). Packs are also the natural paid unit
if monetization happens — selling cuteness, not data.

### Addendum (frontend-refactor, June 2026): packs built
First assets landed — 4 house packs (`garden_patch`, `cozy_cafe`,
`little_friends`, `sakura_dreams`) × 5 tiles each, plus a `basic` trio that
carries the original inline glyphs — so the registry shipped (see the #21
addendum for the multi-decoration shape + version bump). Tiles live at
`app/static/packs/<pack>/<slug>.svg`; `tests/test_theme.py` enforces
registry↔file parity and the no-script / ≤8 KB rules, like EXIF/AA. The avatar
SVG set shipped the same way (#13 addendum). Still curated-only, no user uploads.

## 31. Avatar uploads: byte-identified, re-encoded, metadata-free, tidy

Pipeline per the original spec: the client's filename and content-type are
ignored; Pillow identifies the BYTES (jpeg/png/webp/gif only, 8 MB input cap,
30 M-pixel decompression-bomb ceiling), EXIF orientation is applied FIRST
(else phone photos render sideways forever), then center-crop to 176×176
(88px circle at 2x) and re-encode to WebP with a quality ladder until ≤30 KB.
Re-encoding without passing exif/icc IS the metadata strip — GPS included —
and tests/test_avatar.py enforces it the way test_theme.py enforces AA.
Files live in instance/avatars/ as <user_id>-<12 hex>.webp (name rotates per
upload → /a/<file> serves immutable-cached), pattern-validated at save AND
serve. Data minimization: switching away from a photo, replacing it, or
deleting the account deletes the file. MAX_CONTENT_LENGTH went 64 KB → 8 MB
globally because the CSRF hook parses bodies before routes can set per-route
caps; acceptable on one box with rate limits. Pillow joins requirements
exactly as the dependency rule anticipated ("Pillow only when avatar uploads
ship").

## 32. Email diagnostics: send-test CLI, full error surfacing

The reset endpoint deliberately masks send failures from browsers
(anti-enumeration), which makes "email doesn't work" undebuggable from the
UI. So: HTTP errors from Resend now log the response BODY (where the actual
reason lives — wrong From domain, sandbox restriction, bad key), and
`flask --app wsgi send-test you@example.com` sends outside the masked path
and prints the verdict. First stop for any future email mystery.
Field note: the first real-world failure was Cloudflare's error 1010 —
api.resend.com is fronted by Cloudflare, which bans the default Python-urllib
User-Agent signature before requests reach Resend at all. Fixed by sending a
proper User-Agent ("cutecumber/1.0"). If a stdlib HTTP call to any API ever
403s with a non-JSON body, check for a Cloudflare block page first.

## 33. Deploy: Fly.io, one always-on machine, volume SQLite, optional Litestream

shared-cpu-1x/256MB in fra, ~$3-5/mo, SQLite on a 1 GB volume at /data.
Vercel was ruled out terminally: serverless functions have no persistent disk
at any price — SQLite is architecturally impossible there. Always-on
(auto_stop off) because cold starts would eat the LCP < 1s budget; revisit
only if cost ever matters more than that budget. The entrypoint runs the
idempotent init-db every boot, so schema upgrades ship with deploys. HSTS
moved into the app (Fly terminates TLS; there is no Caddy layer). Litestream
is baked into the image but OPT-IN via LITESTREAM_REPLICA_URL — the app
deploys before backups exist, restores automatically onto an empty volume
once they do, and DEPLOY.md mandates one restore fire-drill. Container runs
as root inside the Firecracker microVM on purpose: the volume mount is
root-owned and isolation is VM-level; revisit if Fly's guidance changes.
Gunicorn stays at one worker (limiter counters are per-process, #7).

## 34. Brand chrome: slice mark + live-text wordmark (design spec v1)

The favicon IS the slice mark — one 1.3 KB cucumber-face SVG with the fixed
brand colors (rind `#8fcb72`, flesh `#ecf7df`, seeds `#cde8b4`, ink `#33502e`),
never recolored/rotated/boxed. Landing inlines it (zero extra requests, per the
spec); dash/auth chrome references it as a cached same-origin `<img>` (img-src
'self' already allows it, no markup duplication). Wordmark is live text in the
already-self-hosted Fredoka 600, `#3f5a39` — not an image, not a second font.
On the landing the wordmark IS the h1, so "one display font, h1 only" still
holds; on the dash it styles `.brand` (chrome, not a perf-budgeted public page).
**Flagged-item #1 (CLS), decided deliberately:** the landing previously loaded
ZERO fonts; the wordmark adds Fredoka. Shipped the essential fix — `<link
rel=preload>` + `font-display: swap` (the proven public_page pattern) so the
font is present at first paint. `size-adjust`/`ascent-override` tuning is
DEFERRED to the real-browser Lighthouse pass (#25): a wrong metric value makes
CLS worse, and it needs Fredoka's real metrics measured in Chrome. Verified the
landing still ships 0 `<script>`, 0 external URLs, 0 cookies, ~2 KB gzipped.
Public profile footer stays system-font "cutecumber.cc" (no emoji, no font, no
mark) to protect the per-profile budget. **Revisit:** tune size-adjust when the
real Lighthouse run happens; revisit the wordmark font only via the #23 pipeline.

## 35. Dependency hygiene: digest-pinned base + blocking pip-audit (issue #7)

Two hardening moves for the live product, both deploy-agnostic:
- **Reproducible builds:** the Dockerfile base is pinned to the `python:3.14-slim`
  *index* digest (`@sha256:…`), not the floating tag — the tag is kept inline for
  readability and to mirror the CI Python pin. A given commit now builds the same
  base bytes forever. Dependabot's `docker` ecosystem updates the digest on a
  schedule, so pinning doesn't freeze us on stale CVEs.
- **Vulnerability scanning:** CI runs `pipx run pip-audit -r requirements.txt` as
  a step in the required `test` job — **blocking**, so a known CVE in our declared
  deps stops a merge to `main`. `pipx` isolates the tool so its own deps don't
  enter the audit. An advisory with no upstream fix is waived narrowly with
  `--ignore-vuln GHSA-…` in `ci.yml` (a visible, reviewed exception) rather than
  by dropping the gate. Update cadence is Dependabot weekly (`.github/dependabot.yml`).
**Lockstep rule:** the base image and `ci.yml`'s `python-version` are pinned to
the SAME minor (3.14) on purpose — a Python minor bump moves BOTH in one change,
or CI tests a runtime prod doesn't use. (The 3.12→3.14 bump in `v0.2.1` did
exactly this: the Dockerfile digest came via Dependabot, `ci.yml` moved with it.)
**Revisit:** GitHub Dependency-graph + Dependabot security alerts are the
repo-settings complement (owner-toggled); if pip-audit noise from unfixable
transitive advisories becomes routine, reconsider scoping it to direct deps.

## 36. Error reporting: optional webhook over raw HTTPS, no SDK (issue #13)

Live 500s previously reached only stdout / Fly logs — no aggregation, no alert,
so a silent error could sit unseen. The fix is an **opt-in** reporter: when
`ERROR_WEBHOOK_URL` is set, `app/monitoring.py` POSTs a small JSON object
(service, method, reset-token-scrubbed path, exception + traceback) to that URL
on Flask's `got_request_exception` signal. Unset = a no-op.

**Why a webhook, not the Sentry SDK** (this is the written closed-deps
justification the stack rule requires): the job is "POST JSON when something
breaks," which the stdlib does — exactly the reasoning that kept Resend SDK-free
(#26). `sentry-sdk` pulls a transitive tree and a background-thread transport
for what one `urllib` call covers, so it doesn't clear the bar in `RULES.md`.
The env var accepts any JSON sink (a Sentry ingest URL, a Slack/Discord webhook,
a self-hosted collector), so we keep the integration without the dependency.

**Privacy:** method + scrubbed path + traceback only — never the request body,
headers, cookies, or user identity; stdlib tracebacks carry no local variables.
Delivery never raises (a monitoring outage must not turn one 500 into two).
**Revisit:** if we ever need breadcrumbs / release health / sampling that a
hand-rolled POST can't carry, re-evaluate `sentry-sdk` as a written dep here —
with the transitive tree counted against the budget.

## 37. Lighthouse SEO < 100 is a false negative from our strict CSP — don't "fix" it

At launch (v0.3.0) the live landing page scores Performance / Accessibility /
Best-Practices **100** but **SEO ~91**, on a single failing audit: `robots-txt`
→ "Lighthouse was unable to download a robots.txt file." It is served correctly
(HTTP 200, `text/plain`, valid `User-agent: * / Disallow:`); `curl` fetches it
fine. The cause is that Lighthouse's audit measures via an **in-page `fetch()`**,
which the public-page CSP (`default-src 'none'`, no `connect-src`) blocks by
design — the same zero-fetch posture that keeps public pages cookie- and
JS-free. **Real crawlers (Googlebot et al.) fetch `robots.txt` as a top-level
request, unaffected by CSP**, so discoverability is fine.

**Decision:** do NOT add `connect-src 'self'` (or otherwise loosen the public
CSP) to make a Lighthouse audit pass — that would weaken a real security control
to satisfy a measurement artifact. Tie-break order puts privacy/security above a
lint. **Revisit:** only if a real crawler is ever shown to be blocked (it
won't be by CSP), or if Lighthouse changes the audit to a top-level fetch.
