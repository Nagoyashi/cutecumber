#!/bin/sh
set -e

# Disaster recovery: empty volume + configured replica -> restore the DB.
if [ -n "$LITESTREAM_REPLICA_URL" ] && [ ! -f "$DATABASE" ]; then
  echo "no database found — attempting restore from replica…"
  litestream restore -if-replica-exists "$DATABASE"
fi

# Idempotent by design: applies schema + any missing-column upgrades.
flask --app wsgi init-db

GUNICORN="gunicorn -w 1 -b 0.0.0.0:8000 --access-logfile - wsgi:app"

if [ -n "$LITESTREAM_REPLICA_URL" ]; then
  echo "replicating to $LITESTREAM_REPLICA_URL"
  exec litestream replicate -exec "$GUNICORN" "$DATABASE" "$LITESTREAM_REPLICA_URL"
else
  echo "LITESTREAM_REPLICA_URL not set — running WITHOUT backups"
  exec $GUNICORN
fi
