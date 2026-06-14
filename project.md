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

**Phase 4 — Production hardening** · status: **in progress**
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

### ▶ Phase 4 — Production hardening (current)

Close the post-launch audit backlog: security regression tests (CSRF / IDOR /
cookie-free), dependency scanning, error monitoring, doc & comment
reconciliation, reset-token log hygiene, static-tile caching, backup
verification, and reset-email deliverability. Tracked as issues on the board.

**Acceptance:** the high/med audit issues closed; DB backups and password-reset
email verified working in production.

### ⬜ Phase 5 — Launch & growth (planned — speculative)

Public launch (flip `ROBOTS_ALLOW`, real Lighthouse pass in Chrome, phone QA),
then growth — paid decoration packs (see `DESIGN_PACKS.md`) and more themes /
avatars. *Best guess; correct as direction firms up.*

> Versioning: shipped phases above are dated from git history — no semver tags
> exist for them. Going forward, each phase release gets a semver tag
> (`v0.1.0`, …); historical commits are not retro-tagged.

## Phase log

Durable completion notes, newest first. Rationale → `DECISIONS.md`.

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
