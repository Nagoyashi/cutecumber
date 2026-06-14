# cutecumber 🥒

the cutest little link-in-bio. fast, private, no trackers — ever.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# generate a secret and paste it into .env:
python -c "import secrets; print(secrets.token_hex(32))"

flask --app wsgi init-db
flask --app wsgi run --debug
```

Then open http://localhost:5000 — sign up, claim a username, and your public
page is live at http://localhost:5000/yourname.

## Production

Deployed on Fly.io — one always-on machine, SQLite on a volume. See `DEPLOY.md`
for the full runbook. Workers stay at 1 (rate-limiter counters are per-process,
DECISIONS.md #7).

## Project docs

- `project.md` — roadmap, current phase, and phase log.
- `RULES.md` — the hard invariants: perf budget, security, stack, voice.
- `CLAUDE.md` — agent operating manual + task tracking.
- `DECISIONS.md` — why things are the way they are, and when to revisit.
- `PROJECT_STRUCTURE.md` — file tree + code-placement conventions.
- `DEPLOY.md` — Fly.io deploy + backup runbook.
