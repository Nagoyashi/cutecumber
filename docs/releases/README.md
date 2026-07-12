# Release notes

One file per release, `vX.Y.Z.md`, named for its version tag. Each is the
**single source of truth** for that release's notes: the `Publish release`
Action (`.github/workflows/release.yml`) reads the file on the tagged commit and
publishes the GitHub Release from it — H1 becomes the Release title, everything
below becomes the body. A tag with no matching file here fails the Action.

**Ordering rule (non-negotiable):** write and merge `vX.Y.Z.md` to `main`
*before* pushing the tag. The notes live on the tagged commit, not after it.

**Content rule (RULES.md voice + integrity):** factual status-quo summary plus
honest raw material (angles + the build story) for a build-in-public post.
Never invent metrics, user numbers, or claims — the owner supplies the voice and
the facts. The durable phase record stays in `project.md`; this file is the
release-note surface.

Pre-releases use a hyphenated tag (`vX.Y.Z-rc.N`) and the Action marks them
"Pre-release" instead of "latest".

## Index

_(newest first — add a line when a release ships)_

- [`v0.11.0`](v0.11.0.md) — Sites, not just pages: multi-page creator sites (`/you/about`), a zero-JS site nav, and a builder page switcher.
- [`v0.10.0`](v0.10.0.md) — A builder that behaves: loud save-failure state, errors that jump to the offending section, gallery-upload feedback, smooth drag.
- [`v0.9.0`](v0.9.0.md) — Page builder for everyone: opened to all creators as the primary editor; paid sprout tier gated as "coming soon".
- [`v0.8.0`](v0.8.0.md) — Page builder live (allowlist-gated): the prod flag flip, real-browser security QA, editor polish, billing deferred.
- [`v0.7.0`](v0.7.0.md) — Page builder (staging): section model, in-canvas editor, public rendering, gallery uploads, premium tier — all behind a flag.
- [`v0.5.0`](v0.5.0.md) — Design refresh v2 continued: public profile + auth screens rebuilt, per-page theme settings, friendlier state screens.
- [`v0.4.0`](v0.4.0.md) — Design refresh v2: modernized landing + dashboard, ambient SVG background, drawn-avatar picker.
- [`v0.3.0`](v0.3.0.md) — Launch: public (robots flip), landing CTA WCAG-AA fix + brand-chrome contrast guard.
- [`v0.2.1`](v0.2.1.md) — Maintenance & polish: held dependency bumps, log scrubbing, art caching, optional error webhook, doc reconcile.
- [`v0.2.0`](v0.2.0.md) — Production hardening (Phase 4): backups, reset email, legal, security tests.
- _`v0.1.0` predates this system and has no notes file._
