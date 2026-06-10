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

## Production (sketch — deploy target not yet decided, see DECISIONS.md #11)

```bash
gunicorn -w 1 'wsgi:app'
```

Keep workers at 1 until the rate-limiter storage decision is made
(DECISIONS.md #7). TLS, HSTS, and gzip belong to the reverse proxy (Caddy).

## Read these first, every session

- `PROJECT_STRUCTURE.md` — file map, conventions, roadmap.
- `DECISIONS.md` — why things are the way they are, and when to revisit.
