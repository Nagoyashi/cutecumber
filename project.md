# project.md — cutecumber.cc

> Canonical roadmap & strategy. **Phase-level status only** — per-task status
> lives on the *cutecumber.cc* GitHub Project board, never here. Architectural
> rationale lives in `DECISIONS.md`; the hard invariants in `RULES.md`.

## Vision

A cute, fast, privacy-first link-in-bio: one tiny server-rendered page for all
your links, with zero JavaScript, zero trackers, and zero cookies on public
pages. It wins on cuteness, curated customization, page speed, and privacy —
never on feature breadth.

## Current phase

**Between cycles.** Phase 4 — Production hardening shipped as **`v0.2.0`**
(2026-06-20). Next up: **Phase 5 — Launch & growth** — propose the cycle scope
and get the owner's OK before starting (see the Release cycle in CLAUDE.md).
Per-task status → the *cutecumber.cc* GitHub Project board ↗

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

### ⬜ Phase 5 — Launch & growth (planned — speculative)

Public launch (flip `ROBOTS_ALLOW`, real Lighthouse pass in Chrome, phone QA),
then growth — paid decoration packs (see `DESIGN_PACKS.md`) and more themes /
avatars. *Best guess; correct as direction firms up.*

> Versioning: shipped phases above are dated from git history — no semver tags
> exist for them. Going forward, each phase release gets a semver tag
> (`v0.1.0`, …); historical commits are not retro-tagged.

## Phase log

Durable completion notes, newest first. Rationale → `DECISIONS.md`.

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
- Deferred to `v0.2.1`: Dependabot runtime bumps (`actions/checkout` v7,
  `actions/setup-python` v6, python 3.14-slim, gunicorn 26).

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
