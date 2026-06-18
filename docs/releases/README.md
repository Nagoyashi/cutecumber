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

- _none yet — `v0.1.0` predates this system and has no notes file._
