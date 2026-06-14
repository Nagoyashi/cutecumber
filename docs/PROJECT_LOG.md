# Project Log — cutecumber.cc

Reverse-chronological log of meaningful changes, milestones, and decisions.
Newest first.

## Current state

- Live in production at https://cutecumber.cc.
- Task tracking via GitHub Project "cutecumber.cc" + Issues.

---

## 2026-06-14 — Project management setup

- Created GitHub Project "cutecumber.cc" (per-repo board).
- Status field: added **Backlog** (default) and **Blocked**.
- Workflows enabled:
  - Auto-add to project — filter `is:issue is:open`, scoped to this repo.
  - Item added → Status: Backlog.
  - Item closed → Status: Done.
  - (Defaults left on: PR linked/merged, review approved/changes requested,
    item reopened, auto-archive.)
- Defined standard labels: `type:*`, `prio:*`.
- Added CLAUDE.md with issue/labeling conventions for Claude Code.

## 2026-06-14 — Frontend refactor: design spec v1

- Integrated the approved brand art within the zero-JS / ≤15 KB budget: slice-mark
  favicon + Fredoka wordmark, a 12-avatar SVG `set` kind plus freeform emoji, and
  curated decoration packs with multi-decoration support.
- Theme shape bumped v1→v2 (decoration string→list) with a tested migration.
  Opened as PR #1 from `frontend-refactor`; 76 tests green. (`eb3ab31`)

## 2026-06-14 — RULES.md working contract

- Codified the per-page performance budget, security non-negotiables, the fixed
  stack, and design-spec constraints as the read-first contract for agents. (`c87487e`)

## 2026-06-13 — Design assets imported; production baseline tagged

- Added the design spec and production SVG assets — mascots, 12 avatars, and 4
  decoration packs — ahead of the brand integration. (`bfa0336`)
- Tagged `pre-refactor-prod` to mark the last known-good production commit.

## 2026-06-11 — Production deploy (Fly.io) + legal + tombstone

- Fly.io deploy config: Dockerfile, entrypoint with optional Litestream, fly.toml,
  app-level HSTS, DEPLOY.md runbook — one always-on machine, SQLite on a volume
  (DECISIONS #33). (`99a1949`)
- Added imprint/privacy legal texts (`704dd82`); 30-day username tombstone to block
  instant impersonation, WebKit drag-reorder fixes, and a plain-language landing
  explainer (`cba93e1`).

## 2026-06-10 — Launch-prep: password reset, account deletion, avatar uploads

- Password reset via Resend (hashed single-use tokens, anti-enumeration) + landing
  redesign (`d142d0c`); password-gated hard account deletion + DESIGN_PACKS spec
  (`90a3708`).
- Avatar uploads re-encoded through Pillow to strip EXIF/GPS (test-enforced) +
  send-test CLI; mail User-Agent fix for Cloudflare error 1010 (`9fb8946`, `c3e4c34`).

## 2026-06-10 — v0 feature build

- Profile editing (name/bio/pronouns, curated emoji + gradient avatars), links CRUD
  (URL validator at save AND render, IDOR-checked), editor JS (pointer-drag +
  keyboard reorder, live-preview iframe, delete confirm, ≤200 lines). (`e040d1d`–`8f52d23`)
- Theming engine: 6 WCAG-AA presets, validated token overrides, self-hosted display
  fonts, SVG decorations; then dash polish — collapsible sections, anchored save
  redirects, robots.txt, favicon, immutable font caching. (`e0aaf7a`, `917aec5`)

## 2026-06-10 — Project start

- Flask + Jinja SSR, raw sqlite3 (WAL), no ORM and no build step; walking skeleton:
  signup → claim username → public page with OG tags. Why: privacy-first, zero-JS
  public pages on a fixed minimal stack. (`44a36d4`–`30071ea`)
