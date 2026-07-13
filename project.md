# project.md — cutecumber.cc

> Canonical roadmap & strategy. **Phase-level status only** — per-task status
> lives on the *cutecumber.cc* GitHub Project board, never here. Architectural
> rationale lives in `DECISIONS.md`; the hard invariants in `RULES.md`.

## Vision

A cute, fast, privacy-first **creator platform** — a lightweight website +
monetization toolkit that starts as a link-in-bio and grows into a small site.
The rival it's aimed at is **beacons.ai**; the way it wins is the *opposite* of
beacons.ai: **the page a visitor loads stays server-rendered, tiny (~2 KB where
it can be), zero-JavaScript, zero-tracker, zero-cookie, and WCAG-AA** — privacy
and speed as the wedge, not a constraint. Creators get the tools (site builder,
store, email, media kit, analytics); visitors get a page that respects them.
Cuteness is the skin over all of it.

**The DNA that never moves** (see `RULES.md`, the contract): the public artifact
is the invariant. Breadth is welcome, but only *the cutecumber way* — rich in the
dashboard, lean and private on the public output. A feature that can't fit the
public-page budget gets redesigned until it can, never rejected for being
ambitious. (Overhaul from "link-in-bio, never feature breadth" → "privacy-first
creator platform" recorded 2026-07-12; see the roadmap and `DECISIONS.md`.)

## Current phase

**Between cycles.** The **page builder is open to every creator** — shipped as
`v0.9.0` (2026-07-12, verified live), which made it the **primary editor** for
all authenticated users (the classic links editor is the secondary path) and
gated the paid **sprout** tier as **"coming soon"** with a work-in-progress
payment placeholder. (`v0.8.0`, 2026-07-11, first put it live for an email
allowlist.) Widening access is safe because the risky section types stay
premium/coming-soon, so only the six free, server-rendered sections go public —
the sandbox/embed CSP exceptions stay dormant until sprout ships. Still ahead:
**real billing** (Stripe — the gate before sprout actually opens) and two
low-priority editor-polish items (#86). **Magic-link sign-in was dropped**
(owner, 2026-07-12 — #53/#70/#71 closed not-planned); password auth stays the
model. A couple of standalone backlog items remain un-milestoned (the
dashboard WCAG-AA button fix #65, and the 404→signup username carry #69).

**Direction (2026-07-12):** the project pivoted from "link-in-bio" to a
**privacy-first creator platform** aimed at rivalling beacons.ai — see the Vision
and the roadmap's *road to a privacy-first creator platform* (Phases A–E).
**Phase B shipped** as `v0.11.0` (2026-07-13, verified live): **sites, not just
pages** — a creator's page grows into a small multi-page site (`/<username>` home
+ `/<username>/<slug>` subpages), with a zero-JS server-rendered site nav and a
page switcher in the builder. Additive model (home stays in the user row;
subpages in a `pages` table, DECISIONS #41). (Phase A, `v0.10.0`, made the builder
*behave*.)

**⚠️ As of `v0.11.1` (2026-07-14) the page builder is HIDDEN in production**
(owner call — still too rough to ship; kept cooking). It's now gated behind
`BUILDER_ENABLED` on *every* surface (creator + visitor), and the prod flag is
**off**, so the **links editor** is the live editor and public pages render the
classic links page. All builder code + saved data stay put — flipping the flag on
restores it. Builder work continues on `main` behind the flag; re-expose it when
it's genuinely shippable.

The next cycle is **Phase C — monetization**: real billing (Stripe —
the deferred #38 item, the gate before `sprout` actually opens), then tips + a
digital-product store (server-rendered, checkout link-out). Pure-visual editor
polish (#86) still waits for the incoming design batch
(`design/Cutecumber.cc-5.zip`). Propose the cycle + its issues, wait for the
owner's OK. Per-task status → the *cutecumber.cc* board ↗

## Roadmap

### ✅ Phase 1 — v0 MVP (2026-06-10)

The complete server-rendered link-in-bio: signup → claim username → public page
with OG tags, profile editing, links CRUD, drag/keyboard reorder + live preview,
theming engine (6 WCAG-AA presets), and a perf/polish pass. Flask + Jinja + raw
sqlite3; zero-JS public pages.

### ✅ Phase 2 — Launch readiness (2026-06-10 → 06-11)

Password reset (Resend, hashed single-use tokens), account deletion + 30-day
username tombstone, avatar uploads (Pillow EXIF/GPS strip), legal pages, and the
Fly.io deploy config (volume SQLite, optional Litestream). Production baseline
tagged `pre-refactor-prod` (2026-06-13).

### ✅ Phase 3 — Design-spec v1 (shipped v0.1.0 · 2026-06-14)

Brand chrome (slice-mark favicon + Fredoka wordmark), the 12-avatar SVG `set`
kind + freeform emoji, and decoration packs + multi-decoration (theme shape
v1 → v2, migrated). Shipped to production within the full perf/security budget
and tagged `v0.1.0`.

### ✅ Phase 4 — Production hardening (shipped v0.2.0 · 2026-06-20)

Closed the post-launch audit backlog: security regression tests (CSRF / IDOR /
cookie-free), dependency vuln scanning + reproducible builds, legal-placeholder
fills, reset-email deliverability, and DB backup setup. Tracked as the `v0.2.0`
milestone.

**Acceptance (met):** the high/med audit issues closed; DB backups (Litestream →
R2) and password-reset email verified working in production.

### ✅ Phase 5 — Launch (shipped v0.3.0 · 2026-06-21)

Public launch: flipped `ROBOTS_ALLOW` so `robots.txt` allows crawling, and held
the front door to the same accessibility bar as the rest of the app (a headless
Lighthouse pass caught the landing CTA failing WCAG AA — fixed). Authoritative
Chrome DevTools Lighthouse + on-phone QA (#34) run as owner-driven post-launch
verification.

### ⬜ The road to a privacy-first creator platform (overhaul — 2026-07-12)

> **North star:** a worthy rival to **beacons.ai** that wins on privacy + speed +
> cuteness instead of tracker-heavy breadth. Beacons' pillars — link-in-bio,
> website builder, store / digital products, email marketing, media kit,
> analytics, AI — each map onto cutecumber **privacy-first**, scoped by the
> public-page contract (`RULES.md`). Phases are directional; per the release
> cycle, materialize only the current one as a milestone.

- **Phase A — The builder feels like a product.** The v0.7–0.9 builder works but
  is rough (gallery photo upload unreliable, general editor jank). Fix the bugs,
  make uploads solid, polish the editor to prototype quality, add tests. Nothing
  rivals anything until the core tool is genuinely pleasant. *(the next cycle)*
- **Phase B — Sites, not just pages.** A creator gets a small **multi-page site**
  (e.g. `/name`, `/name/about`, `/name/shop`) with templates — the "small website
  builder" half of the vision. Every public page stays in-contract.
- **Phase C — Monetization.** Real billing (**Stripe** — the deferred decision,
  `DECISIONS.md` #38) opens `sprout`; then creator money primitives: **tips** and
  a **digital-product / download store**, each a server-rendered page whose
  checkout **links out** — no third-party script or tracker on the public page.
- **Phase D — Audience, privacy-first.** Native **email capture** (first-party,
  consented, GDPR-clean — the creator's list, no third parties) and **cookieless
  aggregate analytics** (Plausible-style, no per-visitor tracking). Beacons'
  email + analytics pillars, done the privacy way — a direct differentiator.
- **Phase E — Media kit + light AI assist.** An **auto-updating media kit** built
  from the creator's own page/analytics data (for brand deals), and optional
  dashboard AI copy-assist. AI is a new dependency → a written `DECISIONS.md`
  entry gates it.

Speculative beyond Phase A; correct as direction firms up. Payment, email-PII
storage, an analytics store, and any AI dependency each need a `DECISIONS.md`
entry before their phase is cycle-ready.

> Versioning: shipped phases above are dated from git history — no semver tags
> exist for them. Going forward, each phase release gets a semver tag
> (`v0.1.0`, …); historical commits are not retro-tagged.

## Phase log

Durable completion notes, newest first. Rationale → `DECISIONS.md`.

### Phase B — sites, not just pages — shipped 2026-07-13 (`v0.11.0`)

A creator's single page grows into a small multi-page site. Additive & safe: the
home page stays in the user row; subpages live in a new table.

- **Data model** (#109, DECISIONS #41): a `pages` table for subpages (home stays
  in `users.sections_*_json` — no live-data migration), all queries user-scoped
  (IDOR), capped at 8, slug immutable after create (the URL is the product, #3).
  Orphan-image GC + account delete cover subpage photos. 11 tests.
- **Public** (#110): `GET /<username>/<slug>` renders a subpage's live section
  stack (same contract as home: zero-JS/-third-party/-cookie, WCAG-AA); a
  theme-agnostic server-rendered **site nav** links home + published subpages,
  hidden when there's only one.
- **Builder** (#111): a **page switcher** — active page is a `?page=<slug>` param,
  switching is a navigation; add/rename/delete/reorder pages, edit + publish each
  with the full section editor. save/publish/preview route to the active page.
- Verified live: `pages` table created on deploy, subpage routing + nav work,
  208 tests green.

### Phase A — a builder that behaves — shipped 2026-07-12 (`v0.10.0`)

First cycle of the creator-platform overhaul: make the builder feel like a
product. Editor-only; the public page a visitor loads is unchanged.

- **Loud save state** (#102): the whole-page autosave was silently all-or-nothing
  — one invalid section dropped the entire draft with only a whisper, so a
  just-uploaded gallery photo vanished on reload. Now a failed save is a
  persistent red "not saved" pill (reason on hover) that clears on the next good
  save; gallery uploads show a per-photo "uploading…" spinner → thumbnail.
- **Errors point to the culprit** (#103): `validate_sections_detailed` returns the
  offending section index; save/publish return it as `at`; the pill reads "click
  to jump there" and selects + scrolls to that section.
- **DOM-light drag** (#103): reorder no longer rebuilds the canvas on every
  pointer move (only a drop-line indicator moves) — smooth on long pages — plus
  edge auto-scroll. Verified in a real browser; 185 tests green.
- Deferred: pure-visual prototype-match polish (#86) → awaits the incoming design
  batch.

### Page builder for everyone; sprout "coming soon" — shipped 2026-07-12 (`v0.9.0`)

- **Opened to all creators** (#90, #91): `BUILDER_ENABLED` alone now grants
  access (flag-off still a plain 404); the former access allowlist is repurposed
  to an internal-test set. The builder becomes the **primary editor** — the
  dashboard leads with an "open the builder" CTA and the classic links editor is
  the secondary path. A public page still switches to the section stack only once
  its owner publishes.
- **Sprout gated as "coming soon"** (#92, #93): premium sections + the two
  premium themes show a coming-soon badge (not buy/upgrade); the upsell is a
  "payments are a work in progress" placeholder with no price/checkout. The
  staging plan toggle is restricted to the internal-test set (normal users get a
  404 there), so premium can still be QA'd internally before billing.
- **Safe by construction** (DECISIONS #38 addendum, #94): the risky section
  types (embed/custom-HTML/form/mail-list) stay premium/coming-soon, so opening
  access exposes only the six free, server-rendered section types — the
  sandbox/embed public-page CSP exceptions stay dormant, no new attack surface.
- **Abuse posture** (#93): the now-public builder write endpoints
  (save/publish/upload/preset) are rate-limited. Verified in a real browser
  (non-allowlisted vs internal paths); 182 tests green.

### Page builder live (allowlist-gated) — shipped 2026-07-11 (`v0.8.0`)

- **The flip** (#83): `BUILDER_ENABLED` + `BUILDER_ALLOWLIST` set as Fly secrets
  and deployed; allowlisted creators reach `/dash/builder`, everyone else gets a
  plain 404 (no hint the surface exists), and the legacy links editor stays the
  default. No new migration — the additive `sections_*_json` / `plan` columns
  already shipped in v0.7.0. Verified live: strict public CSP intact, gate
  redirects unauth to login, Litestream replicating.
- **Security-gated before the flip** (#34, DECISIONS #38): the public-page
  exceptions were QA'd in a real browser — the custom-HTML sandbox blocks scripts
  and network (no exfil reached the origin; off-origin img blocked by the frame's
  own CSP), embeds stay click-to-load (no third-party request until the click),
  and the CSP exceptions arm only on pages that use those sections. Plus owner
  device QA: DevTools Lighthouse (mobile + desktop) + the on-phone walkthrough.
- **Editor polish** (#85): template picker live miniatures, a publish popover
  (copy-URL + free-user sprout teaser), and a button-grid a11y fix (`role=group`
  so the field label doesn't activate the first control).
- **Billing deliberately deferred** (#84): not a flip blocker — allowlist +
  staging plan toggle exercise `sprout` without Stripe; revisited when the
  builder opens beyond the allowlist. Two low-prio editor-polish items → #86.

### Page builder — shipped 2026-07-07 (`v0.7.0`)

- The links-list editor grows into a **page builder**: a public page becomes a
  stack of pre-composed, full-width sections (10 types × hand-tuned variants),
  plus the surface for a paid **sprout** tier. Section model (`sections.py`)
  mirrors the theme engine — strict save / tolerant render, versioned shape
  (#75); additive migration adds `sections_draft_json` / `sections_live_json`
  (draft/live split) + `plan` (#74); theme gains a `line` token + sprout-only
  premium presets (#76).
- **In-canvas editor** (`/dash/builder`): sections render on the page and are
  selectable with a hover tool cluster, drag-to-reorder, gallery placeholders,
  autosave, publish, phone preview, theme picker, starter templates, and the
  premium drawer/upsell — rebuilt to match the design prototype. Public section
  rendering with the legacy links page as fallback (#78, #79). Gallery photo
  uploads reuse the avatar pipeline; `flask gc-images` sweeps orphans (#81).
- **Scoped public-page exceptions** (RULES.md / DECISIONS #38): embeds
  click-to-load, custom-HTML renders in a sandboxed network-blocked iframe,
  mail-list/form link out — each armed by the per-page CSP only where used;
  every other public page keeps the zero-JS / zero-third-party budget.
- The whole thing is **behind `BUILDER_ENABLED` + an allowlist, off in prod** —
  shipped the code without exposing the feature. Verified live: additive
  migration applied, Litestream replicating, public CSP strict, `/dash/builder`
  gated. Caught (self-review) a dash-CSP `connect-src` gap that would have
  blocked the editor's fetch in-browser, and inline-style CSP breakage.
- Deferred: enabling the flag in prod (gated on the real-browser QA pass, #34),
  editor refinement (#82), and billing. v0.6.0 (magic-link) stays deferred.

### Design refresh v2 — public profile + auth — shipped 2026-06-24 (`v0.5.0`)

- Finished the refresh on the two surfaces v0.4.0 left plain: the **public
  profile page** (centered + wide layouts, #50) and the **auth screens**
  (login/signup/reset rebuilt on a shared landing-shell partial — centered
  slice wordmark + glassy card, #51). Added per-page theme settings
  (layout/ambient/credit toggle) as **theme v3** with a migration, plus
  circle-crop photo avatars (#55); the design spec now lives in-repo (#56).
- Friendlier state screens (#52): a username-taken claim error that re-renders
  inline with the attempt kept + zero-JS suggestion chips (each re-checked
  against live names AND resting tombstones, so every chip is claimable), and a
  404 that turns a dead `/<username>` into a claim funnel — still HTTP 404,
  cookie-free, zero-JS.
- Login now accepts username **or** email (#54). Auth submit pills use the #36
  dark-ink token (AA). Dashboard JS held at its 200-line budget by keeping the
  new state screens script-free. Verified live: auth shell + 404 funnel serving
  on prod with CSP/HSTS intact.
- Deferred to v0.6.0: the magic-link UI + backend and the post-launch QA (#34).
  Follow-up filed: dashboard-wide white-on-accent AA cleanup (#65).

### Design refresh v2 — landing + dashboard — shipped 2026-06-21 (`v0.4.0`)

- Re-implemented a designer handoff (delivered as React prototypes) as Jinja +
  vanilla CSS: split-hero landing, restyled dashboard, and a shared inline-SVG
  `<symbol>` ambient background (`_motif_sprite.html`), CSS-only motion. Drawn
  avatars lead the picker; new default `set:sprout`; emoji/gradient kept
  rendering for existing users (no migration). Issues #40–#44.
- Caught pre-tag by Lighthouse: the prototype re-introduced the white-on-pink
  CTA contrast fail (kept the #36 dark-ink fix as a token), and the ambient
  motifs' inline `style=` was CSP-blocked (moved placement into the nonce'd
  `<style>` / `dash.css`). Verified live at Lighthouse 100/100/100, 0 console
  errors. Landing 4.7 KB gz.

### Phase 5 — Launch — shipped 2026-06-21 (`v0.3.0`)

- Public launch: `ROBOTS_ALLOW = "1"` in `fly.toml`; `robots.txt` now serves
  `Disallow:` (allow all). No page-weight or behavior change — same zero-JS,
  cookie-free public pages, now crawlable. Issue #35, PR #38.
- Accessibility fix found by the launch readiness pass: the landing primary CTA
  was white-on-pink at 2.36:1 (below WCAG AA). Switched to a deep-cherry ink on
  the same pink (6.32:1 rest / 5.26:1 hover) + a brand-chrome contrast
  regression test — the preset AA tests never covered chrome. Issue #36.
- Post-launch headless Lighthouse (landing): Performance / Accessibility /
  Best-Practices all **100**. SEO reads 91 due to one false-negative audit:
  Lighthouse fetches `robots.txt` via an in-page `fetch()` that the public-page
  CSP (`default-src 'none'`, no `connect-src`) blocks by design; real crawlers
  fetch it top-level and are unaffected — CSP deliberately not weakened. The
  authoritative Chrome DevTools run + on-phone walkthrough stay owner-driven (#34).
- Patch `v0.2.1` (2026-06-20) preceded this: deferred dependency bumps + the
  prio:low backlog (log scrubbing, art caching, optional error webhook, doc
  reconcile).

### Phase 4 — Production hardening — shipped 2026-06-20 (`v0.2.0`)

- DB backups now live: Litestream → Cloudflare R2 (EU jurisdiction). Production
  had been running with **no** replica configured. Switched from the bare
  `s3://` URL to a `litestream.yml` config file so the S3 `region` can be pinned
  (`region: auto`) — the URL form forces an AWS `GetBucketLocation` lookup that
  R2 rejects with `InvalidAccessKeyId`. Restore fire-drill passed. Issue #9, PR #30.
- Password-reset email deliverability verified in production. Issue #4.
- Legal placeholders (imprint + privacy) filled for the live EU site. Issue #3.
- Security regression tests: CSRF, IDOR, cookie-free guarantee. Issue #6, PR #28.
- Dependency vuln scanning + reproducible (digest-pinned) builds. Issue #7, PR #27.
- Shipped in `v0.2.1` (2026-06-20, patch): the deferred Dependabot runtime
  bumps (`actions/checkout` v7, `actions/setup-python` v6, python 3.14-slim,
  gunicorn 26) plus the four `prio:low` backlog items — reset-token log
  scrubbing (#11), immutable caching for avatar/pack tiles (#12), an optional
  error-reporting webhook (#13, DECISIONS #36), and a docs reconcile (#10).

### Phase 3 — Design-spec v1 — shipped 2026-06-14 (`v0.1.0`)

- Brand chrome: slice-mark favicon + Fredoka wordmark; CLS handled via preload
  + `font-display: swap` (DECISIONS #34).
- Avatars: 12-tile SVG `set` kind + freeform emoji, registry-validated at save
  AND render (DECISIONS #13 addendum).
- Decorations: 4 house packs + multi-decoration; theme shape v1 → v2 with a
  tested migration (DECISIONS #21/#30 addenda).
- Hardening landed alongside: avatar-volume persistence fix, legal-placeholder
  fills, GitHub Actions CI. Merged via PRs #1/#14/#15; deployed to Fly.io.

### Phase 2 — Launch readiness — shipped 2026-06-11

- Fly.io deploy: Dockerfile + entrypoint (restore → init-db → `gunicorn -w 1`),
  volume SQLite, app-level HSTS, optional Litestream (DECISIONS #33; runbook in
  `DEPLOY.md`). `99a1949`
- Password reset via Resend, password-gated account deletion + username
  tombstone, avatar uploads (EXIF/GPS strip, test-enforced), legal drafts.
  DECISIONS #26–#31. `d142d0c` `90a3708` `9fb8946` `704dd82` `cba93e1`
- Production baseline tagged `pre-refactor-prod` (2026-06-13).

### Phase 1 — v0 MVP — shipped 2026-06-10

- Skeleton → profile editing → links CRUD (IDOR-checked, validated at save AND
  render) → reorder + live preview → theming engine (6 AA presets) → perf/polish
  (collapsible dash, robots.txt, favicon, font caching). DECISIONS #1–#25.
  `44a36d4`–`917aec5`
