# RULES.md — read this first, every session, before touching anything

> This file is the contract. If a request conflicts with it, stop and say so
> rather than complying. `DECISIONS.md` holds the *why* behind each rule and
> the conditions under which it may be revisited; `PROJECT_STRUCTURE.md` is
> the file map. Read both before changing an established pattern.

## What cutecumber is (so tradeoffs resolve correctly)

A cute, fast, privacy-first link-in-bio. The product wins on **cuteness,
curated customization, page speed, and privacy** — never on feature breadth.
Any change that wins by adding surface area loses by definition. When two
goals conflict, the tie-break order is: **privacy → accessibility → speed →
cuteness → features.**

## The performance budget — per public page, NON-NEGOTIABLE

These are hard limits, enforced per feature. A change that breaks one gets
redesigned or reverted, regardless of how nice it is.

- **0 bytes of JavaScript** on public profile pages and the landing page.
- **0 third-party requests.** No CDN anything. Self-host every asset.
- **0 cookies** for anonymous visitors (the session cookie exists only after
  login, in the dashboard).
- **≤ 15 KB gzipped** for HTML + inline critical CSS (we currently sit ~2–4 KB
  — keep it there).
- **At most one self-hosted display font per page**, woff2, latin-subset,
  on the `h1` only. Body text is the system stack.
- **Lighthouse performance 100; LCP < 1 s on simulated 4G.**
- Decorative imagery is CSS gradients or small inline/static SVG. **Never
  photographs**, never raster backgrounds.

Before declaring any front-end change done, confirm the page still has zero
`<script>` tags, zero external URLs, and is still in budget.

## Security — non-negotiable

- **XSS is threat #1.** This app renders attacker-controlled strings into HTML
  served to strangers. Jinja autoescaping stays ON; `|safe` NEVER touches user
  content. No exceptions for "it's just a display name."
- **No user-supplied CSS or HTML, ever.** Customization happens only through
  validated design tokens (see `theme.py`). Colors validated as hex; every
  other token validated against an allowlist.
- **Link URLs:** scheme allowlist `http`/`https` only, validated at save AND
  at render; reject `javascript:`, `data:`, everything else. Outbound links
  carry `rel="noopener noreferrer nofollow"` + `target="_blank"`.
- **Every user-scoped query includes `AND user_id = ?`.** No query against
  `links` (or any future per-user table) without it. IDOR is unacceptable.
- **Avatar/image uploads** (where they exist) are re-encoded through Pillow to
  a fixed format and size — this strips EXIF/GPS. Never serve user bytes
  as-received; never trust the client's content-type or filename. Pattern-
  validate served filenames.
- **CSRF:** the token in the signed session is compared against a hidden form
  field on every mutating route. bcrypt for passwords (guard the 72-byte
  limit). Strict security headers everywhere; CSP on public pages is maximally
  strict because we serve no JS and no third-party anything.
- App exits at startup on a missing/weak `SECRET_KEY`. Keep it that way.

## Stack — fixed (a new dependency needs a written `DECISIONS.md` entry first)

- **Flask + Jinja2**, server-rendered. Public pages MUST be SSR (link unfurls
  need OG meta in the initial HTML; crawlers don't run JS). No SPA, anywhere.
- **Raw `sqlite3`, WAL mode, parameterized queries. No ORM.**
- **Vanilla CSS with custom properties** is the theming engine — per-user
  tokens render into a `<style>` block at request time. No Tailwind, no CSS
  framework, no build step, no `node_modules`, no preprocessor.
- **Vanilla JS, dashboard only, ~200-line budget** (currently ~140). It is all
  progressive enhancement: with JS off, every CRUD action still works — only
  drag-reorder and live-preview degrade. If JS would exceed the budget, stop
  and reconsider the design before reaching for a library.
- **Allowed deps:** flask, bcrypt, python-dotenv, flask-limiter, gunicorn,
  pillow. Anything else is a written decision, justified against the problem.

## Versioned data — from day one

Any stored user-data shape (theme JSON, page config) carries `version: N` with
a migration registry applied on load. **No shape change without a version bump
and a migration path.** Saved-data migrations get a test.

## Tests

Run `python -m unittest` before declaring work done; keep it green (currently
53 tests). Tests are required for: URL validation, the theme-token validator,
the avatar pipeline's metadata stripping, and any saved-data migration. Don't
write tests for trivial glue. A claim made in user-facing copy (e.g. landing
"why" points) must be backed by a test or a measurable property.

## Voice

Warm, soft, a little silly, never corporate. In-product microcopy stays in
voice ("your page is looking adorable"); error messages are kind. Inclusive by
default: pronouns are a first-class field; copy never assumes gender.

## Design system (design spec v1) — constraints when implementing it

The brand art (slice mark, 12 avatars, 4 decoration packs) is approved to
integrate, subject to every rule above. Specifics that bind:

- **The slice mark is fixed and never themed:** green rind `#8fcb72`, flesh
  `#ecf7df`, seeds `#cde8b4`, face ink `#33502e`. Don't recolor, rotate,
  outline, or box it. Inline it as SVG (it's tiny) rather than adding requests.
- **Wordmark is live text** in the already-self-hosted Fredoka 600, color
  `#3f5a39`, lowercase. Not an image, not a second font load.
- **Brand palette is separate from the user-page theming engine.** This spec
  does NOT touch `theme.py` presets or their tokens. User-page customization
  stays WCAG-AA-enforced by tests; brand colors apply only to cutecumber's own
  chrome (landing, dash, mark).
- **Avatars and pack tiles are `full_color` static SVG**, ≤ 8 KB each (the set
  ships ~2 KB), no `<script>`, no `<foreignObject>`, no embedded rasters. They
  live in `app/static/`, inherit the existing CSP + caching, add no endpoints.
- **Avatar/decoration tokens** (`set:<name>`, `pack/slug`) are validated
  against a registry at save AND render, exactly like current tokens — and
  carry a theme-version bump + migration because the saved shape changes.
- Curated only: users PICK avatars and packs; they never upload SVG. (Photo
  avatars remain the only user-uploaded image, and stay circle-cropped so the
  shape distinguishes them from the square set tiles.)

## ⚠️ Three things in the design spec to RAISE, not silently implement

1. **`font-display: swap` on the brand fonts.** The spec's own `@font-face`
   blocks use `swap`; pair it with `<link rel="preload">` for the one display
   font, or the wordmark can cause a layout shift that dents the Lighthouse
   100. Decide deliberately.
2. **Multi-decoration backgrounds** (`"decoration": ["baby_cuke","daisy"]`,
   stacked CSS layers, "cap at 5"). Five tiles at ~2 KB is fine on weight, but
   confirm the *gzipped page* stays ≤ 15 KB with the layers inlined, and keep
   the picker's default at 2–3. This also changes the theme JSON shape → needs
   a version bump + migration + validator update + tests. Not a CSS-only edit.
3. **Retiring emoji avatars** (spec says existing emoji rows "fall back to
   default at render"). That's a silent visual change to existing users'
   pages. Confirm this is intended before shipping; if so, it's a documented
   migration decision, not an incidental one.

## Workflow

- Work on a feature branch. `main` = production and is deploy-only via merge.
  A tag `pre-refactor-prod` marks the last known-good prod commit.
- Before a non-trivial change, state the plan: which files change, which are
  new, where each lives. Then implement.
- Update `PROJECT_STRUCTURE.md` and `DECISIONS.md` when a change warrants it.
- Production-ready code, no placeholders. Every file gets a destination path.
