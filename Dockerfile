# Base image digest-pinned for reproducible builds (issue #7). The 3.14-slim
# tag is kept for readability and to match the CI Python pin; the @sha256 digest
# is the actual contract. Dependabot updates the digest; a 3.x->3.y bump is a
# deliberate, separate change (must move the ci.yml python-version in lockstep).
FROM python:3.14-slim@sha256:63a4c7f612a00f92042cbdcc7cdc6a306f38485af0a200b9c89de7d9b1607d15

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
