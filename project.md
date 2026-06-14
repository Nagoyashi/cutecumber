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

**Phase 3 — Design-spec v1 (brand integration)** · status: **in review** (PR #1)
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

### ▶ Phase 3 — Design-spec v1 (current, 2026-06-13 → )

**Scope:** brand chrome (slice-mark favicon + Fredoka wordmark) · 12-avatar SVG
`set` avatar kind + freeform emoji · decoration packs + multi-decoration (theme
shape v1 → v2). Production hardening landed alongside on `main`: the
avatar-volume persistence fix, legal-placeholder fills, and CI.

**Acceptance:** design art integrated with every `RULES.md` invariant intact
(0 JS, 0 third-party requests, ≤15 KB, Lighthouse-100 budget); the theme
migration is tested; the full suite is green in CI; PR #1 reviewed and merged
to `main`.

### ⬜ Phase 4 — Production hardening (planned — prose)

Close the post-launch audit backlog: security regression tests (CSRF / IDOR /
cookie-free), dependency scanning, error monitoring, doc & comment
reconciliation, reset-token log hygiene, static-tile caching, and backup
verification. Tracked as issues on the board.

### ⬜ Phase 5 — Launch & growth (planned — speculative)

Public launch (flip `ROBOTS_ALLOW`, real Lighthouse pass in Chrome, phone QA),
then growth — paid decoration packs (see `DESIGN_PACKS.md`) and more themes /
avatars. *Best guess; correct as direction firms up.*

> Versioning: shipped phases above are dated from git history — no semver tags
> exist for them. Going forward, each phase release gets a semver tag
> (`v0.1.0`, …); historical commits are not retro-tagged.

## Phase log

Durable completion notes, newest first. Rationale → `DECISIONS.md`.

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
