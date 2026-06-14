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
