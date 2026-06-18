# CLAUDE.md — cutecumber.cc

Lean operating manual for agents. Read the right owner before changing anything:

- **`RULES.md`** — hard invariants (perf budget, security, fixed stack, voice).
  Read it before ANY perf / security / stack change. It is the contract.
- **`project.md`** — the roadmap, current phase, and phase-level status (the
  source of truth for what we're building and where we are).
- **`DECISIONS.md`** — why each choice was made + when to revisit it.
- **`PROJECT_STRUCTURE.md`** — file tree + code-placement conventions.
- **`DEPLOY.md`** — Fly.io deploy / backup runbook.

Per-task status is the GitHub Project board's job — never a doc.

## Session protocol

On a fresh session — or when I say **"continue"** / **"read status"** — derive
the *live* state from GitHub first (the docs are roadmap-level and lag the
day-to-day; the board and milestone are the truth for "where are we now"):

1. **Open milestone = the current cycle.** `gh api
   repos/Nagoyashi/cutecumber/milestones --jq '.[]|select(.state=="open")
   |{title,open_issues,closed_issues}'`. There is exactly one; its title is the
   target version (e.g. `v0.2.0`).
2. **Its issues = the cycle scope.** `gh issue list --milestone "<title>"
   --state all` — open vs closed is the burndown.
3. **Open PRs = in-flight work.** `gh pr list`.
4. **The in-progress issue's latest comment = the working note / handoff.**
   `gh issue view <n> --comments`.

Then, before changing anything, read the relevant **owner** doc for the *why* —
they're listed at the top of this file (`RULES.md` is the contract; read it
before any perf / security / stack / voice change). If no milestone is open,
we're between cycles → see the Release cycle (propose the next one; don't
invent work).

## Commands

- Tests: `python -m unittest -v` (repo root). CI runs them on push + PRs to main.
- Run (dev): `flask --app wsgi init-db` then `flask --app wsgi run --debug`.
- Issues: `gh issue create -t "<title>" -b "<body>" -l "type:bug,prio:high"` ·
  `gh issue list --limit 100`.

## Task tracking

Non-trivial work is tracked as GitHub issues. They auto-flow into the GitHub
Project "cutecumber.cc" (owner @Nagoyashi) and land in **Backlog**; **Blocked**
is the other non-default status. Don't add items to the board manually — file a
well-formed issue and the Auto-add workflow places it. (Project number if
needed: `gh project list --owner "@me"`.)

Every cycle issue is filed against the current **milestone** (the open one — see
the Release cycle): `gh issue create … --milestone "<vX.Y.0>"`. The milestone
is the cycle handle; the board shows the per-task lane. Out-of-cycle bugs you
just notice still get filed (no milestone needed) — they get triaged into a
cycle later.

### When to file an issue

- Anything unfinished at end of session; bugs, regressions, security concerns,
  tech debt, or gaps you notice. NOT trivial fixes you complete immediately.
- First run `gh issue list --search "<keywords>"` to avoid duplicates.

### Issue format

- Title: imperative, concise — "Add rate limiting to login endpoint".
- Body: **Context** (why it matters + where, file paths) · **Acceptance
  criteria** (bullets defining done) · **Notes** (optional gotchas / security).
- Always one `type:*` and one `prio:*` label.

### Labels

- type: `type:feature` `type:bug` `type:chore` `type:refactor` `type:docs` `type:security`
- priority: `prio:high` `prio:med` `prio:low`

## Release cycle (milestone = cycle = version)

One **open milestone at a time**, titled for its target version (`v0.2.0`, then
`v0.3.0`, …) — it is the GitHub handle for the current `project.md` phase. Its
issues are the cycle scope (file them `--milestone "<vX.Y.0>"`). Don't plan
beyond the cycle in flight: materialize the current phase only, never all future
phases. Patch releases (`vX.Y.Z`, Z>0) skip the milestone — they're hotfixes.

Branch model: **main-only** (option A). `feature/*` → PR → **squash-merge** to
`main`. `main` is production, but the deploy is **manual** (`fly deploy`, per
`DEPLOY.md`) — pushing to `main` ships nothing on its own. So the version tag
lands on the `main` commit **only after a verified prod deploy**.

The cycle is a state machine — derive the current state from GitHub (Session
protocol), then drive it forward:

| State | Lives in | You're here when | Advance by |
|-------|----------|------------------|------------|
| **1 Plan** | open milestone + board *Backlog* | cycle approved | goal set, issues filed `--milestone` |
| **2 Build** | `feature/*` → PRs to `main` | issues open / in progress | every cycle issue **closed & merged to `main`** |
| **3 Notes** | `docs/releases/vX.Y.Z.md` on `main` | code is done | notes file written + **merged to `main`** |
| **4 Deploy** | Fly.io (manual) | notes merged | `git push origin main && fly deploy`, verified (DEPLOY.md §5) |
| **5 Tag** | `git tag vX.Y.Z && git push --tags` | prod is verified live | `release.yml` publishes the Release & closes the milestone |
| **6 Record** | `project.md` + `README.md` | Release is published | phase → shipped + phase-log entry; advance Current-phase pointer |

Hard ordering rule (the Action enforces it): the `docs/releases/vX.Y.Z.md` notes
must be **merged to `main` before the tag is pushed** — they live on the tagged
commit. The tag push IS the "ship it" approval; `release.yml` then builds the
GitHub Release from that file (H1 → title, body → rest) and closes the
same-named milestone. Don't create Releases by hand.

After tagging: update `project.md` (move the phase to shipped, write its
phase-log entry, advance the Current-phase pointer) and `README.md`. The
milestone auto-closes; closed cards auto-archive — never add an "Archived"
status or move cards by hand. The `project.md` phase log is the durable record.

Between cycles (no milestone open): propose the next one — title `vX.Y.0` + a
one-line goal + its issues — and wait for the owner's OK before creating
anything. Settle any `DECISIONS.md` open question the cycle forces first.

**Integrity (non-negotiable):** release notes and post material NEVER invent
metrics, user numbers, or claims. Factual status-quo summary + honest raw
material (angles + the build story) only; the owner supplies the voice and the
facts.
