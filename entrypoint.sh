#!/bin/sh
set -e

CONFIG=/app/litestream.yml

# Disaster recovery: empty volume + configured replica -> restore the DB.
if [ -n "$LITESTREAM_BUCKET" ] && [ ! -f "$DATABASE" ]; then
  echo "no database found — attempting restore from replica…"
  litestream restore -if-replica-exists -config "$CONFIG" "$DATABASE"
fi

# Idempotent by design: applies schema + any missing-column upgrades.
flask --app wsgi init-db

# -c gunicorn.conf.py installs the access logger that redacts reset tokens (#11).
GUNICORN="gunicorn -c gunicorn.conf.py -w 1 -b 0.0.0.0:8000 --access-logfile - wsgi:app"

# Backups are config-file driven (litestream.yml) so the S3 region can be set —
# the bare s3:// URL form can't, and R2 needs it (see litestream.yml).
if [ -n "$LITESTREAM_BUCKET" ]; then
  echo "replicating to s3://$LITESTREAM_BUCKET/$LITESTREAM_PATH"
  exec litestream replicate -config "$CONFIG" -exec "$GUNICORN"
else
  echo "LITESTREAM_BUCKET not set — running WITHOUT backups"
  exec $GUNICORN
fi
