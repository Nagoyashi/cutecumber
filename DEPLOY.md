# DEPLOY.md — cutecumber on Fly.io 🚀

> One small always-on machine in Frankfurt + a 1 GB volume for SQLite.
> Expected cost: roughly $3–5/month. Litestream backups to free object
> storage make the machine disposable; the data is not.

## 0. One-time prerequisites

```bash
# install flyctl (https://fly.io/docs/flyctl/install/)
curl -L https://fly.io/install.sh | sh
fly auth signup        # or: fly auth login
```

## 1. Create the app + volume (one time)

From the repo root (fly.toml is already here):

```bash
fly apps create cutecumber
fly volumes create cutecumber_data --region fra --size 1
```

## 2. Secrets (one time)

```bash
fly secrets set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
fly secrets set RESEND_API_KEY="re_your_key"
```

Non-secret config (SITE_ORIGIN, MAIL_FROM, COOKIE_SECURE, …) lives in
fly.toml `[env]` — edit there, redeploy to apply.

## 3. First deploy

```bash
fly deploy
fly logs        # watch for "database ready 🥒" then gunicorn booting
```

The entrypoint runs `init-db` on every boot — it's idempotent, so schema
upgrades ship themselves with each deploy.

## 4. Point cutecumber.cc at it (one time)

```bash
fly certs add cutecumber.cc
fly ips list
```

At your registrar, create for the apex domain:
- `A` record → the IPv4 from `fly ips list`
- `AAAA` record → the IPv6

Then `fly certs check cutecumber.cc` until it reports verified (minutes,
sometimes an hour). `force_https` is already on.

## 5. Verify the deploy (every deploy, 60 seconds)

```bash
curl -sI https://cutecumber.cc | grep -iE "strict-transport|content-security"
curl -s  https://cutecumber.cc/robots.txt     # must say "Disallow: /" pre-launch
flask --app wsgi --help >/dev/null            # locally: app still boots
```

Then by hand: sign up, claim, upload an avatar, run a password reset
(`fly logs` shows mail errors if any), and load your page on a phone.

## 6. Backups — do this before inviting ANYONE

Litestream streams every SQLite change to object storage; the entrypoint
auto-restores onto an empty volume, so losing the machine loses nothing.

> Scope: Litestream backs up the **database** only. Uploaded avatars live on
> the volume at `/data/avatars` (`AVATAR_DIR`) and survive deploys/restarts,
> but are **not** in the Litestream replica — destroying the volume loses
> them. They're user-re-uploadable, so this is acceptable; if that changes,
> add object-storage sync for `/data/avatars`.

Config lives in `litestream.yml` (a config file, not the bare `s3://` URL —
Litestream v0.3.13's URL form can't set the S3 `region`, so it does an AWS
region lookup that R2 rejects with `InvalidAccessKeyId`; the config file pins
`region: auto`). Non-secret values are in `fly.toml [env]`; credentials are
secrets. Replication turns on only when `LITESTREAM_BUCKET` is set.

1. Create a free bucket: Cloudflare R2 (10 GB free) or Backblaze B2.
2. Create an "Object Read & Write" access key pair for it. For an **EU**
   R2 bucket the token scope must be **all buckets** (or EU-jurisdiction) and
   the endpoint must be the `.eu.` form — `<account>.eu.r2.cloudflarestorage.com`.
3. Non-secret config in `fly.toml [env]` (commit it):
   ```toml
   LITESTREAM_BUCKET   = "your-bucket"
   LITESTREAM_PATH     = "cutecumber"
   LITESTREAM_ENDPOINT = "https://<account>.eu.r2.cloudflarestorage.com"
   ```
   Credentials as secrets:
   ```bash
   fly secrets set \
     LITESTREAM_ACCESS_KEY_ID="..." \
     LITESTREAM_SECRET_ACCESS_KEY="..."
   ```
4. `fly deploy`, then confirm `fly logs` shows "replicating to …" followed by
   "snapshot written" / "wal segment written" (not "WITHOUT backups" or any
   `monitor error`). Tip: validate creds out-of-band first — a quick boto3
   `put_object`/`get_object` against the endpoint catches key/scope/jurisdiction
   mistakes before a redeploy.
5. **Fire drill (do it once):** `fly ssh console`, then
   `litestream restore -config /app/litestream.yml -o /tmp/verify.db "$DATABASE"`
   and confirm it rebuilds a valid DB (`sqlite3 /tmp/verify.db .tables`). A
   backup you've never restored is a hope, not a backup. (Destroying a
   throwaway app's volume and watching the auto-restore is the heavier variant.)

## 7. Launch day

1. Legal pages: every `[PLACEHOLDER]` filled and reviewed. ✅ before anything.
2. In fly.toml set `ROBOTS_ALLOW = "1"`, then `fly deploy`.
3. Lighthouse run in Chrome DevTools against https://cutecumber.cc.

## Routine updates

```bash
git push && fly deploy
```

## If things look wrong

```bash
fly logs                  # app + mail errors, init-db output
fly ssh console           # shell inside the machine
fly status                # machine health, last deploy
```

## Scaling notes (future-you)

One gunicorn worker is deliberate (rate-limiter counters are per-process,
DECISIONS.md #7). First lever under load: bigger machine. Second: cache
public pages in-process. Worker count and limiter storage change together,
with a written decision.
