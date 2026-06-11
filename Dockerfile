FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Litestream (optional SQLite replication — entrypoint skips it when
# LITESTREAM_REPLICA_URL is unset, so the app deploys before backups exist)
ADD https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin && rm /tmp/litestream.tar.gz

COPY . .
RUN chmod +x entrypoint.sh

# Runs as root inside the Fly microVM on purpose: the /data volume is
# root-owned, and Firecracker gives VM-level isolation (DECISIONS.md #33).
EXPOSE 8000
CMD ["./entrypoint.sh"]
