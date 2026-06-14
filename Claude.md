# CLAUDE.md — cutecumber.cc

## Project status

Live in production at https://cutecumber.cc. Work here is maintenance,
bug-fixing, hardening, and incremental features — not greenfield build-out.

## Task tracking

Non-trivial work is tracked as GitHub issues. Issues auto-flow into the
GitHub Project titled "cutecumber.cc" (owner @Nagoyashi) via its Auto-add
workflow and land in the Backlog column automatically — so do NOT add issues
to the project manually; just create well-formed issues and the board places them.
(If you ever need the project number: `gh project list --owner "@me"`.)

## When to create an issue

- Anything not finished in the current session.
- Bugs, regressions, security concerns, tech debt, or gaps you notice.
- NOT for trivial fixes you complete immediately.
- Before creating: `gh issue list --search "<keywords>"` to avoid duplicates.

## Issue format

- Title: imperative, concise — "Add rate limiting to login endpoint".
- Body:
  **Context** — why it matters / where in the code (file paths).
  **Acceptance criteria** — bullets defining "done".
  **Notes** — optional links, gotchas, security considerations.
- Always apply one `type:*` and one `prio:*` label.

## Labels

- type: `type:feature` `type:bug` `type:chore` `type:refactor` `type:docs` `type:security`
- priority: `prio:high` `prio:med` `prio:low`

## Commands

- Create: gh issue create -t "<title>" -b "<body>" -l "type:bug,prio:high"
- List: gh issue list --limit 100

## Project log

Keep docs/PROJECT_LOG.md current. Append a dated entry whenever you ship a
meaningful change, complete a milestone, or make an architectural decision.
Newest first. Keep entries short: what changed + why.
